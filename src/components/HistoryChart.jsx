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

export default function HistoryChart({ label, metric, unit, readings }) {
  return (
    <article className="history-chart" aria-label={`${label} historical chart`}>
      <h3>{label} ({unit})</h3>
      {readings.length === 0 ? (
        <p className="history-chart__empty">No historical readings for this period.</p>
      ) : (
        <div className="history-chart__plot" role="img" aria-label={`${label} readings from ${dateLabel(readings[0].timestamp)} to ${dateLabel(readings.at(-1).timestamp)}`}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={readings} margin={{ top: 8, right: 12, bottom: 0, left: -20 }}>
              <CartesianGrid stroke="#e8ecef" vertical={false} />
              <XAxis dataKey="timestamp" tickFormatter={dateLabel} tick={{ fontSize: 11, fill: '#526278' }} tickLine={false} axisLine={{ stroke: '#ccd5dd' }} minTickGap={14} />
              <YAxis tick={{ fontSize: 11, fill: '#526278' }} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
              <Tooltip labelFormatter={dateLabel} formatter={(value) => [`${value} ${unit}`, label]} />
              <Area type="monotone" dataKey={metric} stroke="#136534" strokeWidth={2} fill="#e8f4ea" fillOpacity={0.8} dot={{ r: 3, fill: '#136534' }} activeDot={{ r: 5 }} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </article>
  );
}
