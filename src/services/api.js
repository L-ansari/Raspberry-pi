/** @typedef {{ id: string, temperature: number, humidity: number, soil_moisture: number, light: number, timestamp: string }} SensorReading */

const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
const HISTORY_RANGES = ['1h', '24h', '7d', '30d'];

async function request(path, options) {
  const response = await fetch(`${API_BASE_URL}/api${path}`, options);
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
    const error = new Error(data?.error || fieldErrors || `Request failed (HTTP ${response.status})`);
    error.status = response.status;
    throw error;
  }
  return data;
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
    body: JSON.stringify({ hours, language }),
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
    body: JSON.stringify({ message: message.trim(), language }),
    signal,
  });
  if (data?.status !== 'success' || typeof data.reply !== 'string' || !data.reply.trim()) {
    throw new Error('The assistant returned an invalid or empty answer. Please try again.');
  }
  return { ...data, reply: data.reply.trim() };
}

// Plant-aware response shapes to agree with the backend:
// Alert: { id: string, plantId: string, type: string, severity: string, message: string }
// Recommendation: { plantId: string, suggestion: string, explanation: string }
// Endpoints are intentionally unset because the backend has not provided them yet.
export async function getPlantAlerts(_plantId) {
  throw new Error('Plant alerts API is not available yet');
}

export async function getPlantRecommendation(_plantId) {
  throw new Error('Plant recommendation API is not available yet');
}
