import json
import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from api.models import SensorReading
from api.serializers import SensorReadingSerializer

class OllamaServiceError(Exception):
    """Raised when the Ollama service cannot return a valid response."""

def get_sensor_context(hours=24, limit=50):
    latest_reading = (SensorReading.objects.order_by("-timestamp").first())
    
    start_time = timezone.now()-timedelta(hours=hours)
    
    history = (SensorReading.objects.filter(timestamp__gte = start_time).order_by("-timestamp")[:limit])
    
    latest_data = None
    
    if latest_reading is not None:
        latest_data = SensorReadingSerializer(latest_reading).data
    
    history_data = SensorReadingSerializer(history,many=True).data
    
    return{
        "latest_reading":latest_data,
        "history_hours":hours,
        "historical_readings":list(history_data)
    }
    
def call_ollama(messages):
    """
    Send a chat request to the locally running Ollama server.
    """

    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()

        content = result.get("message", {}).get("content")

        if not isinstance(content, str) or not content.strip():
            raise OllamaServiceError(
                "Ollama returned an empty response."
            )

        return content.strip()

    except requests.RequestException as exc:
        raise OllamaServiceError(
            "Could not communicate with Ollama. "
            "Check that Ollama is running and the model is available."
        ) from exc

    except (ValueError, TypeError) as exc:
        raise OllamaServiceError(
            "Ollama returned an invalid response."
        ) from exc


def generate_recommendation(hours=24, language="en"):
    """
    Generate greenhouse recommendations based on sensor data.
    """

    context = get_sensor_context(hours=hours)

    if context["latest_reading"] is None:
        return {
            "recommendation": (
                "No sensor readings are available yet. "
                "Please send sensor data before requesting recommendations."
            ),
            "context": context,
        }

    language_name = "English" if language == "en" else "Swedish"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a smart greenhouse assistant. "
                "Analyze the supplied sensor readings and provide "
                "practical, cautious recommendations. "
                "Use only the supplied data for claims about measured "
                "conditions. Do not invent readings, trends, or causes. "
                "If the data is insufficient, say so. "
                "Do not assume a universal ideal temperature or humidity "
                "without knowing the plant species and growing conditions. "
                "Do not claim that you have operated any hardware. "
                f"Respond in {language_name}."
            ),
        },
        {
            "role": "user",
            "content": (
                "Analyze the following greenhouse sensor data and provide "
                "a short summary, notable observations, and actionable "
                "suggestions.\n\n"
                + json.dumps(context, ensure_ascii=False, default=str)
            ),
        },
    ]

    recommendation = call_ollama(messages)

    return {
        "recommendation": recommendation,
        "context": context,
    }


def chat_with_greenhouse(message, language="en"):
    """
    Answer a user question using recent greenhouse sensor data.
    """

    context = get_sensor_context(hours=24)

    language_name = "English" if language == "en" else "Swedish"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful smart greenhouse assistant. "
                "Answer the user's question using the supplied sensor data "
                "when relevant. Distinguish measured facts from possible "
                "explanations. Never invent sensor readings or claim "
                "certainty when the data does not support it. "
                "If information is missing, explain what additional data "
                "would help. Do not claim to control any hardware. "
                f"Respond in {language_name}."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Sensor context:\n"
                f"{json.dumps(context, ensure_ascii=False, default=str)}"
                f"\n\nUser question:\n{message}"
            ),
        },
    ]

    reply = call_ollama(messages)

    return {
        "reply": reply,
        "context_used": {
            "latest_reading": context["latest_reading"] is not None,
            "historical_readings": bool(
                context["historical_readings"]
            ),
        },
    }
