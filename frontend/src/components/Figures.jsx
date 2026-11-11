// The site's figures. Fig. 1 is drawn from M-04's real constraints and the verifier's own
// measurements of the recorded drafts; the rest render whatever the live API returns.
import { pct } from '../mandates.js'

// ---------- Fig. 1: the feasible region ----------

// M-04 projected onto (tech weight, turnover), in %. Current book: 60% tech, turnover 0.
// Cutting tech by d forces turnover >= 2d (every dollar sold is bought elsewhere), so the
// projected feasible set is {tech <= 40, turnover <= 45, turnover >= 2(60 - tech)}: a sliver.
// Points are the verifier's measurements of each recorded round's draft and its repair.
const ROUNDS = [
  { n: 1, draft: [21.6, 124.3], fix: [39.1, 45.0] },
  { n: 2, draft: [40.4, 57.9], fix: [37.5, 45.0] },
]
const FINAL = [39.3, 43.4]
const SLIVER = [
  [37.5, 45],
  [40, 45],
  [40, 40],
]

const W = 540
const H = 420
const M = { l: 52, r: 14, t: 14, b: 46 }
const X = (v) => M.l + ((v - 10) / 60) * (W - M.l - M.r) // tech 10..70%
const Y = (v) => H - M.b - (v / 130) * (H - M.t - M.b) // turnover 0..130%

// inset: a zoom of tech 36.5..41, turnover 38..48
const IN = { x: 318, y: 22, w: 200, h: 150 }
const IX = (v) => IN.x + ((v - 36.5) / 4.5) * IN.w
const IY = (v) => IN.y + IN.h - ((v - 38) / 10) * IN.h

const poly = (pts, fx, fy) => pts.map(([a, b]) => `${fx(a)},${fy(b)}`).join(' ')

function Cross({ x, y, title }) {
  return (
    <g stroke="var(--bad)" strokeWidth="2.2" strokeLinecap="round">
      <title>{title}</title>
      <line x1={x - 5} y1={y - 5} x2={x + 5} y2={y + 5} />
      <line x1={x - 5} y1={y + 5} x2={x + 5} y2={y - 5} />
      <circle cx={x} cy={y} r="12" fill="transparent" stroke="none" />
    </g>
  )
}

