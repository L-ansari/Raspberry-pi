import assert from 'node:assert/strict';
import { test, beforeEach } from 'node:test';
import { getCurrentUser, getSession, login, logout } from '../src/services/api.js';

const values = new Map();
globalThis.sessionStorage = {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value),
  removeItem: (key) => values.delete(key),
  key: (index) => [...values.keys()][index],
  get length() { return values.size; },
};
beforeEach(() => { logout(); values.clear(); });

test('login obtains a user session and never stores the password', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url.endsWith('/login/')) {
      assert.deepEqual(JSON.parse(options.body), { username: 'alice', password: 'test-password' });
      return Response.json({ access: 'access-token', refresh: 'refresh-token' });
    }
    assert.equal(options.headers.Authorization, 'Bearer access-token');
    return Response.json({ id: 'user-1', username: 'alice' });
  });
  assert.equal((await login(' alice ', 'test-password')).id, 'user-1');
  assert.equal(getSession().user.username, 'alice');
  assert.ok(!JSON.stringify([...values.values()]).includes('test-password'));
});

test('concurrent expired requests share one refresh and retry with the new access token', async (t) => {
  sessionStorage.setItem('greenhouse-session', JSON.stringify({ access: 'expired', refresh: 'refresh-token' }));
  let refreshes = 0;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url.endsWith('/token/refresh/')) { refreshes++; return Response.json({ access: 'fresh' }); }
    return options.headers.Authorization === 'Bearer fresh'
      ? Response.json({ id: 'user-1' })
      : Response.json({ detail: 'Token expired' }, { status: 401 });
  });
  const users = await Promise.all([getCurrentUser(), getCurrentUser()]);
  assert.equal(refreshes, 1);
  assert.ok(users.every((user) => user.id === 'user-1'));
});

test('logout during refresh cannot resurrect a session', async (t) => {
  sessionStorage.setItem('greenhouse-session', JSON.stringify({ access: 'expired', refresh: 'refresh-token' }));
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  let refreshStarted;
  const started = new Promise((resolve) => { refreshStarted = resolve; });
  t.mock.method(globalThis, 'fetch', async (url) => {
    if (url.endsWith('/token/refresh/')) { refreshStarted(); await gate; return Response.json({ access: 'fresh' }); }
    return Response.json({ detail: 'Token expired' }, { status: 401 });
  });
  const request = getCurrentUser();
  await started;
  logout(); release();
  await assert.rejects(request, /Session changed/);
  assert.equal(getSession(), null);
});

test('refresh rejection clears credentials and saved plant selection', async (t) => {
  sessionStorage.setItem('greenhouse-session', JSON.stringify({ access: 'expired', refresh: 'bad' }));
  sessionStorage.setItem('greenhouse-plant-user-1', JSON.stringify({ id: 'tomato' }));
  t.mock.method(globalThis, 'fetch', async () => Response.json({ detail: 'Expired' }, { status: 401 }));
  await assert.rejects(getCurrentUser(), /sign in again/);
  assert.equal(getSession(), null);
  assert.equal(sessionStorage.getItem('greenhouse-plant-user-1'), null);
});

test('an old authenticated response is discarded after logout', async (t) => {
  sessionStorage.setItem('greenhouse-session', JSON.stringify({ access: 'old', refresh: 'old-refresh' }));
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  t.mock.method(globalThis, 'fetch', async () => { await gate; return Response.json({ id: 'old-user' }); });
  const pending = getCurrentUser();
  logout(); release();
  await assert.rejects(pending, /Session changed/);
});
