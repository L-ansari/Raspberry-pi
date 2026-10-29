export default function RecommendationCard({ selectedPlant, recommendation, loading = false, note = '' }) {
  return (
    <section className="recommendation-card assistant-panel" aria-labelledby="recommendation-title" aria-busy={loading}>
      <h2 id="recommendation-title">
        <svg viewBox="0 0 32 32" aria-hidden="true"><path d="m12 3 3 7 7 3-7 3-3 7-3-7-7-3 7-3Zm13 17 1.5 3.5L30 25l-3.5 1.5L25 30l-1.5-3.5L20 25l3.5-1.5Z" /></svg>
        AI Recommendation
      </h2>
      {loading ? <p className="assistant-panel__empty" role="status">Analyzing the selected period…</p> : !selectedPlant ? (
        <p className="assistant-panel__empty">Select a plant to view its recommendation.</p>
      ) : !recommendation ? (
        <p className="assistant-panel__empty">No recommendation is available for {selectedPlant.name} yet.</p>
      ) : (
        <div className="recommendation-card__advice">
          <p className="recommendation-card__plant">For {selectedPlant.name}</p>
          <h3>{recommendation.suggestion}</h3>
          <div className="recommendation-card__reason">
            <h4>Why this recommendation?</h4>
            <p>{recommendation.explanation}</p>
          </div>
        </div>
      )}
      {note && <p className="assistant-panel__note">{note}</p>}
    </section>
  );
}
