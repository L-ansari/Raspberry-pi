
from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from api.scoping import owned_node_ids

from .serializers import (
    RecommendationRequestSerializer,
    ChatRequestSerializer,
)
from .services import (
    generate_recommendation,
    chat_with_greenhouse,
    OllamaServiceError,
)


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def recommend(request):
    serializer = RecommendationRequestSerializer(
        data=request.data
    )

    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = generate_recommendation(
            hours=serializer.validated_data["hours"],
            language=serializer.validated_data["language"],
            node_ids=owned_node_ids(request.user),
        )
    except OllamaServiceError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "status": "success",
            "recommendation": result["recommendation"],
            "context": result["context"],
            "generated_at": timezone.now(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def chat(request):
    serializer = ChatRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = chat_with_greenhouse(
            message=serializer.validated_data["message"],
            language=serializer.validated_data["language"],
            node_ids=owned_node_ids(request.user),
        )
    except OllamaServiceError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "status": "success",
            "reply": result["reply"],
            "context_used": result["context_used"],
            "generated_at": timezone.now(),
        },
        status=status.HTTP_200_OK,
    )


def _plant(plant_id):
    from api.models import Plant
    from rest_framework.exceptions import NotFound
    plant = Plant.objects.filter(pk=plant_id, is_active=True).first()
    if plant is None:
        raise NotFound('Plant not found.')
    return plant


def _reading(user, reading_id):
    from api.scoping import readings_for_user
    from django.core.exceptions import ValidationError
    from rest_framework.exceptions import NotFound
    try:
        reading = readings_for_user(user).filter(pk=reading_id).first()
    except (ValueError, TypeError, ValidationError):
        reading = None
    if reading is None:
        raise NotFound('Sensor reading not found.')
    return reading


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sensor_status(request):
    from api.dashboard import UNITS, json_copy
    from api.serializers import SensorReadingSerializer
    from .serializers import StatusRequestSerializer
    from .plant_services import assess_status
    serializer = StatusRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=400)
    plant = _plant(serializer.validated_data['plant_id'])
    reading = _reading(request.user, serializer.validated_data['reading_id'])
    context = json_copy({
        'plant': {'id': plant.pk, 'name': plant.name, 'scientific_name': plant.scientific_name},
        'latest_reading': SensorReadingSerializer(reading).data, 'units': UNITS,
        'as_of': timezone.now(),
    })
    try:
        statuses = assess_status(context)
    except OllamaServiceError as exc:
        return Response({'error': str(exc)}, status=503)
    return Response({'plant_id': plant.pk, 'reading_id': str(reading.pk), 'sensor_statuses': statuses})


def _analysis_response(analysis):
    return {
        'analysis_id': str(analysis.pk), 'plant_id': analysis.plant_id,
        'range': analysis.range, 'snapshot': analysis.snapshot, **analysis.result,
        'model_name': analysis.model_name, 'schema_version': analysis.schema_version,
        'generated_at': analysis.created_at,
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def plant_analysis(request):
    from api.models import PlantAnalysis
    from api.dashboard import SnapshotQuery, history_snapshot, json_copy
    from .serializers import AnalysisRequestSerializer
    from .plant_services import assess_history
    from django.conf import settings
    from django.db import IntegrityError
    serializer = AnalysisRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=400)
    data = serializer.validated_data
    query = SnapshotQuery(data={'as_of': data['as_of']})
    if not query.is_valid():
        return Response({'errors': query.errors}, status=400)
    analysis_id = str(data['request_id'])
    existing = PlantAnalysis.objects.filter(pk=analysis_id, owner=request.user).first()
    if existing:
        previous = existing.snapshot
        if (existing.plant_id != data['plant_id'] or existing.range != data['range']
                or previous['latest_reading']['id'] != data['reading_id']
                or previous['as_of'] != json_copy(data['as_of'])):
            return Response({'error': 'Request ID already belongs to a different analysis.'}, status=409)
        return Response(_analysis_response(existing))
    plant = _plant(data['plant_id'])
    _reading(request.user, data['reading_id'])
    snapshot = history_snapshot(request.user, data['range'], data['as_of'])
    latest = snapshot['latest_reading']
    if not latest or latest['id'] != data['reading_id']:
        return Response({'error': 'The reading does not match this snapshot. Refresh the dashboard.'}, status=409)
    if not any(point['sample_count'] for point in snapshot['points']):
        return Response({'status': 'no_data', 'plant_id': plant.pk, 'range': data['range'],
                         'alerts': None, 'recommendation': None, 'snapshot': snapshot})
    snapshot['plant'] = {'id': plant.pk, 'name': plant.name, 'scientific_name': plant.scientific_name}
    try:
        result = assess_history(snapshot)
    except OllamaServiceError as exc:
        return Response({'error': str(exc)}, status=503)
    try:
        analysis = PlantAnalysis.objects.create(
            id=analysis_id, owner=request.user, plant=plant, range=data['range'],
            snapshot=snapshot, result=json_copy(result), model_name=settings.OLLAMA_MODEL,
        )
    except IntegrityError:
        return Response({'error': 'This request is already being saved. Retry with the same request ID.'}, status=409)
    return Response(_analysis_response(analysis), status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plant_analysis_detail(request, analysis_id):
    from api.models import PlantAnalysis
    analysis = PlantAnalysis.objects.filter(pk=analysis_id, owner=request.user).first()
    if analysis is None:
        return Response({'error': 'Analysis not found.'}, status=404)
    return Response(_analysis_response(analysis))
