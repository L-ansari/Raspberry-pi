// Demonstration data only. currentReadings matches the documented SensorReading fields.
// Status values are mock display data; the backend has not defined plant-specific status rules yet.
export const mockData = {
  plants: [
    { id: 'tomato', name: 'Tomato' },
    { id: 'basil', name: 'Basil' },
    { id: 'lettuce', name: 'Lettuce' },
  ],
  currentReadings: {
    id: 'demo-reading-1',
    temperature: 24.6,
    humidity: 51,
    soil_moisture: 22,
    light: 620,
    timestamp: '2026-10-14T12:00:00Z',
  },
  sensorStatuses: {
    temperature: 'normal',
    humidity: 'normal',
    soil_moisture: 'low',
    light: 'normal',
  },
  history: {
    '7d': [
      ['2026-10-08', 22.1, 52, 46, 500],
      ['2026-10-09', 25.0, 47, 42, 680],
      ['2026-10-10', 24.0, 51, 37, 540],
      ['2026-10-11', 21.8, 55, 32, 730],
      ['2026-10-12', 23.0, 51, 27, 980],
      ['2026-10-13', 23.1, 47, 24, 690],
      ['2026-10-14', 24.6, 51, 22, 620],
    ],
    '30d': [
      ['2026-09-14', 23.2, 57, 54, 590],
      ['2026-09-19', 25.1, 53, 49, 770],
      ['2026-09-24', 22.6, 56, 45, 640],
      ['2026-09-29', 24.2, 49, 39, 820],
      ['2026-10-04', 23.5, 54, 33, 710],
      ['2026-10-09', 25.0, 47, 27, 680],
      ['2026-10-14', 24.6, 51, 22, 620],
    ],
  },
  // Plant-specific display fixtures until the backend provides an alerts endpoint.
  alerts: [
    {
      id: 'demo-alert-tomato-soil',
      plantId: 'tomato',
      type: 'LOW_SOIL_MOISTURE',
      severity: 'warning',
      message: 'Soil moisture is 22%. Your tomato plant may need attention.',
    },
  ],
  recommendations: [
    {
      plantId: 'tomato',
      suggestion: 'Consider watering your plant.',
      explanation: 'The example soil moisture readings have fallen from 46% to 22% over the past week. Check the soil before watering your tomato plant.',
    },
    {
      plantId: 'basil',
      suggestion: 'Check your basil’s soil moisture.',
      explanation: 'The example readings show soil moisture decreasing this week. Inspect the soil and your basil before deciding whether to water.',
    },
    {
      plantId: 'lettuce',
      suggestion: 'Review your lettuce’s growing conditions.',
      explanation: 'Use the example temperature, humidity, soil moisture and light trends to review conditions around your lettuce. Check the soil before watering.',
    },
  ],
};

for (const range of ['7d', '30d']) {
  mockData.history[range] = mockData.history[range].map(
    ([date, temperature, humidity, soil_moisture, light]) => ({
      id: `demo-${date}`,
      temperature,
      humidity,
      soil_moisture,
      light,
      timestamp: `${date}T12:00:00Z`,
    }),
  );
}

export function mockHistorySummary(range, asOf) {
  const count = range === '7d' ? 28 : 30;
  const hours = range === '7d' ? 6 : 24;
  const end = Date.parse(asOf);
  const step = hours * 3600_000;
  return {
    range, as_of: asOf, interval_hours: hours,
    points: Array.from({ length: count }, (_, i) => {
      const sample = mockData.history[range][Math.floor(i / count * 7)];
      const start = end - (count - i) * step;
      return { ...sample, timestamp: new Date(start + step / 2).toISOString(),
        window_start: new Date(start).toISOString(), window_end: new Date(start + step).toISOString(),
        sample_count: 1,
        minimum: { ...sample }, maximum: { ...sample },
      };
    }),
  };
}

export function mockPlantAnalysis(plant, range) {
  const example = mockData.recommendations.find((item) => item.plantId === plant.id);
  return {
    plant_id: plant.id, range,
    alerts: mockData.alerts.filter((item) => item.plantId === plant.id),
    recommendation: {
      suggestion: example?.suggestion || `Review conditions for your ${plant.name}.`,
      explanation: `This is a demonstration for the selected ${range === '7d' ? 'week' : 'month'}, using example readings. Check the soil before deciding whether to water.`,
    },
  };
}
