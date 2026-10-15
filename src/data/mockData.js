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
  recommendation: null,
  messages: [],
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
