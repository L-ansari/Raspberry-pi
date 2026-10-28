/** @typedef {{ id: string, temperature: number, humidity: number, soil_moisture: number, light: number, timestamp: string }} SensorReading */

const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
const HISTORY_RANGES = ['1h', '24h', '7d', '30d'];
const SESSION_KEY = 'greenhouse-session';
let refreshPromise = null;
let sessionVersion = 0;

export function getSession() {
  try { return JSON.parse(globalThis.sessionStorage?.getItem(SESSION_KEY) || 'null'); }
  catch { return null; }
}

function saveSession(session) {
  globalThis.sessionStorage?.setItem(SESSION_KEY, JSON.stringify(session));
}

export function logout() {
  sessionVersion++;
  globalThis.sessionStorage?.removeItem(SESSION_KEY);
  if (globalThis.sessionStorage) {
    for (let i = sessionStorage.length - 1; i >= 0; i--) {
      const key = sessionStorage.key(i);
      if (key?.startsWith('greenhouse-plant-')) sessionStorage.removeItem(key);
    }
  }
  if (typeof window !== 'undefined') window.dispatchEvent(new Event('greenhouse-logout'));
}

async function refreshAccess() {
  if (refreshPromise) return refreshPromise;
  const version = sessionVersion;
  const session = getSession();
  refreshPromise = (async () => {
    if (!session?.refresh) throw new Error('Please sign in again.');
    const response = await fetch(`${API_BASE_URL}/api/users/token/refresh/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: session.refresh }),
      signal: AbortSignal.timeout(15_000),
    });
    const data = await response.json();
    if (!response.ok || typeof data.access !== 'string') throw new Error('Please sign in again.');
    if (version !== sessionVersion) throw new Error('Session changed.');
    saveSession({ ...session, access: data.access, refresh: data.refresh || session.refresh });
  })().catch((error) => { if (version === sessionVersion) logout(); throw error; })
    .finally(() => { refreshPromise = null; });
  return refreshPromise;
}

async function request(path, options = {}, retry = true) {
  const version = sessionVersion;
  const access = getSession()?.access;
  const response = await fetch(`${API_BASE_URL}/api${path}`, {
    ...options, signal: options.signal || AbortSignal.timeout(15_000),
    headers: { ...options.headers, ...(access ? { Authorization: `Bearer ${access}` } : {}) },
  });
  if (version !== sessionVersion) throw new Error('Session changed.');
  if (response.status === 401 && retry && getSession()?.refresh) {
    await refreshAccess();
    return request(path, options, false);
  }
  if (response.status === 401 || response.status === 403) logout();
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`Backend returned an invalid response (HTTP ${response.status})`);
  }

  // History delete can return an error body with HTTP 200; LLM validation uses "errors".
  if (!response.ok || (data && typeof data === 'object' && ('error' in data || 'errors' in data))) {
    const fieldErrors = data?.errors && Object.entries(data.errors)
      .map(([field, messages]) => `${field}: ${[].concat(messages).join(', ')}`)
      .join('; ');
    const error = new Error(data?.error || data?.detail || fieldErrors || `Request failed (HTTP ${response.status})`);
    error.status = response.status;
    throw error;
  }
  return data;
}

export async function login(username, password) {
  const response = await fetch(`${API_BASE_URL}/api/users/login/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: username.trim(), password }),
    signal: AbortSignal.timeout(15_000),
  });
  const data = await response.json();
  if (!response.ok || !data.access || !data.refresh) throw new Error(data.detail || 'Unable to sign in.');
  sessionVersion++;
  saveSession(data);
  try {
    const user = await getCurrentUser();
    saveSession({ ...getSession(), user });
    return user;
  } catch (error) { logout(); throw error; }
}

export function getCurrentUser() { return request('/users/me/'); }
export function searchPlants(query, { signal } = {}) {
  return request(`/plants/?search=${encodeURIComponent(query)}`, { signal });
}
export function getCurrentReading({ signal } = {}) {
  return request('/sensors/current/', { signal, cache: 'no-store' });
}
export function getHistorySummary(range, asOf, { signal } = {}) {
  return request(`/sensors/history-summary/${checkRange(range)}/?as_of=${encodeURIComponent(asOf)}`, { signal });
}
export function getSensorStatuses(plantId, readingId, { signal } = {}) {
  return request('/llm/status/', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plant_id: plantId, reading_id: readingId }), signal });
}
export function generatePlantAnalysis(plantId, range, readingId, asOf, requestId, { signal } = {}) {
  return request('/plant-analysis/', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plant_id: plantId, range, reading_id: readingId, as_of: asOf, request_id: requestId }), signal });
}

function checkRange(range) {
  if (!HISTORY_RANGES.includes(range)) {
    throw new Error(`Invalid range: ${range}`);
  }
  return range;
}

export function getHealthCheck() {
  return request('/health_check/');
}

/** @returns {Promise<SensorReading[]>} */
export function getSensorReadings() {
  return request('/sensors/');
}

/** @param {{ temperature: number, humidity: number, soil_moisture: number, light: number }} reading */
export function createSensorReading(reading) {
  const { temperature, humidity, soil_moisture, light } = reading;
  return request('/sensors/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ temperature, humidity, soil_moisture, light }),
  });
}

export function getSensorReading(id) {
  return request(`/sensors/${encodeURIComponent(id)}/`);
}

/** @param {'1h' | '24h' | '7d' | '30d'} range */
export function getSensorHistory(range) {
  return request(`/sensors/history/${checkRange(range)}/`);
}

export function deleteSensorHistory(range) {
  return request(`/sensors/history/del/${checkRange(range)}/`, { method: 'DELETE' });
}

export function deleteSensorReading(id) {
  return request(`/sensors/del/${encodeURIComponent(id)}/`, { method: 'DELETE' });
}

/** Generate a recommendation from the latest reading and up to 50 readings in the selected window. */
export function generateRecommendation({ hours = 24, language = 'en' } = {}) {
  return request('/llm/recommend/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hours, language: 'en' }),
  });
}

/** Ask about the greenhouse using the latest reading and up to 50 readings from the last 24 hours. */
export async function sendGreenhouseMessage(message, language = 'en', { signal } = {}) {
  if (typeof message !== 'string' || !message.trim() || message.trim().length > 2000) {
    throw new Error('Enter a question between 1 and 2,000 characters.');
  }
  const data = await request('/llm/chat/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: message.trim(), language: 'en' }),
    signal,
  });
  if (data?.status !== 'success' || typeof data.reply !== 'string' || !data.reply.trim()) {
    throw new Error('The assistant returned an invalid or empty answer. Please try again.');
  }
  return { ...data, reply: data.reply.trim() };
}
