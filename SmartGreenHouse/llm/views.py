
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

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
