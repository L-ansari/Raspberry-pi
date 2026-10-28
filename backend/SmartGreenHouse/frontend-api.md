# Greenhouse API Documentation for Frontend Developers

Updated: 2026-10-28. The dashboard assumes one device and English-only interactions.

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
  "timestamp": "2026-10-10T12:00:00Z",
  "node_id": "pi-zone-1",
  "zone_id": "zone-1"
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
| `node_id` | string \| null | Source edge node; `null` for legacy/anonymous submissions |
| `zone_id` | string \| null | Source greenhouse zone; `null` for legacy/anonymous submissions |

The backend generates `id`, `timestamp`, `node_id`, and `zone_id`. Clients do not send `node_id` or
`zone_id`; the backend derives them from the authenticated device identity. Legacy clients that do
not authenticate can keep submitting the four sensor fields unchanged — those readings have
`node_id`/`zone_id` set to `null`.

---

## 3. Sensor Endpoints

> **Authorization.** Reading, history, and delete endpoints below require an authenticated user
> (`Authorization: Bearer <access-token>`). A user only sees/deletes readings from the edge nodes
> they own; superusers see everything. Cross-user access returns `404`. Uploading a reading
> (`POST /api/sensors/`) remains open to legacy clients and device API keys.

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

Returns all sensor readings as an array. Requires an authenticated user; returns only the readings
from the caller's owned nodes (all readings for a superuser).

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

Returns one `SensorReading` object. Requires an authenticated user; accessing another user's
reading returns `404`.

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

Returns matching readings ordered from oldest to newest, scoped to the caller's owned nodes.
Requires an authenticated user.

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

On success, returns an array containing the deleted readings. Requires an authenticated user; only
the caller's own readings are deleted (all readings for a superuser).

For an unsupported range, the response body contains `error` and `allowed_values`. The current backend does not explicitly assign an error status in this case, so the response may still have status `200`.

### 3.7 Delete One Sensor Reading

#### `DELETE /api/sensors/del/:id/`

Example:

```txt
DELETE /api/sensors/del/672c0a5f9f4d1d2e3b4a5c6d/
```

On success, returns the deleted reading object. Requires an authenticated user; deleting another
user's reading returns `404`.

---

## 4. LLM Endpoints

The LLM endpoints use Ollama and sensor data as context. They accept and return JSON. Both require
an authenticated user (`Authorization: Bearer <access-token>`), and they use only the calling
user's own readings as context.

### 4.1 Generate a Greenhouse Recommendation

#### `POST /api/llm/recommend/`

Request body:

| Field | Type | Required | Default | Constraints |
|---|---|---:|---|---|
| `hours` | integer | No | `24` | Must be between `1` and `720`, inclusive |
| `language` | string | No | `"en"` | Allowed value: `"en"` |

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
| `language` | string | No | `"en"` | Allowed value: `"en"` |

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

### 4.3 Language

The application is English-only. Omit `language` or send `"en"`; other values return `400`.

---

## 5. User and Authentication Endpoints

User endpoints are mounted under `/api/users/`. JWT authentication is configured for Django REST Framework.

### 5.1 Register a User

#### `POST /api/users/register/`

Request body:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `username` | string | Yes | Must be accepted by the configured Django user model |
| `email` | string | Yes | Must be accepted by the configured Django user model |
| `password` | string | Yes | At least 8 characters |

Example request:

```json
{
  "username": "greenhouse_user",
  "email": "user@example.com",
  "password": "a-secure-password"
}
```

On success, returns `201 Created`:

```json
{
  "message": "User registered successfully.",
  "user": {
    "id": "user-id",
    "username": "greenhouse_user",
    "email": "user@example.com",
    "first_name": "",
    "last_name": "",
    "date_joined": "2026-10-10T12:00:00Z"
  }
}
```

The password is write-only and is not returned. Validation failures return `400 Bad Request` with an `errors` object:

```json
{
  "errors": {
    "password": ["Ensure this field has at least 8 characters."]
  }
}
```

### 5.2 Log In and Obtain JWT Tokens

#### `POST /api/users/login/`

This endpoint uses Simple JWT's token-obtain-pair view.

Request body:

```json
{
  "username": "greenhouse_user",
  "password": "a-secure-password"
}
```

Successful response (`200 OK`):

```json
{
  "refresh": "<refresh-token>",
  "access": "<access-token>"
}
```

Use the access token for authenticated requests:

```http
Authorization: Bearer <access-token>
```

### 5.3 Refresh an Access Token

#### `POST /api/users/token/refresh/`

Request body:

```json
{
  "refresh": "<refresh-token>"
}
```

