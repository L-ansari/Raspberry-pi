import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const dateLabel = (timestamp) => new Intl.DateTimeFormat('en', {
  month: 'short', day: 'numeric', timeZone: 'UTC',
}).format(new Date(timestamp));

const timeLabel = (timestamp) => new Date(timestamp).toLocaleString('en-GB', { timeZone: 'UTC' });

function HistoryTooltip({ active, payload, metric, unit }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return <div className="history-tooltip">
    <p>{timeLabel(point.window_start)} – {timeLabel(point.window_end)} UTC</p>
    <p>Average: {Number(point[metric]).toFixed(1)} {unit}</p>
    <p>Min: {point.minimum?.[metric]} · Max: {point.maximum?.[metric]} {unit}</p>
    <p>Samples: {point.sample_count}</p>
  </div>;
}

export default function HistoryChart({ label, metric, unit, readings, range }) {
  const end = Date.parse(readings.at(-1)?.window_end);
  const tickCount = range === '30d' ? 5 : 7;
  const stepDays = range === '30d' ? 7 : 1;
  const dateTicks = Array.from({ length: tickCount }, (_, index) => (
    end - (tickCount - 1 - index) * stepDays * 24 * 60 * 60 * 1000
  ));
  return (
    <article className="history-chart" aria-label={`${label} historical chart`}>
      <h3>{label} ({unit})</h3>
      {!readings.some((point) => point[metric] != null) ? (
        <p className="history-chart__empty">No historical readings for this period.</p>
      ) : (
        <div className="history-chart__plot" role="img" aria-label={`${label} readings from ${dateLabel(readings[0].timestamp)} to ${dateLabel(readings.at(-1).timestamp)}`}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={readings.map((point) => ({ ...point, time: Date.parse(point.timestamp) }))} margin={{ top: 8, right: 12, bottom: 0, left: -20 }}>
              <CartesianGrid stroke="#e8ecef" vertical={false} />
              <XAxis type="number" scale="time" dataKey="time" domain={[Date.parse(readings[0].window_start), end]} ticks={dateTicks} interval={0} tickFormatter={dateLabel} tick={{ fontSize: 11, fill: '#526278' }} angle={-40} textAnchor="end" height={42} tickLine={false} axisLine={{ stroke: '#ccd5dd' }} />
              <YAxis tick={{ fontSize: 11, fill: '#526278' }} tickLine={false} axisLine={false} domain={unit === '%' ? [0, 100] : metric === 'light' ? [0, 'auto'] : ['auto', 'auto']} />
              <Tooltip content={<HistoryTooltip metric={metric} unit={unit} />} />
              <Area type="linear" connectNulls={false} dataKey={metric} stroke="#136534" strokeWidth={2} fill="#e8f4ea" fillOpacity={0.8} dot={false} activeDot={{ r: 5 }} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </article>
  );
}
