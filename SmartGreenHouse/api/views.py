from rest_framework.decorators import api_view
from rest_framework.response import Response
from bson import ObjectId
from .models import SensorReading
from .serializers import SensorReadingSerializer
from datetime import timedelta
from django.utils import timezone
from rest_framework import status


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


@api_view(["POST","GET"])
def create_sensor_reading(request):
    if request.method == "GET":
        readings = SensorReading.objects.all()
        serializer = SensorReadingSerializer(readings,many=True)
        return Response(serializer.data)
    
    serializer = SensorReadingSerializer(data=request.data)
    if request.method == "POST":
        
        if serializer.is_valid():
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

    serializer = SensorReadingSerializer(reading)

    return Response(serializer.data)

@api_view(['GET'])
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
    
    readings = SensorReading.objects.filter(timestamp__gte = start_time).order_by("timestamp")

    serializer = SensorReadingSerializer(readings, many=True)
    
    return Response(serializer.data)

@api_view(['DELETE'])
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
        
        readings = SensorReading.objects.filter(timestamp__gte = start_time)
        serializer = SensorReadingSerializer(readings, many=True)
        data = serializer.data
        readings.delete()
        return Response(data,status=status.HTTP_200_OK)
    if obj_id != None:
        readings = get_by_id(obj_id)
        serializer = SensorReadingSerializer(readings)
        data = serializer.data
        readings.delete()
        return Response(data,status=status.HTTP_200_OK)
    
    return Response(
        {"error": "Please provide either range or obj_id"},
        status=status.HTTP_400_BAD_REQUEST,
    )
    