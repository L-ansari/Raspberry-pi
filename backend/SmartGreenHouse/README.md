# Smart Greenhouse

A Django REST Framework backend for collecting greenhouse sensor readings, querying historical data, managing users, and generating AI-assisted recommendations and chat responses using Ollama.

## Features

- Store and retrieve sensor readings for temperature, humidity, soil moisture, and light.
- Query readings for supported time ranges.
- Delete readings by ID or time range.
- Register users and obtain JWT tokens.
- Generate greenhouse recommendations and chat responses using sensor data as context.
- Register and monitor multiple edge nodes (e.g. Raspberry Pi devices) per greenhouse zone.
- Associate sensor readings with the node and zone that produced them.
- Track node liveness via heartbeats and detect offline devices.
- Isolate data per user: a user can read or delete only the data produced by the
  edge nodes they own. Superusers see everything, including legacy unowned readings.

## Technology

- Python and Django
- Django REST Framework
- MongoDB through `django-mongodb-backend`
- JSON Web Tokens through Simple JWT
- Ollama for LLM-backed recommendations and chat

## Project Layout

```text
SmartGreenHouse/
├── SmartGreenHouse/   # Django project configuration and root URLs
├── api/               # Sensor readings, edge-node registry, serializers, views, and routes
├── llm/               # Ollama integration and LLM endpoints
├── users/             # Registration, JWT, and profile endpoints
├── frontend-api.md    # Frontend API reference
└── manage.py
```

## Requirements

- Python
- A MongoDB database, such as MongoDB Atlas
- Ollama and a locally available model to use the LLM endpoints

Install the runtime packages into a project-local virtual environment:

```bash
python -m venv ../.venv
../.venv/bin/python -m pip install -r requirements.txt
```

## Configuration

The Django settings load environment variables from `atlas-credentials.env` in the project root. Configure the following values there or provide them through the process environment:

```dotenv
MONGODB_URI=your-mongodb-connection-string
MONGODB_DB=greenhouse
```

`MONGODB_DB` is optional and defaults to `greenhouse`. Do not commit database credentials or other secrets.

### Edge-node configuration

Edge-node management reads these optional environment variables (with defaults shown):

```dotenv
EDGE_PROVISIONING_TOKEN=         # shared secret that authorizes device registration
EDGE_HEARTBEAT_TIMEOUT=60        # seconds without a heartbeat before a node is offline
EDGE_ALLOWED_ZONES=zone-1,zone-2,zone-3   # comma-separated zones a node may be assigned
```

- `EDGE_PROVISIONING_TOKEN` is empty by default, which disables token-based registration
  (registration still works for authenticated application users). Set a secret value to allow
  devices to register with that token.
- `EDGE_HEARTBEAT_TIMEOUT` is the offline-detection threshold used by `check_edge_health`.
- `EDGE_ALLOWED_ZONES` is the list of valid `zone_id` values accepted at registration.

### Ollama configuration

Set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in `atlas-credentials.env` or the process environment (see `.env.example`). Settings now read both values. A missing model or invalid/unavailable model response returns a service error. The Ollama server must be reachable and the selected model must already be available. Set `CORS_ALLOWED_ORIGINS` for the frontend origin; localhost:5173 and 127.0.0.1:5173 are allowed by default.

## Run the Development Server

From the project root, with the Python dependencies installed and MongoDB configured, run:

```bash
python manage.py runserver
```

By default, the development server is available at `http://127.0.0.1:8000`.

## API Overview

The API is prefixed with `/api/`.

### Sensor readings

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health_check/` | Check backend health |
| `GET` | `/api/sensors/` | List sensor readings |
| `POST` | `/api/sensors/` | Create a sensor reading |
| `GET` | `/api/sensors/:id/` | Retrieve one reading |
| `GET` | `/api/sensors/history/:range/` | Retrieve readings from a supported time range |
| `DELETE` | `/api/sensors/history/del/:range/` | Delete readings from a supported time range |
| `DELETE` | `/api/sensors/del/:id/` | Delete one reading |

Supported history ranges are `1h`, `24h`, `7d`, and `30d`.

### LLM

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/llm/recommend/` | Generate a recommendation using sensor data |
| `POST` | `/api/llm/chat/` | Chat with the greenhouse assistant using recent sensor data |

All application LLM endpoints are English-only. Existing generic endpoints accept only `language: en`.

### Users

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/users/register/` | Register a user |
| `POST` | `/api/users/login/` | Obtain a JWT access and refresh token pair |
| `POST` | `/api/users/token/refresh/` | Refresh an access token |
| `GET` | `/api/users/me/` | Access the current-user profile endpoint |

The project configures Simple JWT authentication for Django REST Framework. See the view and permission configuration before relying on authentication enforcement for an endpoint.

For request and response examples, validation details, and current API caveats, see [frontend-api.md](./frontend-api.md).

### Edge nodes

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/edges/register/` | Register a new edge node (returns a one-time API key) |
| `POST` | `/api/edges/heartbeat/` | Report that a node is alive (device API key) |
| `GET` | `/api/edges/` | List registered nodes and status (application-user JWT) |