export function FeasibleRegion() {
  return (
    <figure>
      <div className="fig">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-labelledby="fig1-t fig1-d">
          <title id="fig1-t">Feasible region for mandate M-04, projected onto tech weight and turnover</title>
          <desc id="fig1-d">
            The AI's round-1 draft sits at 21.6% tech and 124% turnover, far outside a thin feasible sliver near 40% tech and
            45% turnover. The verifier repairs it to 39.1% tech and 45% turnover.
          </desc>
          <defs>
            <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="var(--accent)" />
            </marker>
            <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="var(--rule)" strokeWidth="2" />
            </pattern>
          </defs>

          {/* unreachable region: below the turnover-needed line */}
          <polygon points={poly([[10, 0], [60, 0], [10, 100]], X, Y)} fill="url(#hatch)" />

          {/* grid + axes */}
          {[20, 30, 40, 50, 60, 70].map((t) => (
            <g key={t}>
              <line x1={X(t)} x2={X(t)} y1={Y(0)} y2={Y(130)} stroke="var(--grid)" />
              <text x={X(t)} y={H - M.b + 18} fontSize="11" textAnchor="middle" fill="var(--faint)">
                {t}%
              </text>
            </g>
          ))}
          {[0, 25, 50, 75, 100, 125].map((t) => (
            <g key={t}>
              <line x1={X(10)} x2={X(70)} y1={Y(t)} y2={Y(t)} stroke="var(--grid)" />
              <text x={M.l - 8} y={Y(t) + 4} fontSize="11" textAnchor="end" fill="var(--faint)">
                {t}%
              </text>
            </g>
          ))}
          <line x1={X(10)} x2={X(70)} y1={Y(0)} y2={Y(0)} stroke="var(--ink)" />
          <text x={X(40)} y={H - 6} fontSize="11.5" textAnchor="middle" fill="var(--muted)">
            TECH WEIGHT
          </text>
          <text x={14} y={Y(65)} fontSize="11.5" textAnchor="middle" fill="var(--muted)" transform={`rotate(-90 14 ${Y(65)})`}>
            TURNOVER
          </text>

          {/* constraint boundaries */}
          <line x1={X(40)} x2={X(40)} y1={Y(0)} y2={Y(130)} stroke="var(--ink)" strokeWidth="1.5" strokeDasharray="5 4" />
          <text x={X(40) - 6} y={Y(126)} fontSize="11" textAnchor="end" fill="var(--ink)">
            R3 tech ≤ 40%
          </text>
          <line x1={X(10)} x2={X(70)} y1={Y(45)} y2={Y(45)} stroke="var(--ink)" strokeWidth="1.5" strokeDasharray="5 4" />
          <text x={X(69)} y={Y(45) - 6} fontSize="11" textAnchor="end" fill="var(--ink)">
            R2 turnover ≤ 45%
          </text>
          <line x1={X(10)} x2={X(60)} y1={Y(100)} y2={Y(0)} stroke="var(--muted)" strokeWidth="1.2" />
          <text x={X(13)} y={Y(98)} fontSize="11" fill="var(--muted)" transform={`rotate(35 ${X(13)} ${Y(98)})`}>
            turnover ≥ 2·(60% − tech)
          </text>

          {/* the feasible sliver */}
          <polygon points={poly(SLIVER, X, Y)} fill="var(--accent)" />
          <rect
            x={X(36.5)}
            y={Y(48)}
            width={X(41) - X(36.5)}
            height={Y(38) - Y(48)}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="1"
          />
          <line x1={X(41)} y1={Y(48)} x2={IN.x} y2={IN.y + IN.h} stroke="var(--accent)" strokeWidth="0.8" strokeDasharray="2 3" />

          {/* current book */}
          <circle cx={X(60)} cy={Y(0)} r="5" fill="var(--paper)" stroke="var(--ink)" strokeWidth="1.8">
            <title>Current holdings: 60% tech, no turnover</title>
          </circle>
          <text x={X(60) + 8} y={Y(0) - 8} fontSize="11" fill="var(--ink)">
            current book
          </text>

          {/* drafts -> repairs */}
          {ROUNDS.map(({ n, draft, fix }) => (
            <g key={n}>
              <line
                x1={X(draft[0])}
                y1={Y(draft[1])}
                x2={X(fix[0])}
                y2={Y(fix[1])}
                stroke="var(--accent)"
                strokeWidth="1.6"
                strokeDasharray="4 4"
                markerEnd="url(#arr)"
              />
              <Cross
                x={X(draft[0])}
                y={Y(draft[1])}
                title={`AI draft, round ${n}: tech ${draft[0]}%, turnover ${draft[1]}%`}
              />
              <text
                x={X(draft[0]) + 9}
                y={Y(draft[1]) + (n === 1 ? 18 : 4)}
                fontSize="11"
                fill="var(--ink)"
              >
                AI draft · round {n}
              </text>
            </g>
          ))}

          {/* inset */}
          <rect x={IN.x} y={IN.y} width={IN.w} height={IN.h} fill="var(--paper)" stroke="var(--accent)" />
          <polygon points={poly(SLIVER, IX, IY)} fill="var(--accent-wash)" stroke="var(--accent)" strokeWidth="1.5" />
          <text x={IN.x + 6} y={IN.y + 14} fontSize="10.5" fill="var(--accent)">
            zoom · feasible set
          </text>
          {ROUNDS.map(({ n, fix }) => (
            <g key={n}>
              <circle cx={IX(fix[0])} cy={IY(fix[1])} r="4.5" fill="var(--accent)">
                <title>{`Repair of round ${n}: tech ${fix[0]}%, turnover ${fix[1]}%`}</title>
              </circle>
              <text
                x={IX(fix[0]) + (n === 2 ? -7 : 7)}
                y={IY(fix[1]) - 7}
                fontSize="10"
                textAnchor={n === 2 ? 'end' : 'start'}
                fill="var(--ink)"
              >
                repair {n}
              </text>
            </g>
          ))}
          <circle cx={IX(FINAL[0])} cy={IY(FINAL[1])} r="4.5" fill="var(--paper)" stroke="var(--good)" strokeWidth="2">
            <title>Round-3 draft: tech 39.3%, turnover 43.4%, compliant as drafted</title>
          </circle>
          <text x={IX(FINAL[0]) - 7} y={IY(FINAL[1]) + 16} fontSize="10" textAnchor="end" fill="var(--ink)">
            round 3 ✓
          </text>
        </svg>
      </div>
      <figcaption>
        <b>Fig. 1.</b> Mandate M-04 projected onto two of its dimensions. Cutting tech from 60% forces turnover of at least
        twice the cut, so with R2 and R3 the feasible set (cobalt) is a sliver. The AI's first draft lands at 124%
        turnover; the verifier moves it to the nearest compliant point. Other constraints (volatility, position limits)
        cut the set further and are not drawn. Points are the verifier's own measurements.
      </figcaption>
    </figure>
  )
}

