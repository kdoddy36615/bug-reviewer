// demo/run.js — generates a self-contained reviewer demo and launches the UI.
//
// Run with: npm run demo
//
// Renders two HTML pages (a "broken" and "fixed" pricing-card row) via Playwright,
// writes a bugs.json describing the bug, and spawns the reviewer server.
// The reviewer UI opens in your default browser at http://localhost:3737.
//
// All output is written to demo/.cache/ which is gitignored.

const { chromium } = require('playwright')
const { spawn } = require('child_process')
const fs = require('fs')
const path = require('path')

const cacheDir = path.join(__dirname, '.cache')
fs.mkdirSync(cacheDir, { recursive: true })

const tier = ({ name, price, features, featured, button }) => `
  <div style="
    flex:1;background:${featured ? 'linear-gradient(180deg,#1e1b4b 0%,#312e81 100%)' : 'white'};
    color:${featured ? 'white' : '#0a0a0a'};
    padding:36px 28px;border-radius:14px;
    box-shadow:${featured ? '0 24px 48px -12px rgba(79,70,229,0.45)' : '0 1px 2px rgba(0,0,0,0.06)'};
    border:${featured ? '2px solid #818cf8' : '1px solid #e5e5e5'};
    transform:${featured ? 'scale(1.06)' : 'none'};
    position:relative;z-index:${featured ? 2 : 1};
  ">
    ${featured ? '<div style="position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:#fbbf24;color:#1e1b4b;font-size:11px;font-weight:700;padding:4px 12px;border-radius:999px;letter-spacing:0.5px">MOST POPULAR</div>' : ''}
    <div style="font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:${featured ? '#a5b4fc' : '#737373'};margin-bottom:8px">${name}</div>
    <div style="font-size:38px;font-weight:700;margin-bottom:4px">${price}<span style="font-size:14px;font-weight:400;color:${featured ? '#c7d2fe' : '#737373'}">/mo</span></div>
    <ul style="list-style:none;padding:0;margin:24px 0;font-size:14px;line-height:1.9;color:${featured ? '#e0e7ff' : '#404040'}">
      ${features.map(f => `<li>✓&nbsp; ${f}</li>`).join('')}
    </ul>
    <button style="width:100%;padding:11px;background:${button.bg};color:${button.fg};border:${button.border || 'none'};border-radius:8px;font-size:14px;font-weight:600;cursor:pointer">${button.label}</button>
  </div>
`

const renderPage = (broken) => `
<html><body style="margin:0;background:#fafafa;font-family:Inter,system-ui,sans-serif;padding:48px 40px">
  <div style="max-width:1100px;margin:0 auto">
    <div style="text-align:center;margin-bottom:36px">
      <div style="font-size:32px;font-weight:700;color:#0a0a0a;margin-bottom:6px">Choose your plan</div>
      <div style="color:#525252">Cancel anytime. No setup fees.</div>
    </div>
    <div style="display:flex;gap:18px;align-items:stretch;padding:24px 0">
      ${tier({ name:'Starter', price:'$12', features:['10 projects','Basic analytics','Email support'], featured:false, button:{bg:'white',fg:'#0a0a0a',border:'1px solid #d4d4d4',label:'Get started'} })}
      ${broken
        ? tier({ name:'Pro', price:'$29', features:['Unlimited projects','Advanced analytics','Priority support','Custom domain','SSO'], featured:false, button:{bg:'white',fg:'#0a0a0a',border:'1px solid #d4d4d4',label:'Get started'} })
        : tier({ name:'Pro', price:'$29', features:['Unlimited projects','Advanced analytics','Priority support','Custom domain','SSO'], featured:true, button:{bg:'#fbbf24',fg:'#1e1b4b',label:'Start free trial'} })
      }
      ${tier({ name:'Enterprise', price:'$99', features:['Everything in Pro','Dedicated CSM','SLA','Audit logs'], featured:false, button:{bg:'white',fg:'#0a0a0a',border:'1px solid #d4d4d4',label:'Contact sales'} })}
    </div>
  </div>
</body></html>
`

