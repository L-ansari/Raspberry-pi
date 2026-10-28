from rest_framework import serializers


class RecommendationRequestSerializer(serializers.Serializer):
    hours = serializers.IntegerField(
        required=False,
        default=24,
        min_value=1,
        max_value=720,
    )

    language = serializers.ChoiceField(
        choices=["en"],
        required=False,
        default="en",
    )


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(
        required=True,
        max_length=2000,
        allow_blank=False,
        trim_whitespace=True,
    )

    language = serializers.ChoiceField(
        choices=["en"],
        required=False,
        default="en",
    )


class StatusRequestSerializer(serializers.Serializer):
    plant_id = serializers.SlugField()
    reading_id = serializers.CharField(max_length=100)


class AnalysisRequestSerializer(StatusRequestSerializer):
    range = serializers.ChoiceField(choices=['7d', '30d'])
    as_of = serializers.DateTimeField()
    request_id = serializers.UUIDField()


class SensorStatusesSerializer(serializers.Serializer):
    temperature = serializers.ChoiceField(choices=['normal', 'low', 'high', 'unknown'])
    humidity = serializers.ChoiceField(choices=['normal', 'low', 'high', 'unknown'])
    soil_moisture = serializers.ChoiceField(choices=['normal', 'low', 'high', 'unknown'])
    light = serializers.ChoiceField(choices=['normal', 'low', 'high', 'unknown'])


class AlertResultSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=80)
    title = serializers.CharField(max_length=150)
    severity = serializers.ChoiceField(choices=['info', 'warning', 'critical'])
    message = serializers.CharField(max_length=4000)


class RecommendationResultSerializer(serializers.Serializer):
    suggestion = serializers.CharField(max_length=4000)
    explanation = serializers.CharField(max_length=8000)


class AnalysisResultSerializer(serializers.Serializer):
    alerts = AlertResultSerializer(many=True, max_length=10)
    recommendation = RecommendationResultSerializer()