// ---------- Fig. 2: the pipeline ----------

function Box({ label, title, children, accent }) {
  return (
    <div
      style={{
        border: `1px solid ${accent ? 'var(--accent)' : 'var(--rule)'}`,
        background: accent ? 'var(--accent-wash)' : 'var(--paper)',
        borderRadius: 8,
        padding: '10px 12px',
        flex: 1,
        minWidth: 0,
      }}
    >
      <div className="label" style={accent ? { color: 'var(--accent)' } : undefined}>
        {label}
      </div>
      <div style={{ fontWeight: 700, fontSize: 15, lineHeight: '22px' }}>{title}</div>
      <div className="small muted" style={{ fontSize: 13, lineHeight: '20px' }}>
        {children}
      </div>
    </div>
  )
}

const Arrow = () => (
  <div className="faint num" aria-hidden="true" style={{ alignSelf: 'center', padding: '0 2px', fontSize: 18 }}>
    →
  </div>
)

export function Pipeline() {
  return (
    <figure>
      <div className="fig pipeline">
        <div className="pipe-row">
          <Box label="LLM · ×3" title="Analysts">
            Macro, fundamentals and risk agents write memos
          </Box>
          <Arrow />
          <Box label="LLM" title="Allocator">
            Turns memos into weights w_draft
          </Box>
          <Arrow />
          <Box label="Deterministic · SCIP" title="Certus verifier" accent>
            Check → feasibility → conflict set → repair
          </Box>
          <Arrow />
          <Box label="Output" title="Certificate">
            Verdict, violations, repaired w, solver log, hashes
          </Box>
        </div>
        <div className="pipe-back small muted">
          <span className="num" style={{ color: 'var(--accent)' }}>↺</span> violations (actual vs limit) go back to the
          allocator for up to three revision rounds; whatever it returns is verified again
        </div>
      </div>
      <figcaption>
        <b>Fig. 2.</b> The language models only propose. Compliance is decided by an exact solver whose answer does not
        depend on the model, the prompt or the random seed.
      </figcaption>
    </figure>
  )
}

// ---------- weights: dumbbell (draft -> repaired) ----------

export function Dumbbell({ before, after, beforeLabel = 'AI draft', afterLabel = 'Repaired' }) {
  const tickers = [...new Set([...Object.keys(before), ...Object.keys(after)])]
  const rows = tickers
    .map((t) => ({ t, a: before[t] ?? 0, b: after[t] ?? 0 }))
    .filter((r) => r.a > 1e-4 || r.b > 1e-4)
    .sort((x, y) => Math.abs(y.b - y.a) - Math.abs(x.b - x.a))
  const max = Math.max(0.25, ...rows.map((r) => Math.max(r.a, r.b))) * 1.05
  const x = (v) => `${(v / max) * 100}%`
  return (
    <figure>
      <div className="db-legend label">
        <span>
          <i className="db-a" /> {beforeLabel}
        </span>
        <span>
          <i className="db-b" /> {afterLabel}
        </span>
      </div>
      <div className="db">
        {rows.map(({ t, a, b }) => (
          <div className="db-row" key={t} title={`${t}: ${pct(a)} → ${pct(b)}`}>
            <span className="num small">{t}</span>
            <span className="db-track">
              <span className="db-line" style={{ left: x(Math.min(a, b)), width: `calc(${x(Math.abs(b - a))})` }} />
              {a > 1e-4 && <span className="db-a" style={{ left: x(a) }} />}
              {b > 1e-4 && <span className="db-b" style={{ left: x(b) }} />}
            </span>
            <span className="num small r">
              <span className="faint">{a > 1e-4 ? pct(a) : '—'}</span> → {b > 1e-4 ? pct(b) : '—'}
            </span>
          </div>
        ))}
        <div className="db-row db-axis">
          <span />
          <span className="db-track">
            {[0, 0.1, 0.2].map((v) => (
              <span key={v} className="num" style={{ left: x(v) }}>
                {v * 100}%
              </span>
            ))}
          </span>
          <span />
        </div>
      </div>
    </figure>
  )
}

// ---------- constraint gauge (used in the checks table) ----------

const FLOOR = new Set(['min_weight', 'sector_min', 'min_holdings', 'buy_in'])

