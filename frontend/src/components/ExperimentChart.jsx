// The experiment's learning curve: compliance after each round per feedback condition, with 95% CI bands.
import { CONDITIONS } from '../experiment.js'
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function ExperimentChart({ summary }) {
  const rounds = summary[CONDITIONS[0].id].per_round.length
  const data = Array.from({ length: rounds }, (_, r) => {
    const row = { round: r }
    for (const c of CONDITIONS) {
      const [m, lo, hi] = summary[c.id].per_round[r].compliance
      row[c.id] = +(m * 100).toFixed(1)
      row[`${c.id}_ci`] = [+(lo * 100).toFixed(1), +(hi * 100).toFixed(1)]
    }
    return row
  })
  return (
    <div data-component="experiment-chart">
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data} margin={{ top: 10, right: 16, left: -8, bottom: 0 }}>
        <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
        <XAxis dataKey="round" tickFormatter={(r) => `Round ${r}`} tickLine={false} axisLine={false} />
        <YAxis domain={[0, 100]} unit="%" tickLine={false} axisLine={false} />
        <Tooltip
          formatter={(v, name) => (Array.isArray(v) ? [`${v[0]}–${v[1]}%`, `${name} 95% CI`] : [`${v}%`, name])}
          labelFormatter={(r) => `Round ${r}`}
        />
        <Legend />
        {CONDITIONS.map((c) => (
          <Area key={`${c.id}_ci`} dataKey={`${c.id}_ci`} stroke="none" fill={c.color} fillOpacity={0.12} legendType="none" name={c.label} isAnimationActive={false} />
        ))}
        {CONDITIONS.map((c) => (
          <Line key={c.id} dataKey={c.id} name={c.label} stroke={c.color} strokeWidth={2.5} dot={{ r: 4 }} type="monotone" />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
    </div>
  )
}
