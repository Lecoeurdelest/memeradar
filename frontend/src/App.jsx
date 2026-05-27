import { useState } from 'react'
import './App.css'

const API = import.meta.env.VITE_API ?? 'http://localhost:8000'

export default function App() {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [visual, setVisual] = useState(0.35)
  const [active, setActive] = useState(null)

  const irony = +(1 - visual).toFixed(2)

  async function go(e) {
    e?.preventDefault()
    if (!q.trim()) return
    setLoading(true)
    try {
      const url = new URL(`${API}/search`)
      url.searchParams.set('q', q)
      url.searchParams.set('k', '24')
      url.searchParams.set('visual_weight', visual)
      url.searchParams.set('irony_weight', irony)
      const r = await fetch(url)
      const data = await r.json()
      setResults(data.results || [])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header>
        <h1>MemeRadar<span>.</span></h1>
        <p>Describe the vibe. We find the meme.</p>
      </header>

      <form className="bar" onSubmit={go}>
        <input
          autoFocus
          placeholder="absolute panic when production crashes..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button disabled={loading}>{loading ? '…' : 'Search'}</button>
      </form>

      <div className="weights">
        <label>
          visual <b>{visual.toFixed(2)}</b>
          <input
            type="range" min="0" max="1" step="0.05"
            value={visual}
            onChange={(e) => setVisual(parseFloat(e.target.value))}
          />
          irony <b>{irony.toFixed(2)}</b>
        </label>
      </div>

      <div className="grid">
        {results.map((m) => (
          <article key={m.id} className="card" onClick={() => setActive(m)}>
            <img src={m.image_url} alt={m.title} loading="lazy" />
            <div className="meta">
              <span className="tpl">{m.template}</span>
              <span className="score">{m.score.toFixed(3)}</span>
            </div>
          </article>
        ))}
      </div>

      {active && (
        <div className="modal" onClick={() => setActive(null)}>
          <div className="modal-inner" onClick={(e) => e.stopPropagation()}>
            <img src={active.image_url} alt="" />
            <div className="info">
              <h3>{active.title}</h3>
              <p className="irony">{active.irony}</p>
              <div className="lineage">
                <strong>Template:</strong> {active.lineage.template ?? active.template}
                {active.lineage.variants?.length > 0 && (
                  <>
                    <br />
                    <strong>Variants:</strong> {active.lineage.variants.join(', ')}
                  </>
                )}
              </div>
              <a href={active.permalink} target="_blank" rel="noreferrer">source ↗</a>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
