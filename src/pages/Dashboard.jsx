import { useEffect, useState } from 'react';
import PlantSelector from '../components/PlantSelector.jsx';
import SensorCard from '../components/SensorCard.jsx';
import HistoryChart from '../components/HistoryChart.jsx';
import AlertPanel from '../components/AlertPanel.jsx';
import RecommendationCard from '../components/RecommendationCard.jsx';
import ChatBox from '../components/ChatBox.jsx';
import { mockData } from '../data/mockData.js';
import { getSensorHistory } from '../services/api.js';

const sensors = [
  { key: 'temperature', label: 'Temperature', unit: '°C' },
  { key: 'humidity', label: 'Humidity', unit: '%' },
  { key: 'soil_moisture', label: 'Soil Moisture', unit: '%' },
  { key: 'light', label: 'Light', unit: ' lux' },
];

export default function Dashboard() {
  const [selectedPlant, setSelectedPlant] = useState(null);
  const [historyRange, setHistoryRange] = useState('7d');
  const [history, setHistory] = useState(mockData.history['7d']);
  const [historySource, setHistorySource] = useState('demo');
  const [historyLoading, setHistoryLoading] = useState(true);
  const plantAlerts = mockData.alerts.filter((alert) => alert.plantId === selectedPlant?.id);
  const plantRecommendation = mockData.recommendations.find((item) => item.plantId === selectedPlant?.id);

  useEffect(() => {
    let active = true;
    setHistoryLoading(true);
    getSensorHistory(historyRange)
      .then((readings) => {
        if (!Array.isArray(readings)) throw new Error('Invalid history response');
        if (active) {
          setHistory(readings);
          setHistorySource('backend');
        }
      })
      .catch(() => {
        if (active) {
          setHistory(mockData.history[historyRange]);
          setHistorySource('demo');
        }
      })
      .finally(() => { if (active) setHistoryLoading(false); });
    return () => { active = false; };
  }, [historyRange]);

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <div className="dashboard__brand">
          <svg className="dashboard__leaf" viewBox="0 0 48 48" aria-hidden="true">
            <path d="M41 6C22 6 8 12 8 28a12 12 0 0 0 12 12C36 40 42 26 41 6ZM7 43C17 27 25 19 36 13" />
          </svg>
          <div>
            <h1>LLM Powered Smart Greenhouse Assistant</h1>
            <p>Monitor conditions. Understand your plants.</p>
          </div>
        </div>
      </header>

      <PlantSelector
        plants={mockData.plants}
        selectedPlant={selectedPlant}
        onSelect={setSelectedPlant}
      />

      <section className="current-status" aria-labelledby="current-status-title">
        <h2 id="current-status-title">Current Status</h2>
        <div className="sensor-grid">
          {sensors.map(({ key, label, unit }) => (
            <SensorCard
              key={key}
              type={key}
              label={label}
              value={mockData.currentReadings?.[key]}
              unit={unit}
              status={mockData.sensorStatuses[key]}
            />
          ))}
        </div>
      </section>

      <section className="historical-data" aria-labelledby="historical-data-title" aria-busy={historyLoading}>
        <div className="historical-data__header">
          <div>
            <h2 id="historical-data-title">Historical Data</h2>
            <p className="historical-data__source" role="status">
              {historyLoading ? 'Loading history…' : historySource === 'demo' ? 'Demo data — backend unavailable' : 'Backend data'}
            </p>
          </div>
          <div className="historical-data__ranges" role="group" aria-label="History time range">
            <button type="button" className={historyRange === '7d' ? 'is-active' : ''} aria-pressed={historyRange === '7d'} onClick={() => setHistoryRange('7d')}>1 Week</button>
            <button type="button" className={historyRange === '30d' ? 'is-active' : ''} aria-pressed={historyRange === '30d'} onClick={() => setHistoryRange('30d')}>1 Month</button>
          </div>
        </div>
        <div className="history-grid">
          {sensors.map(({ key, label, unit }) => (
            <HistoryChart key={key} metric={key} label={label} unit={unit.trim()} readings={history} />
          ))}
        </div>
      </section>

      <AlertPanel alerts={plantAlerts} selectedPlant={selectedPlant} />
      <div className="assistant-grid">
        <RecommendationCard selectedPlant={selectedPlant} recommendation={plantRecommendation} />
        <ChatBox />
      </div>
    </main>
  );
}
