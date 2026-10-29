import secrets

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from bson import ObjectId
from .models import SensorReading, EdgeNode, Plant
from .serializers import (
    SensorReadingSerializer,
    EdgeNodeSerializer,
    EdgeNodeRegisterSerializer,
)
from .authentication import EdgeNodeKeyAuthentication, generate_api_key, hash_api_key
from .scoping import owned_node_ids, readings_for_user, can_access_reading
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from .simulation import backfill_timestamp


def get_by_id(obj_id):

    try:
        object_id = ObjectId(obj_id)
    except Exception:
         return Response({"error":"Invalid sensor ID"},status=400)

    try:
        readings = SensorReading.objects.get(pk=object_id)
    except SensorReading.DoesNotExist:
        return Response(
                    {"error": "Sensor reading not found"},
                    status=404
                )
    return readings

@api_view(["GET"])
def health_check(request):
    return Response({
        "status": "ok",
        "message": "Greenhouse backend is running"
    })


def _client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@api_view(["POST","GET"])
@authentication_classes([JWTAuthentication, EdgeNodeKeyAuthentication])
@permission_classes([AllowAny])
def create_sensor_reading(request):
    if request.method == "GET":
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        readings = readings_for_user(request.user)
        serializer = SensorReadingSerializer(readings,many=True)
        return Response(serializer.data)

    node = getattr(request, "edge_node", None)
    recorded_at = backfill_timestamp(request, node)
    serializer = SensorReadingSerializer(data=request.data)
    if request.method == "POST":

        if serializer.is_valid():
            if node is not None:
                reading = serializer.save(
                    node_id=node.node_id,
                    zone_id=node.zone_id,
                    **({'timestamp': recorded_at} if recorded_at is not None else {}),
                )
                # Backfilling older readings must never move device freshness backwards.
                EdgeNode.objects.filter(pk=node.pk).filter(
                    Q(last_data_at__lt=reading.timestamp) | Q(last_data_at__isnull=True)
                ).update(last_data_at=reading.timestamp, updated_at=timezone.now())
            else:
                reading = serializer.save()

            return Response(
                SensorReadingSerializer(reading).data,
                status=201
            )

        return Response(
            serializer.errors,
            status=400
        )

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def sensor_reading_single(request, obj_id):
    try:
        object_id = ObjectId(obj_id)
    except Exception:
        return Response({"error":"Invalid sensor ID"},status=400)

    try:
        reading = SensorReading.objects.get(pk=object_id)
    except SensorReading.DoesNotExist:
        return Response(
            {"error": "Sensor reading not found"},
            status=404
        )

    if not can_access_reading(request.user, reading):
        return Response(
            {"error": "Sensor reading not found"},
            status=404
        )

    serializer = SensorReadingSerializer(reading)

    return Response(serializer.data)

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def sensor_reading_history(request, range):
    range_options = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    if range not in range_options:
        return Response(
            {
                "error":"Invalid range",
                "allowed_values": list(range_options.keys()),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    start_time = timezone.now()-range_options[range]

    readings = readings_for_user(request.user).filter(timestamp__gte = start_time).order_by("timestamp")

    serializer = SensorReadingSerializer(readings, many=True)

    return Response(serializer.data)

@api_view(['DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def del_sensor_reading(request,range=None,obj_id=None):
    if range != None:
        range_options = {
                "1h": timedelta(hours=1),
                "24h": timedelta(hours=24),
                "7d": timedelta(days=7),
                "30d": timedelta(days=30),
            }
        if range not in range_options:
            return Response({"error":"Invalid range",
                            "allowed_values": list(range_options.keys())},)
        start_time = timezone.now() - range_options[range]

        readings = readings_for_user(request.user).filter(timestamp__gte = start_time)
        serializer = SensorReadingSerializer(readings, many=True)
        data = serializer.data
        readings.delete()
        return Response(data,status=status.HTTP_200_OK)
    if obj_id != None:
        reading = get_by_id(obj_id)
        if isinstance(reading, Response):
            return reading
        if not can_access_reading(request.user, reading):
            return Response(
                {"error": "Sensor reading not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SensorReadingSerializer(reading)
        data = serializer.data
        reading.delete()
        return Response(data,status=status.HTTP_200_OK)

    return Response(
        {"error": "Please provide either range or obj_id"},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _provisioning_token_valid(request):
    configured = getattr(settings, "EDGE_PROVISIONING_TOKEN", "")
    if not configured:
        return False
    provided = request.META.get("HTTP_X_PROVISIONING_TOKEN")
    if not provided:
        provided = request.data.get("provisioning_token")
    if not provided:
        return False
    return secrets.compare_digest(str(provided), str(configured))


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
def register_edge(request):
    # Authorize via provisioning token OR an authenticated application user.
    owner = None
    if _provisioning_token_valid(request):
        authorized = True
    elif request.user and request.user.is_authenticated:
        authorized = True
        owner = request.user
    else:
        authorized = False
    if not authorized:
        return Response(
            {"error": "Provisioning token or authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = EdgeNodeRegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    node_id = serializer.validated_data["node_id"]
    if EdgeNode.objects.filter(node_id=node_id).exists():
        return Response(
            {"error": "A node with this node_id is already registered."},
            status=status.HTTP_409_CONFLICT,
        )

    api_key = generate_api_key()
    node = EdgeNode.objects.create(
        node_id=node_id,
        name=serializer.validated_data["name"],
        zone_id=serializer.validated_data["zone_id"],
        status=EdgeNode.Status.OFFLINE,
        api_key_hash=hash_api_key(api_key),
        owner=owner,
    )

    return Response(
        {
            "message": "Edge node registered successfully.",
            "node": EdgeNodeSerializer(node).data,
            # The plaintext key is returned exactly once, at registration.
            "api_key": api_key,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([EdgeNodeKeyAuthentication])
@permission_classes([AllowAny])
def edge_heartbeat(request):
    node = getattr(request, "edge_node", None)
    if node is None:
        return Response(
            {"error": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    node.last_heartbeat = timezone.now()
    node.ip_address = _client_ip(request)
    if node.status == EdgeNode.Status.OFFLINE:
        node.status = EdgeNode.Status.ONLINE
    node.save(update_fields=["last_heartbeat", "ip_address", "status", "updated_at"])

    return Response(
        {
            "status": node.status,
            "node_id": node.node_id,
            "last_heartbeat": node.last_heartbeat,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def list_edges(request):
    if request.user.is_superuser:
        nodes = EdgeNode.objects.all()
    else:
        nodes = EdgeNode.objects.filter(owner=request.user)
    serializer = EdgeNodeSerializer(nodes, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_plants(request):
    query = request.query_params.get('search', '').strip().casefold()
    if len(query) > 100:
        return Response({'error': 'Search is limited to 100 characters.'}, status=400)
    results = []
    if query:
        for plant in Plant.objects.filter(is_active=True).order_by('name'):
            if any(query in name.casefold() for name in [plant.name, plant.scientific_name, *plant.aliases]):
                results.append({'id': plant.pk, 'name': plant.name, 'scientific_name': plant.scientific_name})
    return Response({'results': results[:20]})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_sensor_reading(request):
    from .dashboard import latest_reading
    as_of = timezone.now()
    reading = latest_reading(request.user, as_of)
    return Response({'as_of': as_of, 'reading': SensorReadingSerializer(reading).data if reading else None})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sensor_history_summary(request, range):
    from .dashboard import RANGES, SnapshotQuery, history_snapshot
    if range not in RANGES:
        return Response({'error': 'Invalid range', 'allowed_values': list(RANGES)}, status=400)
    query = SnapshotQuery(data=request.query_params)
    if not query.is_valid():
        return Response({'errors': query.errors}, status=400)
    return Response(history_snapshot(request.user, range, query.validated_data.get('as_of', timezone.now())))