Sensor readings submitted with a valid device API key are associated with the source node and
zone (`node_id`/`zone_id` in the reading). Legacy unauthenticated sensor requests keep working
and are stored without a node/zone association.

## Edge node health check

Nodes that stop sending heartbeats are marked `offline` by a management command:

```bash
python manage.py check_edge_health
```

It compares each online node's `last_heartbeat` against `EDGE_HEARTBEAT_TIMEOUT` (default 60
seconds) and marks stale nodes offline. Disabled nodes are never changed.

The command does **not** schedule itself. Run it periodically with your platform's scheduler, for
example a cron/systemd timer:

```cron
* * * * * cd /path/to/SmartGreenHouse && python manage.py check_edge_health
```

## Device provisioning and authentication

Edge devices authenticate with a per-node API key in the `X-Edge-Key` header. To provision a
device, an administrator either registers it while authenticated (JWT) or shares the
`EDGE_PROVISIONING_TOKEN` with the device so it can self-register:

```bash
curl -X POST http://127.0.0.1:8000/api/edges/register/ \
  -H "Content-Type: application/json" \
  -d '{"node_id": "pi-zone-1", "name": "Raspberry Pi Zone 1", "zone_id": "zone-1", "provisioning_token": "YOUR_TOKEN"}'
```

The response contains the device's `api_key` exactly once. Store it on the device and send it in
the `X-Edge-Key` header for heartbeats and sensor uploads. To revoke a device's access, set its
`status` to `disabled` (or delete the node); its API key will then be rejected.

## Data ownership and permissions

Each edge node has an `owner`. When a node is registered by an authenticated user (JWT), that
user becomes its owner; nodes registered with the shared provisioning token have no owner.

Authorization is enforced server-side:

- A user can list only the nodes they own, and read/delete only the sensor readings produced by
  those nodes. Cross-user access returns `404` (so the existence of another user's data is not
  leaked).
- Reading endpoints (`GET /api/sensors/`, single reading, history) and both delete endpoints now
  require an authenticated user (JWT). Sensor **uploads** remain open to preserve legacy and
  device-key clients.
- Readings with no `node_id` (legacy/anonymous uploads) and nodes with no owner are visible only
  to superusers.
- Superusers bypass all scoping and can see everything.
- The LLM endpoints (`/api/llm/recommend/`, `/api/llm/chat/`) also require a JWT and use only the
  calling user's own readings as context.
- Deleting a user does not delete their nodes (the `owner` is set to `NULL`); those nodes then
  become superuser-only.

## Notes

- Sensor reading `id` values are returned as strings; timestamps are generated by the backend.
- The backend uses UTC for Django time handling.
- The LLM service may return `503 Service Unavailable` if it cannot communicate with Ollama or receives an invalid response.
- Invalid range deletion still returns an error body with HTTP 200; the frontend recognizes error bodies. Single-record deletion validates IDs and ownership.
- The project settings currently use development-oriented values, including `DEBUG = True` and a development-only Django secret-key fallback (set DJANGO_SECRET_KEY for deployment). Do not deploy these settings to production; use secure environment-based configuration and follow Django's deployment checklist.
- Sensor readings may now carry `node_id` and `zone_id`. Legacy readings and unauthenticated
  submissions have `null` for both fields.
- Edge-node API keys are stored only as a SHA-256 hash; the plaintext key is returned once at
  registration and is never logged or returned again.
- The new `EdgeNode` model and the additive `SensorReading.node_id`/`zone_id` fields require a
  migration (`python manage.py makemigrations api` then `migrate`) in an environment with the
  runtime dependencies installed. The change is additive and does not alter existing documents.


## Dashboard integration (2026-10-28)

The dashboard assumes one device, without a device selector. Shared `Plant` records and private `PlantAnalysis` snapshots are added in migration `0003_plant_plantanalysis`.

```sh
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py seed_plants
```

`seed_plants` inserts or updates 20 English plants without duplicates. New endpoints cover plant search, current readings, transient LLM status, fixed-window history summaries and saved plant analyses. See [frontend-api.md](frontend-api.md), sections 9–10, for the exact contracts. Instantaneous statuses are not persisted. Successful historical results and their actual input snapshots are persisted per user.

Run isolated HTTP contract tests without accessing MongoDB or Ollama:

```sh
../.venv/bin/python manage.py test api.test_dashboard --settings=SmartGreenHouse.test_settings
```

These tests use SQLite and mocked model output. They do not replace MongoDB migration checks or real-model evaluation. Existing MongoDB-backed tests can be run separately in a dedicated test database.


## Virtual-device validation

Restricted historical ingestion and an HTTP-only fixture script are available for
three isolated users/devices. See [scripts/README.md](scripts/README.md). Apply
migration `0004_sensorreading_timestamp_default` before use; existing timestamps
are preserved. Historical ingestion is disabled unless explicitly configured.
