from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

# Create your models here.


class SensorReading(models.Model):
    temperature = models.FloatField()
    humidity = models.FloatField()
    soil_moisture = models.FloatField()
    light = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)
    # Source node and zone, set from authenticated device identity. Null for
    # legacy clients that submit readings without a device association.
    node_id = models.CharField(max_length=128, null=True, blank=True)
    zone_id = models.CharField(max_length=128, null=True, blank=True)

    def __str__(self):
        return f"Sensor reading at {self.timestamp}"


class EdgeNode(models.Model):
    """A registered physical edge device (e.g. Raspberry Pi) in a greenhouse zone."""

    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        DISABLED = "disabled", "Disabled"

    node_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=128)
    zone_id = models.CharField(max_length=128)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OFFLINE,
    )
    ip_address = models.CharField(max_length=64, null=True, blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    last_data_at = models.DateTimeField(null=True, blank=True)
    # SHA-256 hex digest of the device's API key. Never returned to clients.
    api_key_hash = models.CharField(max_length=128)
    # Owning user. Null for nodes provisioned via the shared provisioning token
    # (or after the owner account is deleted); such nodes are visible only to
    # superusers.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edge_nodes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.node_id})"


class Plant(models.Model):
    id = models.SlugField(primary_key=True, max_length=80)
    name = models.CharField(max_length=100)
    scientific_name = models.CharField(max_length=150)
    aliases = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PlantAnalysis(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT)
    range = models.CharField(max_length=3)
    snapshot = models.JSONField()
    result = models.JSONField()
    model_name = models.CharField(max_length=150)
    schema_version = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
