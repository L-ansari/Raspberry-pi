from rest_framework import serializers


class RecommendationRequestSerializer(serializers.Serializer):
    hours = serializers.IntegerField(
        required=False,
        default=24,
        min_value=1,
        max_value=720,
    )

    language = serializers.ChoiceField(
        choices=["en", "zh"],
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
        choices=["en", "zh"],
        required=False,
        default="en",
    )
