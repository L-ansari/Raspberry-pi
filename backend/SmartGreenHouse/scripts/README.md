# Virtual device fixtures

These fixtures simulate three independent users, each with one virtual device.
The existing account comes from `.test-account.env`; two ordinary accounts are
created through the registration API. All device registration, password login,
sensor writes and verification use HTTP APIs, never direct database inserts.

Each device receives 720 hourly samples across the latest 30-day window, with
different temperature, humidity, soil moisture and daylight patterns. These
values are synthetic and are not calibrated hardware measurements. The window
is fixed when preparing the run; rerunning upload skips its existing timestamps.
Do not run two upload processes for the same fixtures simultaneously.

From the directory containing `manage.py`:

```sh
../.venv/bin/python manage.py migrate
../.venv/bin/python scripts/virtual_devices.py prepare
# Restart Django to load the restricted configuration.
../.venv/bin/python scripts/virtual_devices.py upload
../.venv/bin/python scripts/virtual_devices.py verify
../.venv/bin/python scripts/virtual_devices.py disable
# Restart Django again to disable backfilling.
```

`prepare` enables backfill only for the three generated node IDs and an extra
random simulation token. Both that token and a valid device API key are required.
Historical input is limited to the preceding 31 days; future values are rejected.
Ordinary uploads continue using server time. Backfill cannot move `last_data_at`
backwards. The API reports input times as the normal output `timestamp` field.

Private files (ignored by Git, mode `0600`):

- `.test-account.env`: existing test login.
- `.virtual-fixtures.env`: JSON resume state, all three logins, device keys and run bounds.
- `.simulation.env`: temporary backend enablement; `disable` clears both settings.

Keep these files private; do not commit or paste them. The generated
`virtual-device-report.json` contains no passwords or keys. Verification checks
720 visible readings per account, the newest current reading, 28 six-hour buckets
for a week and 30 daily buckets for a month, and all six cross-account reads
returning 404. The counts refer to the saved run cutoff. Other cutoffs may have
different counts as the window advances.

`disable` closes historical ingestion after the required server restart; it does
not delete accounts, devices or readings. Devices are not continuous simulators,
so their heartbeat stops after upload. This script does not install or test an
Ollama model; successful sensor ingestion alone does not establish AI availability.

Run isolated tests without MongoDB or Ollama:

```sh
../.venv/bin/python manage.py test api.test_simulation api.test_dashboard llm.tests users.tests --settings=SmartGreenHouse.test_settings
```
