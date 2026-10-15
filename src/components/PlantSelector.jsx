import { useState } from 'react';

export default function PlantSelector({ plants, selectedPlant, onSelect }) {
  const [query, setQuery] = useState('');
  const matches = query.trim()
    ? plants.filter((plant) => plant.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))
    : [];

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
          />
          {query.trim() && (
            <ul className="plant-results" aria-label="Matching plants">
              {matches.length ? matches.map((plant) => (
                <li key={plant.id}>
                  <button type="button" onClick={() => { onSelect(plant); setQuery(''); }}>
                    {plant.name}
                  </button>
                </li>
              )) : <li>No matching plants</li>}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
