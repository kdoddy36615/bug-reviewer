const express = require('express')
const { WebSocketServer } = require('ws')
const http = require('http')
const fs = require('fs')
const path = require('path')
const { exec } = require('child_process')

const bugsFile = process.argv[2]
if (!bugsFile) {
  console.error('Usage: node server.js <bugs.json> [results.json]')
  process.exit(1)
}

const bugs = JSON.parse(fs.readFileSync(path.resolve(bugsFile), 'utf8'))
const outputFile = path.resolve(process.argv[3] || 'results.json')

const app = express()
app.use(express.static(path.join(__dirname, 'public')))

// Serve screenshots from arbitrary absolute paths on the local filesystem
app.get('/screenshot', (req, res) => {
  const filePath = req.query.path
  if (!filePath || !fs.existsSync(filePath)) return res.status(404).json({ error: 'Not found' })
  res.sendFile(path.resolve(filePath))
})

const server = http.createServer(app)
const wss = new WebSocketServer({ server })

wss.on('connection', ws => {
  console.log('Browser connected')

  // Send all bugs at once — client handles navigation
  ws.send(JSON.stringify({ type: 'init', bugs, total: bugs.length }))

  ws.on('message', raw => {
    let msg
    try { msg = JSON.parse(raw.toString()) } catch { return }

    if (msg.type === 'submit') {
      const results = msg.results || []
      fs.writeFileSync(outputFile, JSON.stringify(results, null, 2))
      console.log(`\nResults  → ${outputFile}`)
      results.forEach(r => {
        const icon = r.status === 'approved' ? '✓' : r.status === 'declined' ? '✗' : '↩'
        console.log(`  ${icon}  #${r.id}${r.feedback ? ` — "${r.feedback}"` : ''}`)
      })
      ws.send(JSON.stringify({ type: 'done', total: results.length }))
      setTimeout(() => process.exit(0), 1200)
    }
  })

  ws.on('close', () => console.log('Browser disconnected'))
})

const PORT = process.env.BUG_REVIEWER_PORT || 3737

server.listen(PORT, () => {
  const url = `http://localhost:${PORT}`
  console.log(`Bug Reviewer → ${url}`)
  console.log(`Reviewing ${bugs.length} bug${bugs.length === 1 ? '' : 's'}`)
  const opener = process.platform === 'darwin' ? 'open' : process.platform === 'win32' ? 'start ""' : 'xdg-open'
  exec(`${opener} ${url}`)
})