Successful response (`200 OK`) includes a new access token:

```json
{
  "access": "<new-access-token>"
}
```

### 5.4 Get the Current User

#### `GET /api/users/me/`

Returns the current user's profile:

```json
{
  "id": "user-id",
  "username": "greenhouse_user",
  "email": "user@example.com",
  "first_name": "",
  "last_name": "",
  "date_joined": "2026-10-10T12:00:00Z"
}
```

Send the access token in the `Authorization` header. The endpoint enforces authentication
(`IsAuthenticated`): unauthenticated requests are rejected with `401`/`403`. The view is implemented
as a `GET` endpoint; profile updates are not provided by this route.

---

## 6. Common HTTP Status Codes

| Status | Meaning |
|---|---|
| `200` | Request succeeded |
| `201` | Sensor reading created |
| `400` | Invalid request data or unsupported range |
| `404` | Sensor reading not found |
| `405` | HTTP method not allowed |
| `503` | LLM service unavailable or returned an invalid response |

Error response shapes vary by endpoint. Sensor and LLM service errors commonly use an `error` field; request validation and registration errors use an `errors` field. See the endpoint details for current implementation caveats.

---

## 7. Endpoint Reference

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
POST   /api/users/register/
POST   /api/users/login/
POST   /api/users/token/refresh/
GET    /api/users/me/
POST   /api/edges/register/
POST   /api/edges/heartbeat/
GET    /api/edges/
```

This document reflects the current backend routes and behavior. Update it when the API or request/response contracts change.

---

## 8. Edge Node Endpoints

Edge nodes are physical devices (e.g. Raspberry Pi) registered per greenhouse zone. Each device is
provisioned with a per-node API key and authenticates with the `X-Edge-Key` header. The key is
separate from application-user JWTs (which use `Authorization: Bearer`).

### 8.1 Register a Node

#### `POST /api/edges/register/`

Registration is authorized by **either** the shared provisioning token **or** an authenticated
application user (JWT). When registered with a JWT, the authenticated user becomes the node's
`owner`; when registered with the provisioning token, the node has no owner (`owner: null`) and is
visible only to superusers.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `node_id` | string | Yes | Unique device identifier, max 128 chars |
| `name` | string | Yes | Human-readable name, max 128 chars |
| `zone_id` | string | Yes | Must be in the configured allowed zones |
| `provisioning_token` | string | No | Shared provisioning secret (alternative to JWT) |

Example request (provisioning token):

```json
{
  "node_id": "pi-zone-1",
  "name": "Raspberry Pi Zone 1",
  "zone_id": "zone-1",
  "provisioning_token": "your-provisioning-token"
}
```

The provisioning token may alternatively be sent as the `X-Provisioning-Token` header.

Successful response (`201 Created`) — note the `api_key` is returned **only once**, at the top
level (it is never part of the node record):

```json
{
  "message": "Edge node registered successfully.",
  "node": {
    "node_id": "pi-zone-1",
    "name": "Raspberry Pi Zone 1",
    "zone_id": "zone-1",
    "status": "offline",
    "owner": "<username-or-null>",
    "ip_address": null,
    "last_heartbeat": null,
    "last_data_at": null,
    "created_at": "2026-10-10T12:00:00Z",
    "updated_at": "2026-10-10T12:00:00Z"
  },
  "api_key": "<one-time-api-key>"
}
```

Duplicate `node_id` returns `409 Conflict`; an invalid `zone_id` returns `400` with an `errors`
object; missing/invalid authorization returns `401`.

### 8.2 Send a Heartbeat

#### `POST /api/edges/heartbeat/`

Authenticated with the device's API key via `X-Edge-Key`. No request body is required.

Example request:

```http
POST /api/edges/heartbeat/
X-Edge-Key: <api-key>
```

Successful response (`200 OK`):

```json
{
  "status": "online",
  "node_id": "pi-zone-1",
  "last_heartbeat": "2026-10-10T12:10:00Z"
}
```

Unknown or disabled devices receive `401 Unauthorized`.

### 8.3 List Nodes

#### `GET /api/edges/`

Authenticated with an application-user JWT (`Authorization: Bearer <access-token>`). A user sees
only the nodes they own; a superuser sees all nodes (including unowned ones).

Successful response (`200 OK`) is an array of non-sensitive node records:

```json
[
  {
    "node_id": "pi-zone-1",
    "name": "Raspberry Pi Zone 1",
    "zone_id": "zone-1",
    "status": "online",
    "owner": "greenhouse_user",
    "ip_address": "192.168.1.10",
    "last_heartbeat": "2026-10-10T12:10:00Z",
    "last_data_at": "2026-10-10T12:09:00Z",
    "created_at": "2026-10-10T12:00:00Z",
    "updated_at": "2026-10-10T12:10:00Z"
  }
]
```

`owner` is the owning user's username, or `null` for unowned nodes (superuser-only). API keys and
credential hashes are never returned. Unauthenticated requests are rejected.

### 8.4 Heartbeat interval and offline detection

Nodes send heartbeats independently of sensor uploads. The backend marks a node `offline` when its
`last_heartbeat` exceeds the configured timeout (default 60 seconds) via the management command:

```bash
python manage.py check_edge_health
```

This command is not self-scheduling; run it periodically (e.g. cron/systemd timer). Disabled nodes
are never changed, and heartbeat freshness is independent of sensor-data freshness.


## 9. Single-device dashboard API

All endpoints in this section require the application user's Bearer JWT. Existing per-user device ownership restrictions still apply. The frontend has no device selector and sends no device ID. This version assumes one device per dashboard; it does not combine plant selections across devices.

### 9.1 Plant search

`GET /api/plants/?search=tomato`

```json
{"results":[{"id":"tomato","name":"Tomato","scientific_name":"Solanum lycopersicum"}]}
```

The shared read-only catalogue is populated by `python manage.py seed_plants`. It contains 20 English-language plants, with stable slug IDs and English aliases. Seeding is idempotent. Search is case-insensitive across common names, scientific names and aliases, limited to 100 input characters and 20 results. Empty queries and unmatched searches return `results: []`. The frontend caches successful searches for five minutes; failed searches use explicitly labeled demo plants.

### 9.2 Current reading

`GET /api/sensors/current/`

```json
{"as_of":"2026-10-28T10:00:00Z","reading":{"id":"reading-id","temperature":24.6,"humidity":51,"soil_moisture":22,"light":620,"timestamp":"2026-10-28T09:59:00Z","node_id":"default-node","zone_id":"zone-1"}}
```

The backend chooses the latest accessible record by timestamp and primary key, bounded by `as_of`. No readings returns `reading: null`. This endpoint does not wait for a model. Readings use Celsius, relative humidity %, soil moisture %, and lux; the ingestion source must provide calibrated values in these units. The measurement timestamp is displayed separately from the request time; no automatic stale-data threshold is assumed.

### 9.3 Transient plant status

`POST /api/llm/status/`

```json
{"plant_id":"tomato","reading_id":"reading-id"}
```

```json
{"plant_id":"tomato","reading_id":"reading-id","sensor_statuses":{"temperature":"normal","humidity":"normal","soil_moisture":"low","light":"unknown"}}
```

The backend reads the plant and authorized reading, then asks Ollama for structured JSON. Each metric must be `normal`, `low`, `high` or `unknown`. Insufficient context should yield `unknown`. The result is validated and returned without saving it. Invalid model output or an unavailable model returns `503`; inactive plants and inaccessible readings return `404`. Frontend thresholds are not used. On assessment failure, real readings remain visible with unavailable labels, not fabricated normal labels.

### 9.4 Historical summaries

`GET /api/sensors/history-summary/7d/?as_of=<ISO timestamp>`

`GET /api/sensors/history-summary/30d/?as_of=<ISO timestamp>`

`as_of` is optional; the dashboard passes the value returned by current. Future timestamps are rejected. The response contains `range`, `as_of`, `window_start`, `window_end`, `interval_hours`, `units`, `latest_reading` and `points`.

- `7d`: 28 consecutive six-hour buckets covering the preceding 168 hours.
- `30d`: 30 consecutive 24-hour buckets covering the preceding 720 hours.
- Each point contains a midpoint `timestamp`, `window_start`, `window_end`, `sample_count`, the four metric averages, and `minimum`/`maximum` objects keyed by metric.
- Empty buckets contain `null` averages and extrema, with zero samples. They are not interpolated or treated as zero.
- Bounds are relative to `as_of`, not calendar-day boundaries. A reading exactly on an internal boundary belongs to the next bucket; a reading exactly at the overall end belongs to the final bucket.
- All records in the window contribute through a streaming aggregation; there is no last-50-record truncation.

The four charts use numeric time axes, linear average curves and hover details for extrema and sample counts. Percentage axes span 0–100, light begins at zero, and temperature uses an automatic domain. The original raw history endpoints remain unchanged.

### 9.5 Create and save a plant analysis

`POST /api/plant-analysis/`

```json
{"plant_id":"tomato","range":"7d","reading_id":"reading-id","as_of":"2026-10-28T10:00:00Z","request_id":"29ebfe69-c02b-4dda-908d-949ae76b8dc7"}
```

`request_id` must be a UUID. Retrying the same logical operation must reuse it. `reading_id` must identify the latest authorized reading at `as_of`; mismatch returns `409`. Invalid range, future time or malformed input returns `400`.

The backend supplies the plant identity, latest reading, units and whole-window summaries to Ollama. It validates this output before saving:

```json
{"alerts":[{"type":"LOW_SOIL_MOISTURE","title":"Low soil moisture","severity":"warning","message":"Check the soil before watering."}],"recommendation":{"suggestion":"Inspect the soil.","explanation":"The supplied measurements suggest checking soil moisture."}}
```

The text above is a structural example, not a measured assessment. `alerts` may be empty, with at most ten entries. Severity is `info`, `warning` or `critical`. Suggestion and explanation are required nonblank strings. Invalid or incomplete model output returns `503` and is not saved. This first version saves only complete successful analyses; it does not silently treat an incomplete result as normal.

On success, `201` returns `analysis_id`, `plant_id`, `range`, `snapshot`, `alerts`, `recommendation`, `model_name`, `schema_version` and `generated_at`. The immutable saved snapshot includes the plant name/scientific name at analysis time, actual latest reading values, time bounds, all buckets and units. No instantaneous status labels are saved.

A repeated completed request with the same ID and matching context returns its saved result with `200`. Reusing an ID for a different context returns `409`. If no historical samples are available, `200` returns `status: no_data`, `alerts: null`, `recommendation: null` and the snapshot; no analysis is saved. An empty alert array is reserved for a valid assessment with no supported alerts.

### 9.6 Retrieve a saved analysis

`GET /api/plant-analysis/<analysis-id>/`

Only the creating user may retrieve a record. Another user's record returns `404`; the owner is derived from authentication, never from request JSON. The saved reading values and LLM input summaries remain available even if source readings are later removed. Deleting an account removes its analyses; plants referenced by analyses are protected from deletion.

## 10. Dashboard refresh and failure behavior

- Login restores a JWT session; logout clears credentials, saved plant choices and mounted dashboard/chat state. Refresh-token failure returns to login. Passwords are never saved by the frontend.
- Initial load and Refresh data request current once, then summaries using the same `as_of`.
- Selecting a plant triggers transient status and historical analysis. Switching week/month changes summary and historical analysis, but not instantaneous labels.
- The selected plant is saved per user in tab session storage and restored on reload. Backend analysis revalidates the ID. Chat remains independent of plant choice and chart range.
- No automatic polling, device selector, registration page or hardware-control UI is included.
- Authentication failures do not fall back to demo mode. Other service/network failures may display clearly labeled demo content; successful empty data stays empty. Demo analyses are not saved.
- current, summary and plant search use short frontend timeouts; model requests allow up to 130 seconds while Ollama uses a 120-second request timeout. Cancelling a browser request does not guarantee model generation is cancelled.


## 11. Restricted virtual-device historical ingestion

Normal `POST /api/sensors/` behavior is unchanged: the server assigns the current
time and output `timestamp`, `node_id` and `zone_id` remain read-only.

For explicitly enabled test fixtures only, the same endpoint additionally accepts
`recorded_at` (ISO 8601 datetime). It requires all three conditions:

- A valid `X-Edge-Key` for an enabled device.
- The device ID is in backend `SIMULATION_NODE_IDS`.
- `X-Simulation-Token` matches the nonempty backend `SIMULATION_INGESTION_TOKEN`.

These settings default to disabled. Development settings optionally load the
ignored local `.simulation.env`. Keep the token and device keys out of frontend
configuration. Restart Django after enabling or disabling this local file.

Example body (the date must be within the preceding 31 days, not in the future):

```json
{"temperature":24.5,"humidity":58,"soil_moisture":35,"light":800,"recorded_at":"2026-10-20T12:00:00Z"}
```

A successful write returns the ordinary `201` sensor record with `timestamp` set
to `recorded_at` and device/zone derived from authentication. Unauthorized
historical input returns `403`; malformed, null, future or older-than-31-day
values return `400`. Invalid device authentication is rejected before ingestion.
Requests without `recorded_at` still work without the simulation token and always
use server time. Sending the read-only `timestamp` does not backdate a reading.
Historical writes never reduce the device's `last_data_at`.

There is no new bulk endpoint, frontend device selector or user-controlled owner
field. The fixture script uses individual POST requests. See
[virtual fixture instructions](scripts/README.md)
for account setup, verification and disabling backfill.