export function Gauge({ check }) {
  if (check.type === 'exclude') return null
  const max = Math.max(check.limit, check.actual) * 1.35 || 1
  const at = (v) => `${Math.min(100, (v / max) * 100)}%`
  const floor = FLOOR.has(check.type)
  return (
    <span className="gauge" title={`actual ${check.actual.toFixed(3)} vs ${floor ? 'floor' : 'cap'} ${check.limit}`}>
      <span className={`gauge-fill ${check.passed ? '' : 'bad'}`} style={{ width: at(check.actual) }} />
      <span className="gauge-tick" style={{ left: at(check.limit) }} />
    </span>
  )
}

// ---------- Case 2: the conflict, drawn ----------

const CAP_TYPES = new Set(['sector_max', 'max_weight'])
const FLOOR_TYPES = new Set(['min_weight', 'sector_min'])

/** Floors stacked against one cap; renders only for that shape of conflict (e.g. M-03). */
export function ConflictBar({ conflictIds, rules }) {
  const byId = Object.fromEntries(rules.map((r) => [r.id, r]))
  const set = conflictIds.map((id) => byId[id]).filter(Boolean)
  const caps = set.filter((r) => CAP_TYPES.has(r.type))
  const floors = set.filter((r) => FLOOR_TYPES.has(r.type))
  if (caps.length !== 1 || floors.length < 1) return null
  const cap = caps[0].params.max
  const total = floors.reduce((s, r) => s + r.params.min, 0)
  if (total <= cap) return null
  const max = total * 1.2
  const x = (v) => `${(v / max) * 100}%`
  const segs = floors.map((r, i) => ({ r, i, left: floors.slice(0, i).reduce((s, f) => s + f.params.min, 0) }))
  return (
    <figure>
      <div className="cb">
        <div className="cb-labels num">
          {segs.map(({ r, left }) => (
            <span key={r.id} style={{ left: x(left) }}>
              {r.id} · {r.params.ticker ?? r.params.sector} ≥ {pct(r.params.min)}
            </span>
          ))}
        </div>
        <div className="cb-bar">
          {segs.map(({ r, i, left }) => (
            <span
              key={r.id}
              className={`cb-seg ${i % 2 ? 'alt' : ''}`}
              style={{ left: x(left), width: `calc(${x(r.params.min)} - 2px)` }}
              title={`${r.id}: ${r.source}`}
            />
          ))}
          <span className="cb-over" style={{ left: x(cap), width: x(total - cap) }} title="Over the cap: no portfolio fits" />
          <span className="cb-cap" style={{ left: x(cap) }} />
        </div>
        <div className="cb-scale num">
          <span style={{ left: x(cap) }}>
            {caps[0].id} · {caps[0].params.sector ?? caps[0].params.ticker} ≤ {pct(cap)}
          </span>
          <span style={{ left: x(total) }} className="bad-text">
            floors need {pct(total)}
          </span>
        </div>
      </div>
      <figcaption>
        The floors alone need {pct(total)}, the cap allows {pct(cap)}: the hatched {((total - cap) * 100).toFixed(1)} points
        are why no portfolio exists.
      </figcaption>
    </figure>
  )
}

// ---------- Results: dot-and-whisker ----------

export function CIChart({ runs }) {
  const x = (v) => `${v}%`
  return (
    <figure>
      <div className="ci">
        {runs.map((run) => (
          <div key={run.model} className="ci-group">
            <div className="label" style={{ color: 'var(--ink)' }}>
              {run.model} · {run.n} trials · {run.broken} drafts violating
            </div>
            {run.rows.map((r) => (
              <div className="ci-row" key={r.name} title={`${r.name}: ${r.mean}% [${r.lo}, ${r.hi}]`}>
                <span className="small">{r.name}</span>
                <span className="ci-track">
                  <span className="ci-whisker" style={{ left: x(r.lo), width: x(r.hi - r.lo) }} />
                  <span className="ci-dot" style={{ left: x(r.mean) }} />
                </span>
                <span className="num small r">
                  {r.mean}% <span className="faint">[{r.lo}, {r.hi}]</span>
                </span>
              </div>
            ))}
          </div>
        ))}
        <div className="ci-row ci-axis">
          <span />
          <span className="ci-track">
            {[0, 25, 50, 75, 100].map((v) => (
              <span key={v} className="num" style={{ left: x(v) }}>
                {v}%
              </span>
            ))}
          </span>
          <span />
        </div>
      </div>
    </figure>
  )
}
