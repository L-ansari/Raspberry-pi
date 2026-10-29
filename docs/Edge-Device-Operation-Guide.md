# LLM Powered Smart Greenhouse Assistant — Edge Device Operation Guide

Updated: 28 October 2026. This guide describes the current backend implementation.

## 1. Workflow

1. Log in as the greenhouse user and obtain a user access token.
2. Register a device using that token. The backend binds the device to the user.
3. Save the returned device API key and configure it on the edge device.
4. Read the sensors and upload measurements using the device key.
5. Send heartbeats separately to update device connectivity status.
6. Log in to the frontend as the same user and select **Refresh data**.

The dashboard assumes one device per user and has no device selector. Register a
real device under the intended user; the existing virtual test devices belong to
their respective test users.

## 2. Prerequisites and server address

- The backend and its database connection must be available.
- You need an existing user account and its password.
- For Postman testing on the backend computer, use `http://127.0.0.1:8000`.
- A physical device must use an address it can reach. `127.0.0.1` on a Raspberry Pi
  points to that Pi, not to the backend computer.
- For a LAN test, the backend must listen on an appropriate network interface and
  allow the server hostname/IP. Network access must also be permitted. Changing
  only the URL does not make a loopback-only server reachable.
- For a deployed system, use the backend's HTTPS address.

All paths below are relative to the backend address, not the frontend at port 5173.

## 3. Configure Postman

Create a local environment with these variables:

| Variable | Value |
| --- | --- |
| `base_url` | `http://127.0.0.1:8000` for testing on this computer |
| `access_token` | The user's access token returned after login |
| `device_api_key` | The API key returned after device registration |

Treat the last two values as secrets. Keep them local and do not include them in
shared collections, exported environments, screenshots or source control.

For each JSON request, select **Body → raw → JSON**. Ensure the header
`Content-Type: application/json` is present.

## 4. Log in as a user

In Postman, select **Authorization → No Auth** for this request.

```http
POST {{base_url}}/api/users/login/
Content-Type: application/json

{
  "username": "<your username>",
  "password": "<your password>"
}
```

Expected status: **200 OK**.

```json
{
  "refresh": "<refresh token>",
  "access": "<access token>"
}
```

Copy `access` into the local `access_token` variable. Use the access token, not
the refresh token, when registering devices or reading user data. If it expires,
log in again or use `POST /api/users/token/refresh/` with a `refresh` field.

## 5. Register a device once

Select **Authorization → Bearer Token** and enter `{{access_token}}`.

```http
POST {{base_url}}/api/edges/register/
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "node_id": "greenhouse-edge-001",
  "name": "My Greenhouse",
  "zone_id": "zone-1"
}
```

| Field | Meaning |
| --- | --- |
| `node_id` | A unique, stable device identifier chosen during deployment |
| `name` | A readable device name |
| `zone_id` | An allowed greenhouse zone; use `zone-1` for this single-device setup |

The default allowed zones are `zone-1`, `zone-2` and `zone-3`; server configuration
can change the list. Reusing an existing `node_id` returns **409 Conflict**.

Expected status: **201 Created**. The response includes `message`, `node` and
`api_key`. Copy `api_key` into `device_api_key` and securely provision it on the
physical device. The device record should show the intended username as `owner`.

The plaintext key is returned only once. The backend stores its hash. Restarting
a device does not require registering it again. The current API does not provide
a key-retrieval or key-rotation endpoint; if the key is lost, administrator support
is required.

Use the user-token registration flow above for user-owned devices. The backend
also supports a provisioning-token flow, but that currently creates a device
without an owner. It does not automatically bind the device to a dashboard user.
Do not supply a provisioning token for the user-owned flow.

## 6. Upload a sensor reading

Select **Authorization → No Auth** for device uploads. Add the device key in
**Headers**. Do not inherit or send a user Bearer token with this request: JWT
authentication runs before device authentication in the current sensor endpoint.

```http
POST {{base_url}}/api/sensors/
Content-Type: application/json
X-Edge-Key: {{device_api_key}}

{
  "temperature": 25.3,
  "humidity": 62,
  "soil_moisture": 38,
  "light": 850
}
```

| Field | Expected measurement |
| --- | --- |
| `temperature` | Temperature in degrees Celsius |
| `humidity` | Relative humidity in percent |
| `soil_moisture` | Soil moisture in percent, using the device's calibration |
| `light` | Illuminance in lux |

