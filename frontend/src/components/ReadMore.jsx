// Long LLM text (Chair drafts run 560–740 characters): the first sentence, or ~limit characters cut at a word
// boundary, with a toggle that expands the full text inline. Short text renders as-is.
import { useState } from 'react'
import { shorten } from '../format.js'

export default function ReadMore({ text, limit = 240, label = 'Read more', className = '' }) {
  const [open, setOpen] = useState(false)
  const short = shorten(text, limit)
  return (
    <p data-component="read-more" data-expanded={short ? open : undefined} className={className}>
      {short && !open ? short : text}
      {short && (
        <>
          {' '}
          <button
            type="button"
            onClick={() => setOpen(!open)}
            className="no-print whitespace-nowrap font-sans text-xs font-semibold not-italic text-muted underline underline-offset-4 hover:text-ink"
          >
            {open ? 'Show less' : label}
          </button>
        </>
      )}
    </p>
  )
}
