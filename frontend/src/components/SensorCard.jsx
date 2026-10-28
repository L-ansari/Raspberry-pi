const statusLabels = { normal: 'Normal', low: 'Low', high: 'High', unknown: 'Unknown' };

function SensorIcon({ type }) {
  const common = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' };

  return (
    <svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true" {...common}>
      {type === 'temperature' && <><path d="M14 19V7a3 3 0 0 1 6 0v12a6 6 0 1 1-6 0Z" /><path d="M17 11v13" /></>}
      {type === 'humidity' && <path d="M16 3C12 9 7 15 7 20a9 9 0 0 0 18 0c0-5-5-11-9-17Z" />}
      {type === 'soil_moisture' && <><path d="M16 28V14" /><path d="M16 19C8 19 5 15 5 9c7 0 11 3 11 10ZM16 17c0-7 4-10 11-10 0 6-3 10-11 10Z" /></>}
      {type === 'light' && <><circle cx="16" cy="16" r="6" /><path d="M16 2v5M16 25v5M2 16h5M25 16h5M6 6l4 4M22 22l4 4M26 6l-4 4M10 22l-4 4" /></>}
    </svg>
  );
}

export default function SensorCard({ label, value, unit, status, type }) {
  const shownValue = value == null ? '—' : `${value}${unit === '°C' ? ' ' : ''}${unit}`;
  const shownStatus = value == null ? 'No data' : statusLabels[status] || 'Status unavailable';

  return (
    <article className="sensor-card" aria-label={`${label}: ${shownValue}, ${shownStatus}`}>
      <span className="sensor-card__icon"><SensorIcon type={type} /></span>
      <div className="sensor-card__content">
        <h3>{label}</h3>
        <p className="sensor-card__value">{shownValue}</p>
        <span className={`sensor-card__status sensor-card__status--${statusLabels[status] && value != null ? status : 'unknown'}`}>
          {shownStatus}
        </span>
      </div>
    </article>
  );
}
