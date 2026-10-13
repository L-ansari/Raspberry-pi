from rest_framework import serializers
from .models import SensorReading


class SensorReadingSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()

    class Meta:
        model = SensorReading
        fields = [
            "id",
            "temperature",
            "humidity",
            "soil_moisture",
            "light",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]

    def get_id(self, obj):
        # print("obj:", obj)
        # print("obj.id:", obj.id)
        # print("obj.pk:", obj.pk)
        # print("obj.__dict__:", obj.__dict__)
        return str(obj.id)