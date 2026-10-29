import { useEffect, useState } from 'react';
import PlantSelector from '../components/PlantSelector.jsx';
import SensorCard from '../components/SensorCard.jsx';
import HistoryChart from '../components/HistoryChart.jsx';
import AlertPanel from '../components/AlertPanel.jsx';
import RecommendationCard from '../components/RecommendationCard.jsx';
import ChatBox from '../components/ChatBox.jsx';
import { mockData, mockHistorySummary, mockPlantAnalysis } from '../data/mockData.js';
import { getCurrentReading, getHistorySummary, getSensorStatuses, generatePlantAnalysis } from '../services/api.js';

const sensors = [
  { key: 'temperature', label: 'Temperature', unit: '°C' },
  { key: 'humidity', label: 'Humidity', unit: '%' },
  { key: 'soil_moisture', label: 'Soil Moisture', unit: '%' },
  { key: 'light', label: 'Light', unit: ' lux' },
];

export default function Dashboard({ user, onLogout }) {
  const plantKey = `greenhouse-plant-${user.id}`;
  const [selectedPlant, setSelectedPlant] = useState(() => {
    try {
      const plant = JSON.parse(sessionStorage.getItem(plantKey) || 'null');
      return plant && typeof plant.id === 'string' && typeof plant.name === 'string' ? plant : null;
    } catch { return null; }
  });
  const [refresh, setRefresh] = useState(0);
  const [current, setCurrent] = useState({ loading: true, reading: null, as_of: null, source: null });
  const [historyRange, setHistoryRange] = useState('7d');
  const [history, setHistory] = useState({ key: '', points: [], source: null });
  const [statuses, setStatuses] = useState({ key: '', values: {}, source: null });
  const [analysis, setAnalysis] = useState({ key: '', data: null, source: null });
  const historyKey = `${current.as_of}|${historyRange}`;
  const statusKey = `${current.as_of}|${current.reading?.id}|${selectedPlant?.id}`;
  const analysisKey = `${statusKey}|${historyRange}`;
  const historyLoading = current.loading || history.key !== historyKey;
  const analysisLoading = Boolean(selectedPlant && (current.loading || (current.reading && analysis.key !== analysisKey)));
  const analysisData = analysis.key === analysisKey ? analysis.data : null;
  const period = historyRange === '7d' ? 'Last 7 days' : 'Last 30 days';
  const analysisNote = !selectedPlant ? '' : analysisLoading ? period
    : !current.reading ? `${period} · No sensor readings available for analysis.`
    : analysis.source === 'demo' ? `${period} · Demo analysis — live analysis unavailable; not saved.`
      : analysisData?.status === 'no_data' ? `${period} · Insufficient readings; no analysis saved.`
        : `${period} · Saved analysis${analysisData?.generated_at ? ` · ${new Date(analysisData.generated_at).toLocaleString('en-GB', { timeZone: 'UTC' })} UTC` : ''}`;

  function selectPlant(plant) {
    setSelectedPlant(plant);
    if (plant) sessionStorage.setItem(plantKey, JSON.stringify(plant));
    else sessionStorage.removeItem(plantKey);
  }

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15_000);
    setCurrent({ loading: true, reading: null, as_of: null, source: null });
    getCurrentReading({ signal: controller.signal }).then((data) => {
      if (!Number.isFinite(Date.parse(data.as_of)) || (data.reading !== null && (
        typeof data.reading?.id !== 'string' || !Number.isFinite(Date.parse(data.reading.timestamp))
        || sensors.some(({ key }) => !Number.isFinite(data.reading[key]))
      ))) throw new Error('Invalid current response');
      if (active) setCurrent({ ...data, loading: false, source: 'backend' });
    }).catch(() => {
      if (active) setCurrent({ loading: false, reading: mockData.currentReadings, as_of: new Date().toISOString(), source: 'demo' });
    }).finally(() => clearTimeout(timer));
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [refresh]);

  useEffect(() => {
    if (!current.as_of) return;
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15_000);
    const fallback = () => setHistory({ key: historyKey, ...mockHistorySummary(historyRange, current.as_of), source: 'demo' });
    if (current.source === 'demo') { fallback(); clearTimeout(timer); return; }
    getHistorySummary(historyRange, current.as_of, { signal: controller.signal }).then((data) => {
      const expected = historyRange === '7d' ? 28 : 30;
      if (data.range !== historyRange || Date.parse(data.as_of) !== Date.parse(current.as_of)
        || !Array.isArray(data.points) || data.points.length !== expected
        || data.points.some((point) => !Number.isFinite(Date.parse(point.timestamp))
          || sensors.some(({ key }) => point[key] !== null && !Number.isFinite(point[key])))) throw new Error('Invalid history response');
      if (active) setHistory({ ...data, key: historyKey, source: 'backend' });
    }).catch(() => { if (active) fallback(); }).finally(() => clearTimeout(timer));
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [current.as_of, current.source, historyRange, historyKey]);

  useEffect(() => {
    if (!selectedPlant || !current.reading || current.loading) return;
    if (current.source === 'demo') {
      setStatuses({ key: statusKey, values: mockData.sensorStatuses, source: 'demo' });
      return;
    }
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 130_000);
    getSensorStatuses(selectedPlant.id, current.reading.id, { signal: controller.signal }).then((data) => {
      if (data.plant_id !== selectedPlant.id || data.reading_id !== current.reading.id
        || sensors.some(({ key }) => !['normal', 'low', 'high', 'unknown'].includes(data.sensor_statuses?.[key]))) throw new Error('Invalid status response');
      if (active) setStatuses({ key: statusKey, values: data.sensor_statuses, source: 'backend' });
    }).catch((error) => {
      if (!active) return;
      if (error.status === 404 && error.message === 'Plant not found.') selectPlant(null);
      setStatuses({ key: statusKey, values: {}, source: 'unavailable' });
    }).finally(() => clearTimeout(timer));
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [selectedPlant?.id, current.as_of, current.reading?.id, current.source, current.loading, statusKey]);

  useEffect(() => {
    if (!selectedPlant || !current.reading || current.loading) return;
    if (current.source === 'demo') {
      setAnalysis({ key: analysisKey, data: mockPlantAnalysis(selectedPlant, historyRange), source: 'demo' });
      return;
    }
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 130_000);
    const requestId = crypto.randomUUID();
    generatePlantAnalysis(selectedPlant.id, historyRange, current.reading.id, current.as_of, requestId, { signal: controller.signal }).then((data) => {
      if (data.plant_id !== selectedPlant.id || data.range !== historyRange || !data.snapshot
        || data.snapshot.latest_reading?.id !== current.reading.id
        || Date.parse(data.snapshot.as_of) !== Date.parse(current.as_of)
        || (data.status !== 'no_data' && (!Array.isArray(data.alerts)
          || !data.alerts.every((item) => typeof item.message === 'string')
          || typeof data.recommendation?.suggestion !== 'string' || typeof data.recommendation?.explanation !== 'string'))) throw new Error('Invalid analysis response');
      if (active) setAnalysis({ key: analysisKey, data, source: 'backend' });
    }).catch((error) => {
      if (!active) return;
      if (error.status === 404 && error.message === 'Plant not found.') selectPlant(null);
      setAnalysis({ key: analysisKey, data: mockPlantAnalysis(selectedPlant, historyRange), source: 'demo' });
    }).finally(() => clearTimeout(timer));
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [selectedPlant?.id, current.as_of, current.reading?.id, current.source, current.loading, historyRange, analysisKey]);

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
        <div className="dashboard__account"><span>{user.username}</span><button type="button" onClick={() => setRefresh((n) => n + 1)} disabled={current.loading}>Refresh data</button><button type="button" onClick={onLogout}>Sign out</button></div>
      </header>

      <PlantSelector
        plants={mockData.plants}
        selectedPlant={selectedPlant}
        onSelect={selectPlant}
      />

      <section className="current-status" aria-labelledby="current-status-title" aria-busy={current.loading}>
        <h2 id="current-status-title">Current Status</h2>
        <p className="current-status__source" role="status">
          {current.loading ? 'Loading latest readings…' : current.source === 'demo' ? 'Demo readings — live data unavailable.' : !current.reading ? 'No sensor readings yet.' : 'Latest backend reading.'}
          {current.reading && <> · Measured: {new Date(current.reading.timestamp).toLocaleString('en-GB', { timeZone: 'UTC' })} UTC</>}
          {!selectedPlant ? ' · Select a plant to assess status.' : !current.loading && current.reading && (statuses.key !== statusKey ? ' · Assessing status…' : statuses.source === 'demo' ? ' · Demo status labels.' : statuses.source === 'unavailable' ? ' · Status assessment unavailable.' : ' · AI status assessment.')}
        </p>
        <div className="sensor-grid">
          {sensors.map(({ key, label, unit }) => (
            <SensorCard
              key={key}
              type={key}
              label={label}
              value={current.reading?.[key]}
              unit={unit}
              status={selectedPlant && statuses.key === statusKey ? statuses.values[key] : undefined}
            />
          ))}
        </div>
      </section>

      <section className="historical-data" aria-labelledby="historical-data-title" aria-busy={historyLoading}>
        <div className="historical-data__header">
          <div>
            <h2 id="historical-data-title">Historical Data</h2>
            <p className="historical-data__source" role="status">
              {historyLoading ? 'Loading history…' : history.source === 'demo' ? 'Demo history — live data unavailable' : 'Backend data'}
              {' · '}{historyRange === '7d' ? '6-hour averages' : '24-hour averages'} · UTC
            </p>
          </div>
          <div className="historical-data__ranges" role="group" aria-label="History time range">
            <button type="button" className={historyRange === '7d' ? 'is-active' : ''} aria-pressed={historyRange === '7d'} onClick={() => setHistoryRange('7d')}>1 Week</button>
            <button type="button" className={historyRange === '30d' ? 'is-active' : ''} aria-pressed={historyRange === '30d'} onClick={() => setHistoryRange('30d')}>1 Month</button>
          </div>
        </div>
        <div className="history-grid">
          {sensors.map(({ key, label, unit }) => (
            <HistoryChart key={key} metric={key} label={label} unit={unit.trim()} readings={historyLoading ? [] : history.points} range={historyRange} />
          ))}
        </div>
      </section>

      <AlertPanel alerts={analysisData?.alerts || []} selectedPlant={selectedPlant} loading={analysisLoading} note={analysisNote} emptyText={selectedPlant && (!current.reading || analysisData?.status === 'no_data') ? 'Insufficient readings to assess warnings.' : analysis.source === 'demo' ? 'No warnings in this demonstration.' : undefined} />
      <div className="assistant-grid">
        <RecommendationCard selectedPlant={selectedPlant} recommendation={analysisData?.recommendation} loading={analysisLoading} note={analysisNote} />
        <ChatBox />
      </div>
    </main>
  );
}
