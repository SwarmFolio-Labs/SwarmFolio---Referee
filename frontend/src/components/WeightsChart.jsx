// Before/after weights as grouped bars (e.g. first draft vs final, or proposal vs Referee repair).
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function WeightsChart({ before, after, beforeLabel = 'Before', afterLabel = 'After', height = 260 }) {
  const tickers = [...new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})])]
  const data = tickers
    .map((t) => ({
      ticker: t,
      before: +(((before ?? {})[t] ?? 0) * 100).toFixed(2),
      after: +(((after ?? {})[t] ?? 0) * 100).toFixed(2),
    }))
    .filter((d) => d.before > 0.01 || d.after > 0.01)
    .sort((a, b) => Math.max(b.before, b.after) - Math.max(a.before, a.after))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} barGap={2}>
        <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
        <XAxis dataKey="ticker" tick={{ fontSize: 11, fontFamily: 'var(--font-mono)' }} tickLine={false} axisLine={false} />
        <YAxis unit="%" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <Tooltip formatter={(v) => `${v.toFixed(1)}%`} cursor={{ fill: 'rgb(var(--sunken))' }} />
        <Legend wrapperStyle={{ fontSize: 12 }} iconType="square" />
        <Bar dataKey="before" name={beforeLabel} fill="var(--chart-before)" radius={[3, 3, 0, 0]} />
        <Bar dataKey="after" name={afterLabel} fill="var(--chart-after)" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
