const alertTitles = {
  LOW_SOIL_MOISTURE: 'Low soil moisture',
};

export default function AlertPanel({ alerts = [], selectedPlant, loading = false, note = '', emptyText }) {
  const emptyMessage = emptyText || (selectedPlant
    ? `No warnings for ${selectedPlant.name} in this period.`
    : 'Select a plant to view its warnings.');

  return (
    <section className="alert-panel" aria-labelledby="alert-panel-title" aria-busy={loading}>
      <svg className="alert-panel__icon" viewBox="0 0 48 48" aria-hidden="true">
        <path d="M21.4 5.5a3 3 0 0 1 5.2 0l19 33A3 3 0 0 1 43 43H5a3 3 0 0 1-2.6-4.5l19-33Z" fill="currentColor" />
        <path d="M24 16v13m0 6v.5" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" />
      </svg>
      <div className="alert-panel__content">
        <h2 id="alert-panel-title">Alerts &amp; Warnings</h2>
        {loading ? <p role="status">Analyzing the selected period…</p> : alerts.length > 0 ? (
          <ul className="alert-panel__list">
            {alerts.map((alert, index) => (
              <li key={alert.id || `${alert.type}-${index}`}>
                <strong>{alert.title || alertTitles[alert.type] || 'Plant warning'}</strong>
                <p>{alert.message}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="alert-panel__empty">{emptyMessage}</p>
        )}
        {note && <p className="assistant-panel__note">{note}</p>}
      </div>
    </section>
  );
}
