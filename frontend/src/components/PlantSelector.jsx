import { useEffect, useRef, useState } from 'react';
import { searchPlants } from '../services/api.js';

export default function PlantSelector({ plants, selectedPlant, onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState({ query: '', plants: [], source: 'backend' });
  const cache = useRef(new Map());
  const term = query.trim();
  useEffect(() => {
    if (!term) return;
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      const cached = cache.current.get(term.toLowerCase());
      if (cached && Date.now() - cached.at < 300_000) {
        setResults({ query: term, plants: cached.plants, source: 'backend' });
        return;
      }
      try {
        const data = await searchPlants(term, { signal: controller.signal });
        if (!Array.isArray(data.results) || !data.results.every((item) => typeof item.id === 'string' && typeof item.name === 'string')) throw new Error('Invalid plant list');
        if (active) {
          if (cache.current.size >= 20) cache.current.delete(cache.current.keys().next().value);
          cache.current.set(term.toLowerCase(), { at: Date.now(), plants: data.results });
          setResults({ query: term, plants: data.results, source: 'backend' });
        }
      } catch {
        if (active) setResults({ query: term, plants: plants.filter((plant) => plant.name.toLowerCase().includes(term.toLowerCase())), source: 'demo' });
      }
    }, 300);
    const timeout = setTimeout(() => controller.abort(), 10_000);
    return () => { active = false; clearTimeout(timer); clearTimeout(timeout); controller.abort(); };
  }, [term, plants]);
  const pending = term !== results.query;
  const matches = pending ? [] : results.plants;

  return (
    <section aria-labelledby="plant-selector-title" className="plant-selector">
      <h2 id="plant-selector-title">Select your plant</h2>
      <div className="plant-selector__row">
        <p className="plant-selector__current" aria-live="polite">
          <span>Current plant: </span>
          <strong>{selectedPlant?.name || 'None selected'}</strong>
        </p>
        <div className="plant-selector__search">
          <label htmlFor="plant-search">Search plant type</label>
          <input
            id="plant-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Type a plant name"
            autoComplete="off"
            maxLength={100}
          />
          {query.trim() && (
            <ul className="plant-results" aria-label="Matching plants">
              {pending ? <li className="plant-results__note" role="status">Searching plants…</li> : <>
              {results.source === 'demo' && <li className="plant-results__note">Demo plants — search unavailable</li>}
              {matches.length ? matches.map((plant) => (
                <li key={plant.id}>
                  <button type="button" onClick={() => { onSelect(plant); setQuery(''); }}>
                    {plant.name}
                  </button>
                </li>
              )) : <li>No matching plants</li>}
              </>}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
