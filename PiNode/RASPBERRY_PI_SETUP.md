# Raspberry Pi Sensor Uploader

`read_sensors.py` prints the readings and uploads complete samples to the Greenhouse backend. It also sends a heartbeat every 30 seconds so the backend can report the edge node as online.

## 1. Start the backend on the laptop

From `backend/SmartGreenHouse`, start Django so it accepts connections from the local network:

```bash
python manage.py runserver 0.0.0.0:8000
```

Find the laptop's IPv4 address (`ipconfig` on Windows, `ip addr` on Linux). Use that address in the Pi configuration, not `localhost` or `127.0.0.1`. Allow the laptop firewall to accept private-network connections on port `8000`. Keep the development server off the public internet.

## 2. Register the Pi once

Register the node while authenticated as the application user who should own its readings. Log in using `POST /api/users/login/` and use the returned `access` token below:

```bash
curl -X POST http://LAPTOP_IP:8000/api/edges/register/ \
  -H 'Authorization: Bearer ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"node_id":"pi-zone-1","name":"Raspberry Pi Zone 1","zone_id":"zone-1"}'
```

Replace `LAPTOP_IP` and `ACCESS_TOKEN`. Use a `zone_id` allowed by the backend's `EDGE_ALLOWED_ZONES` setting. Save the returned `api_key`; the backend only returns its plaintext value once. Registration using the shared provisioning token is also supported, but creates an unowned node.

## 3. Install and configure the Pi

From this project directory on the Pi:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-pi.txt
cp .env.example .env
```

Edit `.env`: set `GREENHOUSE_API_URL` to the laptop's address, for example `http://192.168.1.25:8000`, and set `GREENHOUSE_EDGE_KEY` to the key returned during registration. `.env` is ignored by Git; do not commit or share it.

### Calibrate soil moisture

The probe reports a raw capacitive count. To upload a percentage, record its raw count in dry soil, then record it again in well-watered soil. The script prints raw counts while uncalibrated. Put those two measured values in `.env`:

```dotenv
SOIL_MOISTURE_DRY_RAW=<dry-soil-count>
SOIL_MOISTURE_WET_RAW=<well-watered-soil-count>
```

The script maps the dry reference to 0% and the well-watered reference to 100%, clamps readings to that range, and uploads the calculated percentage. This is a relative calibration for your probe and soil, not a universal soil-water percentage. Until both values are set, readings are printed but not uploaded.

## 4. Run and check

With the backend running and both devices on the same reachable network:

```bash
source .venv/bin/activate
python read_sensors.py
```

The console reports upload success or the request error. Readings are uploaded only when all four required values are available: air temperature, air humidity, soil moisture, and light. Failed uploads are reported but are not queued for later retry. The backend timestamps readings when it receives them.