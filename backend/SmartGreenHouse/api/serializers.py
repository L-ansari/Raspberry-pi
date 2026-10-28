from rest_framework import serializers
from django.conf import settings
from .models import SensorReading, EdgeNode


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
            "node_id",
            "zone_id",
        ]
        read_only_fields = ["id", "timestamp", "node_id", "zone_id"]

    def get_id(self, obj):
        # print("obj:", obj)
        # print("obj.id:", obj.id)
        # print("obj.pk:", obj.pk)
        # print("obj.__dict__:", obj.__dict__)
        return str(obj.id)


class EdgeNodeSerializer(serializers.ModelSerializer):
    """Non-sensitive device record. Credentials are intentionally excluded."""

    owner = serializers.CharField(
        source="owner.username", read_only=True, allow_null=True
    )

    class Meta:
        model = EdgeNode
        fields = [
            "node_id",
            "name",
            "zone_id",
            "status",
            "owner",
            "ip_address",
            "last_heartbeat",
            "last_data_at",
            "created_at",
            "updated_at",
        ]


class EdgeNodeRegisterSerializer(serializers.Serializer):
    node_id = serializers.CharField(max_length=128)
    name = serializers.CharField(max_length=128)
    zone_id = serializers.CharField(max_length=128)
    provisioning_token = serializers.CharField(
        required=False,
        write_only=True,
        allow_blank=True,
    )

    def validate_zone_id(self, value):
        allowed = getattr(settings, "EDGE_ALLOWED_ZONES", [])
        if allowed and value not in allowed:
            raise serializers.ValidationError(
                f"Zone {value!r} is not permitted. "
                f"Allowed zones: {', '.join(allowed)}"
            )
        return value