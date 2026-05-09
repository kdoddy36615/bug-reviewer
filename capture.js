// capture.js — builds a complete bug payload entry
//
// Usage:
//   node capture.js <config.json> <output.json>
//
// config.json shape:
// {
//   "id": 12345,
//   "title": "Bug title",
//   "description": "<p>HTML from your issue tracker</p>",
//   "adoScreenshots": ["/tmp/issue-1.png"],
//   "currentUrl": "https://preview.example.com/page",
//   "fixedUrl":   "https://preview.example.com/page",
//   "selector":   "optional CSS selector to screenshot a specific element",
//   "styles":     ["background-color", "border-color", "color"],
//   "repoPath":   "/Users/<you>/projects/<your-repo>"
// }
//
// What it does:
//   1. Takes a Playwright screenshot of currentUrl  → /tmp/bug-<id>-current.png
//   2. Takes a Playwright screenshot of fixedUrl    → /tmp/bug-<id>-fixed.png
//   3. Captures computed styles for the selector (if provided)
//   4. Runs git diff --unified=3 in repoPath and parses it into codeDiff format
//   5. Writes the complete payload entry to output.json
//
// problem + fix fields are intentionally left empty — Claude fills these in
// based on understanding of the bug before launching the reviewer.

const { chromium } = require('playwright')
const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const configFile = process.argv[2]
const outputFile = process.argv[3] || '/tmp/bug-payload.json'

if (!configFile) {
  console.error('Usage: node capture.js <config.json> [output.json]')
  process.exit(1)
}

const config = JSON.parse(fs.readFileSync(path.resolve(configFile), 'utf8'))
const { id, title, description, adoScreenshots, currentUrl, fixedUrl, selector, styles, repoPath } = config

const currentPath = `/tmp/bug-${id}-current.png`
const fixedPath   = `/tmp/bug-${id}-fixed.png`

;(async () => {
  const browser = await chromium.launch()
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, ignoreHTTPSErrors: true })
  const page = await context.newPage()

  // ── Current screenshot ──────────────────────────────────────────────────
  let currentStyles = null
  if (currentUrl) {
    await page.goto(currentUrl, { waitUntil: 'networkidle' })
    await page.waitForTimeout(500)

    if (selector) {
      const el = page.locator(selector).first()
      await el.screenshot({ path: currentPath })
      if (styles?.length) {
        currentStyles = await page.evaluate(({ sel, props }) => {
          const el = document.querySelector(sel)
          if (!el) return null
          const cs = window.getComputedStyle(el)
          return props.reduce((acc, p) => { acc[p] = cs.getPropertyValue(p).trim(); return acc }, {})
        }, { sel: selector, props: styles })
      }
    } else {
      await page.screenshot({ path: currentPath, fullPage: false })
    }
    console.log(`Current  → ${currentPath}`)
  } else {
    console.log('currentUrl not provided — skipping current screenshot')
  }

  // ── Fixed screenshot ────────────────────────────────────────────────────
  let fixedStyles = null
  if (fixedUrl) {
    await page.goto(fixedUrl, { waitUntil: 'networkidle' })
    await page.waitForTimeout(500)

    if (selector) {
      const el = page.locator(selector).first()
      await el.screenshot({ path: fixedPath })
      if (styles?.length) {
        fixedStyles = await page.evaluate(({ sel, props }) => {
          const el = document.querySelector(sel)
          if (!el) return null
          const cs = window.getComputedStyle(el)
          return props.reduce((acc, p) => { acc[p] = cs.getPropertyValue(p).trim(); return acc }, {})
        }, { sel: selector, props: styles })
      }
    } else {
      await page.screenshot({ path: fixedPath, fullPage: false })
    }
    console.log(`Fixed    → ${fixedPath}`)
  } else {
    console.log('fixedUrl not provided — skipping fixed screenshot')
  }

  await browser.close()

  // ── Code diff ───────────────────────────────────────────────────────────
  let codeDiff = null
  if (repoPath) {
    try {
      const rawDiff = execSync('git diff --unified=3', { cwd: repoPath }).toString()
      if (rawDiff.trim()) {
        codeDiff = parseUnifiedDiff(rawDiff)
        console.log(`Diff     → ${codeDiff.path} (${codeDiff.lines.length} lines)`)
      } else {
        console.log('No unstaged diff found — skipping codeDiff')
      }
    } catch (e) {
      console.warn('git diff failed:', e.message)
    }
  }

  // ── Assemble payload ────────────────────────────────────────────────────
  const payload = {
    id,
    title,
    description,
    problem: '',   // Claude fills this in before launching the reviewer
    fix:     '',   // Claude fills this in before launching the reviewer
    adoScreenshots: adoScreenshots || [],
    currentScreenshot: currentUrl ? currentPath : null,
    fixedScreenshot:   fixedUrl   ? fixedPath   : null,
    ...(currentStyles ? { currentStyles } : {}),
    ...(fixedStyles   ? { fixedStyles }   : {}),
    ...(codeDiff      ? { codeDiff }      : {}),
  }

  fs.writeFileSync(path.resolve(outputFile), JSON.stringify(payload, null, 2))
  console.log(`\nPayload  → ${outputFile}`)
  console.log('Next: fill in problem + fix fields, then add to bugs.json')
})()

// ── Unified diff parser ──────────────────────────────────────────────────────
function parseUnifiedDiff(rawDiff) {
  const fileMatch = rawDiff.match(/^diff --git a\/(.+?) b\//)
  const filePath = fileMatch ? fileMatch[1] : 'unknown'

  const allLines = rawDiff.split('\n')
  const out = { path: filePath, hunk: '', lines: [] }
  let oldNo = 0, newNo = 0
  let inHunk = false
  let lineCount = 0

  for (const raw of allLines) {
    if (lineCount >= 60) {
      // Hard cap — keep the panel readable
      out.lines.push({ type: 'hunk', text: '... diff truncated at 60 lines ...' })
      break
    }

    if (raw.startsWith('@@')) {
      const m = raw.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/)
      if (m) { oldNo = +m[1]; newNo = +m[2] }
      if (out.lines.length === 0) out.hunk = raw
      else out.lines.push({ type: 'hunk', text: raw })
      inHunk = true
      continue
    }

    if (!inHunk) continue
    if (raw.startsWith('+++') || raw.startsWith('---') || raw.startsWith('diff') || raw.startsWith('index')) continue

    const sign = raw[0]
    const content = raw.slice(1)

    if (sign === '+') {
      out.lines.push({ type: 'add', oldNo: null, newNo: newNo++, content })
      lineCount++
    } else if (sign === '-') {
      out.lines.push({ type: 'del', oldNo: oldNo++, newNo: null, content })
      lineCount++
    } else if (sign === ' ') {
      out.lines.push({ type: 'ctx', oldNo: oldNo++, newNo: newNo++, content })
      lineCount++
    }
  }

  return out
}
