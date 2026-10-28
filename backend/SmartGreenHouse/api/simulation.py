"""Explicitly enabled historical ingestion for allowlisted virtual devices."""
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied


def backfill_timestamp(request, node):
    if 'recorded_at' not in request.data:
        return None
    configured = getattr(settings, 'SIMULATION_INGESTION_TOKEN', '')
    allowed = getattr(settings, 'SIMULATION_NODE_IDS', [])
    provided = request.headers.get('X-Simulation-Token', '')
    if (not configured or node is None or node.node_id not in allowed
            or not secrets.compare_digest(provided, configured)):
        raise PermissionDenied('Historical ingestion is disabled or not authorized for this device.')
    value = serializers.DateTimeField().run_validation(request.data['recorded_at'])
    now = timezone.now()
    if not now - timedelta(days=31) <= value <= now:
        raise serializers.ValidationError({'recorded_at': 'Must be within the past 31 days and not in the future.'})
    return value
