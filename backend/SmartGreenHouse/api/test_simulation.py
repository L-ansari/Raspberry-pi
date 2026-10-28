from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from api.authentication import hash_api_key
from api.models import EdgeNode, SensorReading


@override_settings(SIMULATION_INGESTION_TOKEN='test-secret', SIMULATION_NODE_IDS=['virtual-test'])
class SimulationTests(APITestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='simulation-owner')
        self.node = EdgeNode.objects.create(node_id='virtual-test', name='Virtual', zone_id='zone-1',
                                           owner=self.owner, api_key_hash=hash_api_key('device-key'))
        self.payload = dict(temperature=24, humidity=50, soil_moisture=35, light=600)
        self.old = timezone.now() - timedelta(days=29)
        self.headers = dict(HTTP_X_EDGE_KEY='device-key', HTTP_X_SIMULATION_TOKEN='test-secret')

    def post(self, **changes):
        return self.client.post('/api/sensors/', {**self.payload, **changes}, format='json', **self.headers)

    def test_backfill_and_older_upload_do_not_regress_last_data_at(self):
        response = self.post(recorded_at=self.old.isoformat())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SensorReading.objects.get().timestamp, self.old)
        self.post(recorded_at=(self.old - timedelta(hours=1)).isoformat())
        self.node.refresh_from_db()
        self.assertEqual(self.node.last_data_at, self.old)
        self.client.force_authenticate(self.owner)
        response = self.client.get('/api/sensors/current/')
        self.assertEqual(response.data['reading']['id'], str(SensorReading.objects.order_by('-timestamp').first().pk))

    def test_each_authorization_requirement_is_enforced_without_writes(self):
        for headers in [{}, {'HTTP_X_EDGE_KEY': 'device-key'},
                        {**self.headers, 'HTTP_X_SIMULATION_TOKEN': 'wrong'}]:
            self.headers = headers
            self.assertEqual(self.post(recorded_at=self.old.isoformat()).status_code, 403)
        self.headers = dict(HTTP_X_EDGE_KEY='device-key', HTTP_X_SIMULATION_TOKEN='test-secret')
        for options in [dict(SIMULATION_NODE_IDS=[]), dict(SIMULATION_INGESTION_TOKEN='')]:
            with override_settings(**options):
                self.assertEqual(self.post(recorded_at=self.old.isoformat()).status_code, 403)
        self.assertEqual(SensorReading.objects.count(), 0)

    def test_invalid_or_out_of_window_timestamp_rejected(self):
        for value in ['invalid', None, (timezone.now() + timedelta(hours=1)).isoformat(),
                      (timezone.now() - timedelta(days=32)).isoformat()]:
            self.assertEqual(self.post(recorded_at=value).status_code, 400)
        self.assertEqual(SensorReading.objects.count(), 0)

    def test_normal_upload_uses_server_time_even_with_readonly_timestamp(self):
        self.headers = {'HTTP_X_EDGE_KEY': 'device-key'}
        before = timezone.now()
        self.assertEqual(self.post(timestamp=self.old.isoformat()).status_code, 201)
        self.assertGreaterEqual(SensorReading.objects.get().timestamp, before)
