// Fails if a component hard-codes a color, font, size or arbitrary Tailwind value instead of using
// the design tokens (src/index.css + tailwind.config.js). Run: npm run check:tokens
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const BANNED = [
  [/#[0-9a-fA-F]{3,8}\b/, 'hex color'],
  [/\brgba?\(\s*\d/, 'rgb() color'],
  [/\bhsla?\(/, 'hsl() color'],
  [/\b(text|bg|border|fill|stroke|ring)-(white|black|gray|slate|zinc|red|green|blue|amber|yellow)\b/, 'Tailwind palette color'],
  [/\b[a-z-]+-\[[^\]]+\]/, 'arbitrary Tailwind value'],
  [/fontFamily\s*:/, 'inline font family'],
  [/fontSize\s*:/, 'inline font size'],
]

const files = (dir) =>
  readdirSync(dir).flatMap((f) => {
    const p = join(dir, f)
    return statSync(p).isDirectory() ? files(p) : /\.(jsx?|tsx?)$/.test(p) ? [p] : []
  })

let bad = 0
for (const file of files('src')) {
  readFileSync(file, 'utf8')
    .split('\n')
    .forEach((line, i) => {
      for (const [re, what] of BANNED) {
        if (re.test(line)) {
          bad++
          console.log(`${file}:${i + 1}: ${what}: ${line.trim()}`)
        }
      }
    })
}
if (bad) {
  console.log(`\n${bad} hard-coded style value(s). Add a token in src/index.css instead.`)
  process.exit(1)
}
console.log('check:tokens OK: no hard-coded colors, fonts or arbitrary values in src/')