;(async () => {
  console.log('Generating demo screenshots…')
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1100, height: 600 }, deviceScaleFactor: 2 })
  const screenshots = {}
  for (const [name, html] of [['current', renderPage(true)], ['fixed', renderPage(false)]]) {
    const page = await ctx.newPage()
    await page.setContent(html)
    const out = path.join(cacheDir, `bug-${name}.png`)
    await page.screenshot({ path: out })
    screenshots[name] = out
    await page.close()
  }
  await browser.close()

  const bugs = [
    {
      id: 1342546,
      title: 'Pricing — featured tier missing emphasis treatment',
      description:
        '<p>The middle pricing tier (<strong>Pro</strong>) is supposed to be the featured/recommended plan and visually dominate the row. On production right now it renders identically to the Starter and Enterprise tiers — same neutral background, same flat shadow, no scale, no border highlight, no "Most Popular" ribbon, and the CTA button is rendering as the default outline variant instead of the brand accent color.</p>',
      problem:
        'The Pro tier renders identically to the surrounding tiers — flat white background, no scale, no border highlight, no "Most Popular" ribbon, and the CTA uses the default outline variant. The card disappears in the row instead of pulling the eye.',
      fix: 'Wired the `featured` prop through `PricingTier` so the middle tier renders the indigo gradient background, the `scale-[1.06]` lift with `shadow-indigo-500/45`, the amber ribbon, and the brand `bg-amber-400` CTA. Updated `PricingTable` to pass `featured` for index `1`.',
      adoScreenshots: [],
      currentScreenshot: screenshots.current,
      fixedScreenshot: screenshots.fixed,
      codeDiff: {
        path: 'packages/ui/src/components/PricingTier/PricingTier.tsx',
        hunk: '@@ -18,24 +18,42 @@',
        lines: [
          { type: 'ctx', oldNo: 18, newNo: 18, content: 'type Props = {' },
          { type: 'ctx', oldNo: 19, newNo: 19, content: '  name: string' },
          { type: 'ctx', oldNo: 20, newNo: 20, content: '  price: string' },
          { type: 'ctx', oldNo: 21, newNo: 21, content: '  features: string[]' },
          { type: 'del', oldNo: 22, newNo: null, content: '  ctaLabel: string' },
          { type: 'add', oldNo: null, newNo: 22, content: '  ctaLabel: string' },
          { type: 'add', oldNo: null, newNo: 23, content: '  featured?: boolean' },
          { type: 'ctx', oldNo: 23, newNo: 24, content: '}' },
          { type: 'ctx', oldNo: 24, newNo: 25, content: '' },
          { type: 'del', oldNo: 25, newNo: null, content: 'export function PricingTier({ name, price, features, ctaLabel }: Props) {' },
          { type: 'add', oldNo: null, newNo: 26, content: 'export function PricingTier({ name, price, features, ctaLabel, featured = false }: Props) {' },
          { type: 'ctx', oldNo: 26, newNo: 27, content: '  return (' },
          { type: 'del', oldNo: 27, newNo: null, content: '    <article className="flex-1 bg-white text-neutral-950 p-9 rounded-2xl shadow-sm border border-neutral-200">' },
          { type: 'add', oldNo: null, newNo: 28, content: '    <article' },
          { type: 'add', oldNo: null, newNo: 29, content: '      className={cn(' },
          { type: 'add', oldNo: null, newNo: 30, content: "        'flex-1 p-9 rounded-2xl relative'," },
          { type: 'add', oldNo: null, newNo: 31, content: '        featured' },
          { type: 'add', oldNo: null, newNo: 32, content: "          ? 'bg-gradient-to-b from-indigo-950 to-indigo-800 text-white border-2 border-indigo-400 shadow-2xl shadow-indigo-500/45 scale-[1.06] z-10'" },
          { type: 'add', oldNo: null, newNo: 33, content: "          : 'bg-white text-neutral-950 border border-neutral-200 shadow-sm'" },
          { type: 'add', oldNo: null, newNo: 34, content: '      )}' },
          { type: 'add', oldNo: null, newNo: 35, content: '    >' },
          { type: 'add', oldNo: null, newNo: 36, content: '      {featured && (' },
          { type: 'add', oldNo: null, newNo: 37, content: '        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-400 text-indigo-950 text-[11px] font-bold tracking-wider px-3 py-1 rounded-full">' },
          { type: 'add', oldNo: null, newNo: 38, content: '          MOST POPULAR' },
          { type: 'add', oldNo: null, newNo: 39, content: '        </span>' },
          { type: 'add', oldNo: null, newNo: 40, content: '      )}' },
          { type: 'ctx', oldNo: 28, newNo: 41, content: '      <Heading tier={name} featured={featured} />' },
          { type: 'ctx', oldNo: 29, newNo: 42, content: '      <Price value={price} featured={featured} />' },
          { type: 'ctx', oldNo: 30, newNo: 43, content: '      <FeatureList items={features} featured={featured} />' },
          { type: 'del', oldNo: 31, newNo: null, content: '      <Button variant="outline">{ctaLabel}</Button>' },
          { type: 'add', oldNo: null, newNo: 44, content: "      <Button variant={featured ? 'brand' : 'outline'}>{ctaLabel}</Button>" },
          { type: 'ctx', oldNo: 32, newNo: 45, content: '    </article>' },
          { type: 'ctx', oldNo: 33, newNo: 46, content: '  )' },
          { type: 'ctx', oldNo: 34, newNo: 47, content: '}' },
        ],
      },
    },
  ]

  const bugsPath = path.join(cacheDir, 'bugs.json')
  const resultsPath = path.join(cacheDir, 'results.json')
  fs.writeFileSync(bugsPath, JSON.stringify(bugs, null, 2))

  console.log('Launching reviewer at http://localhost:3737')
  console.log('Approve, decline, or send feedback. Results write to demo/.cache/results.json.\n')

  const serverPath = path.join(__dirname, '..', 'server.js')
  const child = spawn(process.execPath, [serverPath, bugsPath, resultsPath], {
    stdio: 'inherit',
    env: process.env,
  })

  child.on('exit', code => process.exit(code ?? 0))
})().catch(err => {
  console.error(err)
  process.exit(1)
})
