#!/usr/bin/env node
/**
 * Is the app usable on a phone?
 *
 * Passes when the layout viewport stays at the device width on every page. It
 * inflates when something refuses to fit, and the browser then scales the page
 * down — which is what "looks bad on mobile" turned out to mean here.
 *
 *   node scripts/mobile-check.mjs                      # the live site
 *   node scripts/mobile-check.mjs http://localhost:5173
 * API_URL overrides where the title page's id is looked up.
 *
 * Needs Playwright, which is not a dependency of this repo:
 *   npm i -D playwright && npx playwright install chromium
 * Or point at an existing install with PLAYWRIGHT_PATH.
 */
const BASE = process.argv[2] || 'https://anime-portal-gules.vercel.app'
// the API is a different host from the frontend, so the title page needs its own
const API = process.env.API_URL ||
  (BASE.includes('localhost') ? 'http://localhost:8000' : 'https://anime.necromemecon.party:2096')

let chromium, devices
try {
  ;({ chromium, devices } = await import(process.env.PLAYWRIGHT_PATH || 'playwright'))
} catch {
  console.error('Playwright not found. npm i -D playwright && npx playwright install chromium')
  console.error('(or set PLAYWRIGHT_PATH to an existing install)')
  process.exit(2)
}

const PAGES = [
  ['chat', '/'],
  ['browse', '/browse'],
  ['explore', '/explore'],
]

const browser = await chromium.launch()
const ctx = await browser.newContext({ ...devices['iPhone 13'] })
const page = await ctx.newPage()

// the title page needs a real id
let titleId = null
try {
  const res = await ctx.request.get(`${API}/api/anime?limit=1`)
  titleId = (await res.json())[0]?.id
} catch { /* fall back to skipping it */ }
if (titleId) PAGES.push(['title', `/title/${titleId}`])

let failed = 0
for (const [name, path] of PAGES) {
  await page.goto(BASE + path, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  const m = await page.evaluate(() => ({
    inner: window.innerWidth,
    scroll: document.documentElement.scrollWidth,
    // Content inside a deliberate horizontal scroller is meant to extend past
    // the edge — the Recent strip and the filter bar both do. Only report
    // elements that overflow the page itself.
    over: [...document.querySelectorAll('body *')]
      .filter(el => el.getBoundingClientRect().right > window.innerWidth + 1)
      .filter(el => {
        for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
          const ox = getComputedStyle(p).overflowX
          if (ox === 'auto' || ox === 'scroll') return false
        }
        return true
      })
      .slice(0, 6)
      .map(el => `${el.tagName.toLowerCase()}.${(el.className || '').toString().trim().split(/\s+/)[0]}`),
  }))
  const ok = m.inner === 390 && m.scroll <= m.inner
  if (!ok) failed++
  console.log(
    `${ok ? 'PASS' : 'FAIL'}  ${name.padEnd(8)} innerWidth ${m.inner}  scrollWidth ${m.scroll}` +
      (m.over.length ? `\n        past the edge: ${[...new Set(m.over)].join(', ')}` : '')
  )
}

await browser.close()
console.log(failed ? `\n${failed} of ${PAGES.length} pages do not fit` : `\nall ${PAGES.length} pages fit`)
process.exit(failed ? 1 : 0)
