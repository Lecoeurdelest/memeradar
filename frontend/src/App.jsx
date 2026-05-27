import { useState, useRef, useEffect } from 'react'
import { searchMemes } from './api.js'
import './App.css'

export default function App() {
  const [q, setQ] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState(null)
  const [visual, setVisual] = useState(0.35)
  const [active, setActive] = useState(null)
  const debounceRef = useRef(null)
  const lastQuery = useRef('')

  const irony = +(1 - visual).toFixed(2)

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  async function go(visualVal, queryVal) {
    const qTrimmed = (queryVal ?? q).trim()
    if (!qTrimmed) return
    lastQuery.current = qTrimmed
    setLoading(true)
    try {
      const data = await searchMemes({ q: qTrimmed, k: 24, visualWeight: visualVal ?? visual, ironyWeight: +(1 - (visualVal ?? visual)).toFixed(2) })
      setResults(data.results || [])
    } catch (err) {
      showToast('Search failed — backend error. Try again.')
    } finally {
      setLoading(false)
    }
  }

  function onSubmit(e) {
    e?.preventDefault()
    go(visual, q.trim())
  }

  function onSlider(e) {
    const val = parseFloat(e.target.value)
    setVisual(val)
    if (!lastQuery.current) return
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => go(val, lastQuery.current), 400)
  }

  return (
    <div className="app">
      {toast && <div className="toast">{toast}</div>}

      <header>
        <h1>MemeRadar<span>.</span></h1>
        <p>Describe the vibe. We find the meme.</p>
      </header>

      <form className="bar" onSubmit={onSubmit}>
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
            onChange={onSlider}
          />
          irony <b>{irony.toFixed(2)}</b>
        </label>
      </div>

      {results !== null && results.length === 0 && (
        <div className="empty">No memes match — try a different query or adjust the weights.</div>
      )}

      <div className="grid">
        {(results || []).map((m) => (
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
              <p className="core-joke">{active.core_joke}</p>
              <p className="psych"><em>{active.psychological_state}</em></p>
              <p className="subtext">{active.subtext_context}</p>
              <div className="lineage">
                <strong>Template:</strong> {active.lineage?.template ?? active.template}
                {active.lineage?.variants?.length > 0 && (
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
