# Greenhouse API Documentation for Frontend Developers

## 1. Base URL

Set `API_BASE_URL` to the root URL of the backend server:

```txt
${API_BASE_URL}
```

For example:

```txt
http://localhost:8000
```

All endpoints in this document include the `/api/` prefix.

---

## 2. Sensor Reading Data

### `SensorReading`

```json
{
  "id": "string",
  "temperature": 25.4,
  "humidity": 60.5,
  "soil_moisture": 45.1,
  "light": 800,
  "timestamp": "2026-10-10T12:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string | Reading ID, returned as a string |
| `temperature` | number | Temperature |
| `humidity` | number | Humidity |
| `soil_moisture` | number | Soil moisture |
| `light` | number | Light intensity |
| `timestamp` | string | Reading timestamp in ISO 8601 format |

The backend generates `id` and `timestamp`; clients do not need to send these fields when creating a reading.

---

## 3. Sensor Endpoints

### 3.1 Health Check

#### `GET /api/health_check/`

Checks whether the backend is running.

Example response:

```json
{
  "status": "ok",
  "message": "Greenhouse backend is running"
}
```

### 3.2 Get All Sensor Readings

#### `GET /api/sensors/`

Returns all sensor readings as an array.

Example response:

```json
[
  {
    "id": "672c0a5f9f4d1d2e3b4a5c6d",
    "temperature": 24.5,
    "humidity": 58.2,
    "soil_moisture": 42.7,
    "light": 760,
    "timestamp": "2026-10-10T12:00:00Z"
  }
]
```

### 3.3 Create a Sensor Reading

#### `POST /api/sensors/`

Example request body:

```json
{
  "temperature": 26.3,
  "humidity": 61.0,
  "soil_moisture": 40.5,
  "light": 820
}
```

On success, returns the created reading with status `201 Created`.

### 3.4 Get One Sensor Reading

#### `GET /api/sensors/:id/`

Replace `:id` with the reading ID.

Example:

```txt
GET /api/sensors/672c0a5f9f4d1d2e3b4a5c6d/
```

Returns one `SensorReading` object.

Possible errors:

| Status | Description |
|---|---|
| `400` | Invalid ID format |
| `404` | Reading not found |

Example error body:

```json
{
  "error": "Invalid sensor ID"
}
```

### 3.5 Get Historical Readings

#### `GET /api/sensors/history/:range/`

Supported `:range` values:

| Value | Time period |
|---|---|
| `1h` | Last hour |
| `24h` | Last 24 hours |
| `7d` | Last 7 days |
| `30d` | Last 30 days |

Example:

```txt
GET /api/sensors/history/24h/
```

Returns matching readings ordered from oldest to newest.

An unsupported range returns status `400`:

```json
{
  "error": "Invalid range",
  "allowed_values": ["1h", "24h", "7d", "30d"]
}
```

### 3.6 Delete Readings by Time Range

#### `DELETE /api/sensors/history/del/:range/`

Example:

```txt
DELETE /api/sensors/history/del/24h/
```

On success, returns an array containing the deleted readings.

For an unsupported range, the response body contains `error` and `allowed_values`. The current backend does not explicitly assign an error status in this case, so the response may still have status `200`.

### 3.7 Delete One Sensor Reading

#### `DELETE /api/sensors/del/:id/`

Example:

```txt
DELETE /api/sensors/del/672c0a5f9f4d1d2e3b4a5c6d/
```

On success, returns the deleted reading object.

**Implementation note:** The current delete view does not correctly handle invalid or nonexistent IDs. Do not rely on a consistent `400` or `404` response for these cases.

---

## 4. LLM Endpoints

The LLM endpoints use Ollama and sensor data as context. They accept and return JSON.

### 4.1 Generate a Greenhouse Recommendation

#### `POST /api/llm/recommend/`

Request body:

| Field | Type | Required | Default | Constraints |
|---|---|---:|---|---|
| `hours` | integer | No | `24` | Must be between `1` and `720`, inclusive |
| `language` | string | No | `"en"` | Allowed values: `"en"` or `"zh"` |

Example request:

```json
{
  "hours": 24,
  "language": "en"
}
```

`hours` controls the time window for historical readings in the context. The context includes the latest reading and up to 50 readings from that window.

Example successful response (`200 OK`):

```json
{
  "status": "success",
  "recommendation": "The latest reading shows ...",
  "context": {
    "latest_reading": {
      "id": "672c0a5f9f4d1d2e3b4a5c6d",
      "temperature": 24.5,
      "humidity": 58.2,
      "soil_moisture": 42.7,
      "light": 760,
      "timestamp": "2026-10-10T12:00:00Z"
    },
    "history_hours": 24,
    "historical_readings": []
  },
  "generated_at": "2026-10-10T12:10:00Z"
}
```

If there are no sensor readings, the endpoint still returns a successful response with a message explaining that readings are unavailable; the context has `latest_reading: null` and an empty `historical_readings` array.

Validation errors return `400 Bad Request` in this shape:

```json
{
  "errors": {
    "hours": ["Ensure this value is less than or equal to 720."]
  }
}
```

If the backend cannot communicate with Ollama or Ollama returns an invalid/empty response, the endpoint returns `503 Service Unavailable`:

```json
{
  "error": "Could not communicate with Ollama. Check that Ollama is running and the model is available."
}
```

### 4.2 Chat with the Greenhouse Assistant

#### `POST /api/llm/chat/`

Request body:

| Field | Type | Required | Default | Constraints |
|---|---|---:|---|---|
| `message` | string | Yes | — | Must not be blank; maximum 2,000 characters |
| `language` | string | No | `"en"` | Allowed values: `"en"` or `"zh"` |

Leading and trailing whitespace is removed from `message` during validation.

Example request:

```json
{
  "message": "What do the latest sensor readings suggest?",
  "language": "en"
}
```

The chat endpoint supplies the latest sensor reading and up to 50 readings from the last 24 hours as context.

Example successful response (`200 OK`):

```json
{
  "status": "success",
  "reply": "Based on the available readings ...",
  "context_used": {
    "latest_reading": true,
    "historical_readings": true
  },
  "generated_at": "2026-10-10T12:10:00Z"
}
```

`context_used` indicates whether a latest reading and historical readings were available; it does not include the readings themselves.

Validation errors return `400 Bad Request`:

```json
{
  "errors": {
    "message": ["This field may not be blank."]
  }
}
```

If Ollama is unavailable or returns an invalid/empty response, the endpoint returns `503 Service Unavailable` with an `error` field.

### 4.3 Language Behavior Note

Both LLM request serializers currently accept `"en"` and `"zh"`. However, the service currently maps `"en"` to English and every other accepted value (including `"zh"`) to Swedish. Until the backend mapping is corrected, sending `"zh"` may produce Swedish rather than Chinese.

---

## 5. Common HTTP Status Codes

| Status | Meaning |
|---|---|
| `200` | Request succeeded |
| `201` | Sensor reading created |
| `400` | Invalid request data or unsupported range |
| `404` | Sensor reading not found |
| `405` | HTTP method not allowed |
| `503` | LLM service unavailable or returned an invalid response |

Most explicit API errors use a JSON body with an `error` field, except LLM request validation errors, which use an `errors` field. See the endpoint details for current implementation caveats.

---

## 6. Endpoint Reference

```txt
Base URL: ${API_BASE_URL}

GET    /api/health_check/
GET    /api/sensors/
POST   /api/sensors/
GET    /api/sensors/:id/
GET    /api/sensors/history/:range/
DELETE /api/sensors/history/del/:range/
DELETE /api/sensors/del/:id/
POST   /api/llm/recommend/
POST   /api/llm/chat/
```

This document reflects the current backend routes and behavior. Update it when the API or request/response contracts change.





## 7.LLM implementation

Find the SmartGreenHouse/llm/service.py， to integrate your own Ollama Model.

```python
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

```

And related Prompts also store in `/llm/service.py`