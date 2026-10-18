/**
 * Design tokens live in src/index.css as CSS variables; this file only maps them to
 * Tailwind names. To restyle the app (Paper design), change the variables, not the components.
 */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: v('bg'),
        surface: v('surface'),
        sunken: v('sunken'),
        ink: v('ink'),
        muted: v('muted'),
        line: v('line'),
        accent: v('accent'),
        pass: v('pass'),
        fail: v('fail'),
        warn: v('warn'),
        concede: v('concede'),
        defend: v('defend'),
        modify: v('modify'),
      },
      fontFamily: {
        sans: 'var(--font-sans)',
        display: 'var(--font-display)',
        mono: 'var(--font-mono)',
      },
      borderRadius: {
        card: 'var(--radius-card)',
        chip: 'var(--radius-chip)',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
      },
      keyframes: {
        reveal: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        reveal: 'reveal 360ms ease-out both',
      },
    },
  },
  plugins: [],
}
