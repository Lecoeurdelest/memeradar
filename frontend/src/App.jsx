import { useState, useRef, useEffect } from 'react'
import { searchMemes, randomMemes, uploadCheck, uploadIngest, resolveImageUrl, fetchMutations, buildMutationIndex, toMutationRadarModel, LANGUAGES, UPLOAD_STRINGS } from './api.js'
import MutationRadar from './components/MutationRadar.jsx'
import './App.css'

export default function App() {
  const [q, setQ] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState(null)
  const [visual, setVisual] = useState(0.35)
  const [lang, setLang] = useState('en')
  const [active, setActive] = useState(null)
  const [uploadState, setUploadState] = useState(null)
  const [uploadBusy, setUploadBusy] = useState(false)
  const [mutationIndex, setMutationIndex] = useState(() => buildMutationIndex(null))
  const [nodePreview, setNodePreview] = useState(null)
  const debounceRef = useRef(null)
  const lastQuery = useRef('')
  const fileInputRef = useRef(null)

  const irony = +(1 - visual).toFixed(2)
  const t = UPLOAD_STRINGS[lang] || UPLOAD_STRINGS.en

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  function sortByTimeline(arr) {
    return [...arr].sort((a, b) => {
      const aV = a.lineage?.variants?.length ?? 0
      const bV = b.lineage?.variants?.length ?? 0
      return bV - aV
    })
  }

  async function go(visualVal, queryVal, langVal) {
    const qTrimmed = (queryVal ?? q).trim()
    if (!qTrimmed) return
    lastQuery.current = qTrimmed
    setLoading(true)
    try {
      const data = await searchMemes({ q: qTrimmed, k: 24, visualWeight: visualVal ?? visual, ironyWeight: +(1 - (visualVal ?? visual)).toFixed(2), lang: langVal ?? lang })
      setResults(sortByTimeline(data.results || []))
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

  async function rollRandom(langVal) {
    setLoading(true)
    lastQuery.current = ''
    setQ('')
    try {
      const data = await randomMemes({ k: 24, lang: langVal ?? lang })
      setResults(sortByTimeline(data.results || []))
    } catch (err) {
      showToast('Could not load memes — backend error.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { rollRandom() }, [])

  useEffect(() => {
    let cancelled = false
    fetchMutations()
      .then((data) => { if (!cancelled) setMutationIndex(buildMutationIndex(data)) })
      .catch(() => { if (!cancelled) setMutationIndex(buildMutationIndex(null)) })
    return () => { cancelled = true }
  }, [])

  const radarModel = active ? toMutationRadarModel(active, mutationIndex) : null

  function onSlider(e) {
    const val = parseFloat(e.target.value)
    setVisual(val)
    if (!lastQuery.current) return
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => go(val, lastQuery.current), 400)
  }

  function onPickFile() {
    fileInputRef.current?.click()
  }

  async function onFileChosen(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (!file.type.startsWith('image/')) {
      showToast(t.pickImage)
      return
    }
    setUploadBusy(true)
    try {
      const data = await uploadCheck(file)
      setUploadState(data)
    } catch (err) {
      showToast(`${t.uploadFailed}: ${err.message}`)
    } finally {
      setUploadBusy(false)
    }
  }

  async function onConfirmNewMeme() {
    if (!uploadState) return
    setUploadBusy(true)
    try {
      const hit = await uploadIngest({ imageSha256: uploadState.image_sha256, title: null })
      setResults((prev) => [hit, ...(prev || [])])
      setUploadState(null)
      showToast(t.addedOk)
    } catch (err) {
      showToast(`${t.ingestFailed}: ${err.message}`)
    } finally {
      setUploadBusy(false)
    }
  }

  function onPickMatch(match) {
    setUploadState(null)
    setActive(match)
  }

  async function onTimelineNodeClick(templateName) {
    try {
      const data = await searchMemes({ q: templateName, k: 1, template: templateName, lang })
      const hit = data.results?.[0]
      if (hit) {
        setNodePreview({ meme: hit, templateName })
      } else {
        const fallback = await searchMemes({ q: templateName, k: 1, lang })
        const fallbackHit = fallback.results?.[0]
        if (fallbackHit) setNodePreview({ meme: fallbackHit, templateName })
        else showToast(`No memes found for "${templateName}"`)
      }
    } catch {
      showToast('Could not load meme for this template.')
    }
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
        <button type="button" className="roll-btn" onClick={() => rollRandom()} disabled={loading} title="Show random memes">🎲 Random</button>
        <button type="button" className="upload-btn" onClick={onPickFile} disabled={uploadBusy} title="Upload an image to check or add">
          {uploadBusy ? '…' : '⬆ Upload'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          style={{ display: 'none' }}
          onChange={onFileChosen}
        />
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

      <div className="lang-picker">
        {Object.entries(LANGUAGES).map(([code, label]) => (
          <button
            key={code}
            className={`lang-btn${lang === code ? ' active' : ''}`}
            onClick={() => { setLang(code); if (lastQuery.current) go(visual, lastQuery.current, code); else rollRandom(code) }}
          >{label}</button>
        ))}
      </div>

      {results !== null && results.length === 0 && (
        <div className="empty">No memes match — try a different query or adjust the weights.</div>
      )}

      <div className="grid">
        {(results || []).map((m) => (
          <article key={m.id} className="card" onClick={() => setActive(m)}>
            <img src={resolveImageUrl(m.image_url)} alt={m.title} loading="lazy" />
            <div className="meta">
              <span className="tpl">{m.template}</span>
              {m.score > 0 && <span className="score">{m.score.toFixed(3)}</span>}
            </div>
          </article>
        ))}
      </div>

      {active && (
        <div className="modal" onClick={() => setActive(null)}>
          <div className="modal-inner" onClick={(e) => e.stopPropagation()}>
            <img src={resolveImageUrl(active.image_url)} alt="" />
            <div className="info">
              <h3>{active.title}</h3>
              <p className="core-joke">{active.core_joke}</p>
              <p className="psych"><em>{active.psychological_state}</em></p>
              <p className="subtext">{active.subtext_context}</p>
              <a href={active.permalink} target="_blank" rel="noreferrer">source ↗</a>
            </div>
            {radarModel && <MutationRadar model={radarModel} onNodeClick={onTimelineNodeClick} />}
          </div>
        </div>
      )}

      {nodePreview && (
        <div className="node-preview-backdrop" onClick={() => setNodePreview(null)}>
          <div className="node-preview" onClick={(e) => e.stopPropagation()}>
            <button className="node-preview-close" onClick={() => setNodePreview(null)} aria-label="Close">✕</button>
            <div className="node-preview-tag">{nodePreview.templateName}</div>
            <div className="node-preview-body">
              <img src={resolveImageUrl(nodePreview.meme.image_url)} alt={nodePreview.meme.title} />
              <div className="node-preview-info">
                <h4>{nodePreview.meme.title}</h4>
                <p className="node-preview-joke">{nodePreview.meme.core_joke}</p>
                <p className="node-preview-psych"><em>{nodePreview.meme.psychological_state}</em></p>
                <div className="node-preview-actions">
                  <button className="node-preview-view" onClick={() => { setActive(nodePreview.meme); setNodePreview(null) }}>
                    View Full ↗
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {uploadState && (
        <div className="modal" onClick={() => !uploadBusy && setUploadState(null)}>
          <div className="modal-inner upload-modal" onClick={(e) => e.stopPropagation()}>
            <h3>
              {uploadState.is_exact_duplicate
                ? t.headerExact
                : uploadState.is_likely_duplicate
                  ? t.headerLikely
                  : t.headerAsk}
            </h3>
            <p className="upload-meta">
              SHA-256: <code>{uploadState.image_sha256.slice(0, 12)}…</code>
              {' · '}{t.bestScore}: <b>{uploadState.best_score.toFixed(3)}</b>
            </p>

            <div className="upload-preview">
              <div>
                <div className="upload-label">{t.youUploaded}</div>
                <img src={resolveImageUrl(uploadState.stored_path)} alt="upload preview" />
              </div>
            </div>

            <div className="upload-matches">
              {uploadState.matches.map((m) => (
                <button key={m.id} className="upload-match" onClick={() => onPickMatch(m)}>
                  <img src={resolveImageUrl(m.image_url)} alt={m.title} />
                  <div className="upload-match-meta">
                    <span className="tpl">{m.template}</span>
                    <span className="score">{m.score.toFixed(3)}</span>
                  </div>
                  <div className="upload-match-cta">{t.pickMatch}</div>
                </button>
              ))}
              {uploadState.matches.length === 0 && (
                <div className="empty">{t.noMatches}</div>
              )}
            </div>

            <div className="upload-actions">
              <button className="ghost" onClick={() => setUploadState(null)} disabled={uploadBusy}>{t.close}</button>
              {!uploadState.is_exact_duplicate && (
                <button className="primary" onClick={onConfirmNewMeme} disabled={uploadBusy}>
                  {uploadBusy ? '…' : t.addAsNew}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
