"""Read-only, user-scoped snapshots for the single-device dashboard."""
from datetime import timedelta
import json

from rest_framework.utils.encoders import JSONEncoder
from django.utils import timezone
from rest_framework import serializers

from .scoping import readings_for_user
from .serializers import SensorReadingSerializer

METRICS = ('temperature', 'humidity', 'soil_moisture', 'light')
UNITS = {'temperature': '°C', 'humidity': '%', 'soil_moisture': '%', 'light': 'lux'}
RANGES = {'7d': (168, 6), '30d': (720, 24)}


def json_copy(value):
    return json.loads(json.dumps(value, cls=JSONEncoder))


class SnapshotQuery(serializers.Serializer):
    as_of = serializers.DateTimeField(required=False)

    def validate_as_of(self, value):
        if value > timezone.now() + timedelta(seconds=1):
            raise serializers.ValidationError('Snapshot time cannot be in the future.')
        return value


def latest_reading(user, as_of):
    return readings_for_user(user).filter(timestamp__lte=as_of).order_by('-timestamp', '-pk').first()


def history_snapshot(user, range_name, as_of):
    hours, interval_hours = RANGES[range_name]
    start = as_of - timedelta(hours=hours)
    step = timedelta(hours=interval_hours)
    points = []
    for i in range(hours // interval_hours):
        left = start + i * step
        points.append({
            'timestamp': left + step / 2, 'window_start': left, 'window_end': left + step,
            'sample_count': 0, **{key: None for key in METRICS},
            'minimum': {key: None for key in METRICS},
            'maximum': {key: None for key in METRICS},
        })
    rows = readings_for_user(user).filter(timestamp__gte=start, timestamp__lte=as_of)
    for row in rows.values('timestamp', *METRICS).iterator(chunk_size=1000):
        index = min(int((row['timestamp'] - start) / step), len(points) - 1)
        point = points[index]
        count = point['sample_count']
        for key in METRICS:
            value = row[key]
            point[key] = value if count == 0 else point[key] + (value - point[key]) / (count + 1)
            point['minimum'][key] = value if count == 0 else min(point['minimum'][key], value)
            point['maximum'][key] = value if count == 0 else max(point['maximum'][key], value)
        point['sample_count'] += 1
    latest = latest_reading(user, as_of)
    return json_copy({
        'range': range_name, 'as_of': as_of, 'window_start': start, 'window_end': as_of,
        'interval_hours': interval_hours, 'units': UNITS,
        'latest_reading': SensorReadingSerializer(latest).data if latest else None,
        'points': points,
    })
