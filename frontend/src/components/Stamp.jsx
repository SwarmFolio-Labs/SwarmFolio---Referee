// The ink stamp: one word that says how the run ended, pressed on at a slight angle (thunk animation).
const KINDS = {
  PASS: { word: 'Compliant', tone: 'text-pass border-pass' },
  VIOLATIONS_REPAIRED: { word: 'Repaired', tone: 'text-warn-text border-warn' },
  RULES_INFEASIBLE: { word: 'Needs approval', tone: 'text-warn-text border-warn' },
  ERROR: { word: 'Not checked', tone: 'text-fail border-fail' },
}

export default function Stamp({ verdict, sub, size = 'md' }) {
  const k = KINDS[verdict] ?? KINDS.ERROR
  const big = size === 'lg'
  const small = size === 'sm'
  return (
    <div
      data-component="stamp"
      data-verdict={verdict}
      className={`inline-flex -rotate-3 animate-stamp flex-col items-center border-3 border-double px-3 py-1 ${k.tone} ${big ? 'px-4 py-1.5' : ''} ${small ? 'border-2 px-2' : ''}`}
    >
      <span className={`font-display font-bold uppercase leading-none tracking-wide ${big ? 'text-3xl' : small ? 'text-md' : 'text-xl'}`}>{k.word}</span>
      {sub && <span className="num mt-1 text-3xs uppercase tracking-wider">{sub}</span>}
    </div>
  )
}
