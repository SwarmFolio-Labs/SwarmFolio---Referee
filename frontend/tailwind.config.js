/**
 * Maps the design tokens in src/index.css to Tailwind class names.
 * Colors, fonts, type sizes, spacing, radii and shadows REPLACE Tailwind's defaults (theme, not
 * theme.extend), so components can only use tokenized values. To restyle, edit index.css.
 */
const color = (name) => `rgb(var(--${name}) / <alpha-value>)`

const TOKEN_COLORS = ['bg', 'surface', 'sunken', 'ink', 'muted', 'faint', 'prose', 'placeholder', 'line', 'perforation',
  'before-bar', 'accent', 'on-accent', 'pass', 'fail', 'warn', 'warn-text', 'pass-tint', 'fail-tint', 'warn-tint',
  'concede', 'defend', 'modify']

// Tailwind's default spacing keys, each a multiple of --space-unit (p-4 = 4 units = 1rem by default).
const SPACING_STEPS = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 20, 24, 28, 32, 36, 40,
  44, 48, 52, 56, 60, 64, 72, 80, 96]
const spacing = {
  0: '0px',
  px: '1px',
  ...Object.fromEntries(SPACING_STEPS.map((n) => [n, `calc(var(--space-unit) * ${n})`])),
}

const size = (name, leading = true) => (leading ? [`var(--text-${name})`, `var(--leading-${name})`] : `var(--text-${name})`)

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      inherit: 'inherit',
      ...Object.fromEntries(TOKEN_COLORS.map((c) => [c, color(c)])),
    },
    borderColor: ({ theme }) => ({ ...theme('colors'), DEFAULT: color('line') }),
    fontFamily: {
      sans: 'var(--font-sans)',
      display: 'var(--font-display)',
      mono: 'var(--font-mono)',
    },
    fontSize: {
      '3xs': size('3xs', false),
      '2xs': size('2xs', false),
      xs: size('xs'),
      ui: size('ui'),
      sm: size('sm'),
      md: size('md'),
      base: size('base'),
      prose: size('prose'),
      lg: size('lg'),
      lead: size('lead'),
      xl: size('xl'),
      '2xl': size('2xl'),
      h3: size('h3'),
      '3xl': size('3xl'),
      '4xl': size('4xl'),
      '5xl': size('5xl'),
      '6xl': size('6xl'),
    },
    fontWeight: {
      normal: 'var(--weight-normal)',
      medium: 'var(--weight-medium)',
      semibold: 'var(--weight-semibold)',
      bold: 'var(--weight-bold)',
    },
    letterSpacing: {
      normal: '0em',
      tight: 'var(--tracking-tight)',
      snug: 'var(--tracking-snug)',
      wide: 'var(--tracking-wide)',
      wider: 'var(--tracking-wider)',
    },
    spacing,
    maxWidth: {
      none: 'none',
      full: '100%',
      page: 'var(--page-width)',
      prose: 'var(--prose-width)',
      lede: 'var(--lede-width)',
    },
    borderRadius: {
      none: '0px',
      DEFAULT: 'var(--radius-sm)',
      md: 'var(--radius-control)',
      card: 'var(--radius-card)',
      chip: 'var(--radius-chip)',
      full: '9999px',
    },
    boxShadow: {
      none: 'none',
      card: 'var(--shadow-card)',
    },
    extend: {
      gridTemplateColumns: {
        'price-tag': '1fr var(--price-meter-width)',
        stance: 'calc(var(--space-unit) * 2) 1fr',
        conflict: '1fr var(--aside-width)',
        receipt: 'var(--receipt-width) 1fr',
        'receipt-row': '1fr auto',
      },
      borderWidth: { 3: '3px' },
      keyframes: {
        stamp: {
          '0%': { opacity: '0', transform: 'rotate(-4deg) scale(1.6)' },
          '70%': { opacity: '1', transform: 'rotate(-4deg) scale(0.96)' },
          '100%': { opacity: '1', transform: 'rotate(-4deg) scale(1)' },
        },
        reveal: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        reveal: 'reveal var(--motion-reveal) ease-out both',
        stamp: 'stamp var(--motion-stamp) cubic-bezier(0.2, 0.8, 0.3, 1.2) both',
      },
    },
  },
  plugins: [],
}
