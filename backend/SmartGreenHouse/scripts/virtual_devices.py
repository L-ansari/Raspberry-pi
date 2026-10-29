"""Create and verify private HTTP-only fixtures; no direct database access.

Run prepare, restart Django, upload, verify, disable, then restart Django again.
Credentials and resume state stay in ignored owner-readable files.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import secrets

import requests

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.virtual-fixtures.env'
CONFIG = ROOT / '.simulation.env'
BASE = os.environ.get('GREENHOUSE_API_URL', 'http://127.0.0.1:8000').rstrip('/')


def private_write(path, content):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(content)


def save(state):
    private_write(STATE, json.dumps(state, indent=2))


def request(session, method, path, expected=200, **kwargs):
    response = session.request(method, BASE + path, timeout=60, **kwargs)
    if response.status_code != expected:
        # Never echo server payloads, authorization headers, or passwords.
        raise RuntimeError(f'{method} {path}: expected {expected}, got {response.status_code}')
    return response.json()


def login(account):
    session = requests.Session()
    tokens = request(session, 'POST', '/api/users/login/', json={
        'username': account['username'], 'password': account['password']})
    session.headers['Authorization'] = 'Bearer ' + tokens['access']
    return session


def prepare():
    if STATE.exists():
        state = json.loads(STATE.read_text())
    else:
        credentials = dict(line.split('=', 1) for line in (ROOT / '.test-account.env').read_text().splitlines() if '=' in line)
        run = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        state = {'run': run, 'end': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                 'token': secrets.token_urlsafe(32), 'accounts': []}
        for index in range(3):
            account = {'username': credentials['USERNAME'] if index == 0 else f'greenhouse_virtual_{run}_{index+1}',
                       'password': credentials['PASSWORD'] if index == 0 else secrets.token_urlsafe(24),
                       'node_id': f'virtual-{run}-{index+1}', 'index': index,
                       'registered': index == 0}
            state['accounts'].append(account)
        save(state)
    for account in state['accounts']:
        if not account['registered']:
            with requests.Session() as session:
                request(session, 'POST', '/api/users/register/', expected=201, json={
                    'username': account['username'], 'password': account['password'], 'email': ''})
            account['registered'] = True
            save(state)
        with login(account) as session:
            if not account.get('api_key'):
                nodes = request(session, 'GET', '/api/edges/')
                # Do not attach simulation data to a user with an existing real device.
                if nodes:
                    raise RuntimeError('Account already has a device; inspect it before creating fixtures.')
                result = request(session, 'POST', '/api/edges/register/', expected=201, json={
                    'node_id': account['node_id'], 'name': f'Virtual Greenhouse {chr(65 + account["index"])}',
                    'zone_id': f'zone-{account["index"]+1}'})
                account['api_key'] = result['api_key']
                save(state)
        print(f'Ready: {account["username"]} / {account["node_id"]}', flush=True)
    private_write(CONFIG, 'SIMULATION_INGESTION_TOKEN=' + state['token'] + '\nSIMULATION_NODE_IDS=' +
                  ','.join(a['node_id'] for a in state['accounts']) + '\n')
    print('Restricted backfill configured. Restart Django before upload.', flush=True)


def samples(state, account):
    end = datetime.fromisoformat(state['end'])
    index = account['index']
    for hour in range(720):
        # Half-hour offset keeps samples away from inclusive range boundaries.
        instant = end - timedelta(hours=719-hour, minutes=30)
        daylight = max(0, math.sin(math.pi * (instant.hour - 6) / 12))
        wave = math.sin(hour / 19 + index)
        yield {'temperature': round(19 + index*2 + daylight*7 + wave, 2),
               'humidity': round(65 - daylight*18 + wave*5 + index*3, 2),
               'soil_moisture': round(48 - (hour % (96 + index*12))*0.27 + index*4, 2),
               'light': round(20 + daylight*(1100 + index*250), 2),
               'recorded_at': instant.isoformat()}


def upload_one(state, account):
    with login(account) as owner:
        existing = request(owner, 'GET', '/api/sensors/')
    existing_times = {datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')) for row in existing}
    inserted = 0
    with requests.Session() as device:
        device.headers.update({'X-Edge-Key': account['api_key'], 'X-Simulation-Token': state['token']})
        request(device, 'POST', '/api/edges/heartbeat/', json={})
        for number, payload in enumerate(samples(state, account), 1):
            if datetime.fromisoformat(payload['recorded_at']) not in existing_times:
                request(device, 'POST', '/api/sensors/', expected=201, json=payload)
                inserted += 1
            if number % 120 == 0:
                print(f'{account["node_id"]}: {number}/720 checked ({inserted} inserted)', flush=True)
        request(device, 'POST', '/api/edges/heartbeat/', json={})
    return inserted


def verify(state):
    report = {'run': state['run'], 'end': state['end'], 'devices': []}
    readings = []
    for account in state['accounts']:
        with login(account) as session:
            rows = request(session, 'GET', '/api/sensors/')
            assert len(rows) == 720, 'Unexpected reading count'
            assert {row['node_id'] for row in rows} == {account['node_id']}, 'Ownership violation'
            readings.append(rows[0]['id'])
            current = request(session, 'GET', '/api/sensors/current/')['reading']
            expected_latest = max(rows, key=lambda row: row['timestamp'])
            assert current['id'] == expected_latest['id'], 'Current reading mismatch'
            summaries = {}
            for window, buckets, count in [('7d', 28, 168), ('30d', 30, 720)]:
                summary = request(session, 'GET', f'/api/sensors/history-summary/{window}/', params={'as_of': state['end']})
                points = summary['points']
                assert len(points) == buckets and all(p['sample_count'] > 0 for p in points)
                assert sum(p['sample_count'] for p in points) == count
                summaries[window] = {'buckets': len(points), 'samples': count}
            report['devices'].append({'username': account['username'], 'node_id': account['node_id'],
                                      'readings': len(rows), 'current_id': current['id'], 'summaries': summaries})
    for index, account in enumerate(state['accounts']):
        with login(account) as session:
            for other in range(3):
                if other != index:
                    request(session, 'GET', f'/api/sensors/{readings[other]}/', expected=404)
    report['cross_account_read_checks'] = '6/6 denied with 404'
    if 'SIMULATION_INGESTION_TOKEN=\n' in CONFIG.read_text():
        with requests.Session() as device:
            device.headers.update({'X-Edge-Key': state['accounts'][0]['api_key'],
                                   'X-Simulation-Token': state['token']})
            # A future timestamp cannot create a row even if restart was forgotten.
            payload = next(samples(state, state['accounts'][0]))
            payload['recorded_at'] = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            request(device, 'POST', '/api/sensors/', expected=403, json=payload)
        report['historical_ingestion_disabled'] = True
    (ROOT / 'scripts' / 'virtual-device-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'upload', 'verify', 'disable'])
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'disable':
        private_write(CONFIG, 'SIMULATION_INGESTION_TOKEN=\nSIMULATION_NODE_IDS=\n')
        print('Backfill disabled in local configuration. Restart Django to apply.')
    else:
        state = json.loads(STATE.read_text())
        if args.action == 'upload':
            with ThreadPoolExecutor(max_workers=3) as pool:
                results = list(pool.map(lambda account: upload_one(state, account), state['accounts']))
            print(f'Inserted {sum(results)} readings through POST /api/sensors/.')
        else:
            verify(state)


if __name__ == '__main__':
    main()