Send numeric values without unit strings. Convert raw sensor output to the agreed
units before uploading; an ADC value is not automatically a moisture percentage
or lux measurement. Physical sensor calibration remains device-side work.

Expected status: **201 Created**. The response contains the saved values plus
`id`, `timestamp`, `node_id` and `zone_id`.

Do not put `node_id`, `zone_id` or `timestamp` in the body. They are read-only:
the backend derives the device/zone from the key and assigns the current server
time. The timestamp represents ingestion time, not a device-supplied measurement
time. Ordinary uploads do not support historical timestamps.

## 7. Send heartbeats

Select **Authorization → No Auth** and use the same device key.

```http
POST {{base_url}}/api/edges/heartbeat/
Content-Type: application/json
X-Edge-Key: {{device_api_key}}

{}
```

Expected status: **200 OK**, with `status`, `node_id` and `last_heartbeat`.
A newly registered device starts offline; a successful heartbeat marks it online.
Sensor uploads update `last_data_at` separately and do not replace heartbeats.

A suggested starting schedule is a heartbeat every 30 seconds and a reading every
60 seconds. These are device-program choices, not automatic backend schedules.
The default heartbeat timeout is 60 seconds. Marking stale devices offline
requires periodically running the existing management command through an external
scheduler:

```sh
../.venv/bin/python manage.py check_edge_health
```

Run this command from the backend directory containing `manage.py`. The endpoint
alone does not schedule this check.

## 8. Verify ownership and frontend data

Use **Bearer Token → `{{access_token}}`** for these user requests. Do not use a
device API key in place of a user token.

| Request | Expected result |
| --- | --- |
| `GET {{base_url}}/api/edges/` | Devices owned by the logged-in ordinary user |
| `GET {{base_url}}/api/sensors/current/` | The user's latest accessible reading, or `reading: null` |
| `GET {{base_url}}/api/sensors/history-summary/7d/` | 28 six-hour summary buckets |
| `GET {{base_url}}/api/sensors/history-summary/30d/` | 30 daily summary buckets |

Log in to the frontend as the same user, then click **Refresh data**. Confirm the
four current values match the submitted reading, provided no newer reading has
arrived. Historical curves display bucket averages, so they need not show the
new raw value exactly. An ordinary user must not be able to read another user's
device readings; superusers have broader visibility.

## 9. Troubleshooting

| Symptom | Check or action |
| --- | --- |
| Connection refused or timed out | Confirm the backend is running and the device can reach its address and port. |
| Login or user request returns 401 | Check the user credentials or obtain a new access token. |
| Device request returns 401 | Check `X-Edge-Key`; an invalid key or disabled device is rejected. |
| Registration returns 400 | Check required fields and the configured allowed zones. |
| Registration returns 409 | The device ID is already registered. Use its saved key rather than registering it again. |
| Sensor upload returns 400 | Check valid JSON, all four numeric fields and their types. |
| Upload succeeds but device/zone is null | Check that a valid device key was sent and no user JWT took precedence. |
| Data is absent from the frontend | Check the device owner, the frontend's logged-in user and Refresh data. |
| Device remains online after disconnection | Confirm the health-check command is scheduled. |
| Values load but AI results fail | Check Ollama and model configuration; sensor ingestion does not establish LLM availability. |

## 10. Current limits and deployment work

- The sensor POST endpoint still supports legacy uploads without a device key.
  Such records have no device association and are not visible to ordinary users
  through the owner-scoped queries. Require device-key authentication before a
  real deployment; the current endpoint does not enforce it for every upload.
- Keep each device's key on that device, separate from frontend source code and
  browser configuration. Use HTTPS for deployed traffic.
- The physical-device program is not included in this guide. It still needs
  sensor acquisition, calibration, scheduling, request timeouts and retry handling.
- Uploads are not idempotent. Retrying after an uncertain response may create a
  duplicate. Reliable offline replay needs an agreed measurement timestamp and
  deduplication contract; queued samples currently receive their upload time.
- Restricted `recorded_at` backfilling is for allowlisted test fixtures only and
  is currently disabled locally. Do not use its simulation token on real devices.

For the test-fixture workflow, see [Virtual device fixtures](../backend/SmartGreenHouse/scripts/README.md).
For the complete API contract, see [Frontend API reference](../backend/SmartGreenHouse/frontend-api.md).
