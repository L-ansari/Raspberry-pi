from datetime import timedelta
from io import StringIO
import json
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import EdgeNode, SensorReading, Plant, PlantAnalysis
from api.dashboard import history_snapshot
from llm.services import call_ollama, OllamaServiceError


class DashboardTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='alice', password='test-password')
        self.other = get_user_model().objects.create_user(username='bob', password='test-password')
        EdgeNode.objects.create(node_id='owned', name='Default', zone_id='zone-1', owner=self.user, api_key_hash='one')
        EdgeNode.objects.create(node_id='other', name='Other', zone_id='zone-2', owner=self.other, api_key_hash='two')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.user).access_token}')
        self.plant = Plant.objects.create(id='tomato', name='Tomato', scientific_name='Solanum lycopersicum')
        self.reading = SensorReading.objects.create(temperature=24, humidity=50, soil_moisture=22, light=620, node_id='owned')
        self.as_of = timezone.now()
        self.payload = {'plant_id': 'tomato', 'reading_id': str(self.reading.pk), 'range': '7d',
                        'as_of': self.as_of.isoformat(), 'request_id': str(uuid.uuid4())}
        self.result = {'alerts': [{'type': 'LOW_SOIL_MOISTURE', 'title': 'Low soil moisture',
                                  'severity': 'warning', 'message': 'Check the soil.'}],
                       'recommendation': {'suggestion': 'Inspect before watering.', 'explanation': 'The supplied soil reading is low.'}}

    def test_seed_is_idempotent_and_english_searches_aliases(self):
        for _ in range(2):
            call_command('seed_plants', stdout=StringIO())
        self.assertEqual(Plant.objects.count(), 20)
        response = self.client.get('/api/plants/?search=CILANTRO')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['id'], 'coriander')
        self.assertEqual(self.client.get('/api/plants/?search=missing').data['results'], [])

    def test_current_is_latest_owned_not_latest_other_user(self):
        newer = SensorReading.objects.create(temperature=99, humidity=1, soil_moisture=1, light=1, node_id='other')
        response = self.client.get('/api/sensors/current/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['reading']['id'], str(self.reading.pk))
        self.assertNotEqual(response.data['reading']['id'], str(newer.pk))

    def test_current_empty_and_auth_required(self):
        self.reading.delete()
        self.assertIsNone(self.client.get('/api/sensors/current/').data['reading'])
        self.client.credentials()
        self.assertEqual(self.client.get('/api/sensors/current/').status_code, 401)

    def test_summary_has_exact_buckets_and_preserves_gaps_and_extrema(self):
        older = SensorReading.objects.create(temperature=30, humidity=60, soil_moisture=40, light=800, node_id='owned')
        SensorReading.objects.filter(pk=older.pk).update(timestamp=self.as_of - timedelta(hours=1))
        SensorReading.objects.create(temperature=999, humidity=0, soil_moisture=0, light=0, node_id='other')
        summary = history_snapshot(self.user, '7d', self.as_of)
        self.assertEqual(len(summary['points']), 28)
        self.assertIsNone(summary['points'][0]['temperature'])
        last = summary['points'][-1]
        self.assertEqual(last['sample_count'], 2)
        self.assertEqual(last['temperature'], 27)
        self.assertEqual(last['maximum']['temperature'], 30)
        self.assertEqual(len(history_snapshot(self.user, '30d', self.as_of)['points']), 30)
        self.assertEqual(self.client.get('/api/sensors/history-summary/invalid/').status_code, 400)

    @patch('llm.plant_services.call_ollama')
    def test_status_is_validated_not_persisted_and_cannot_read_another_user(self, model):
        model.return_value = json.dumps({key: 'unknown' for key in ['temperature', 'humidity', 'soil_moisture', 'light']})
        response = self.client.post('/api/llm/status/', self.payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PlantAnalysis.objects.count(), 0)
        foreign = SensorReading.objects.create(temperature=1, humidity=1, soil_moisture=1, light=1, node_id='other')
        self.assertEqual(self.client.post('/api/llm/status/', {**self.payload, 'reading_id': str(foreign.pk)}, format='json').status_code, 404)
        model.return_value = json.dumps({'temperature': 'invented'})
        self.assertEqual(self.client.post('/api/llm/status/', self.payload, format='json').status_code, 503)

    @patch('llm.plant_services.call_ollama')
    def test_analysis_saves_exact_snapshot_retries_once_and_is_private(self, model):
        model.return_value = json.dumps(self.result)
        response = self.client.post('/api/plant-analysis/', self.payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        analysis = PlantAnalysis.objects.get()
        self.assertEqual(analysis.snapshot['latest_reading']['id'], str(self.reading.pk))
        self.assertEqual(analysis.snapshot['plant']['name'], 'Tomato')
        self.assertEqual(len(analysis.snapshot['points']), 28)
        replay = self.client.post('/api/plant-analysis/', self.payload, format='json')
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(model.call_count, 1)
        self.reading.delete()
        detail = self.client.get(f'/api/plant-analysis/{analysis.pk}/')
        self.assertEqual(detail.data['snapshot']['latest_reading']['temperature'], 24)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.other).access_token}')
        self.assertEqual(self.client.get(f'/api/plant-analysis/{analysis.pk}/').status_code, 404)

    @patch('llm.plant_services.call_ollama')
    def test_analysis_invalid_json_does_not_save_and_snapshot_mismatch_rejected(self, model):
        model.return_value = 'not json'
        self.assertEqual(self.client.post('/api/plant-analysis/', self.payload, format='json').status_code, 503)
        self.assertEqual(PlantAnalysis.objects.count(), 0)
        earlier = self.as_of - timedelta(days=1)
        self.assertEqual(self.client.post('/api/plant-analysis/', {**self.payload, 'as_of': earlier.isoformat()}, format='json').status_code, 409)

    def test_english_only_and_cors_preflight(self):
        self.assertEqual(self.client.post('/api/llm/chat/', {'message': 'Hello', 'language': 'zh'}, format='json').status_code, 400)
        response = self.client.options('/api/llm/status/', HTTP_ORIGIN='http://127.0.0.1:5173', HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST', HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization,content-type')
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://127.0.0.1:5173')

    @override_settings(OLLAMA_MODEL='')
    def test_missing_model_is_a_service_error(self):
        with self.assertRaises(OllamaServiceError):
            call_ollama([])
