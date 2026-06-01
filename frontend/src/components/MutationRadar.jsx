import { useState } from 'react'
import './MutationRadar.css'

const DRIFT_ZONES = [
  { label: 'Canonical', limit: 0.34 },
  { label: 'Drifting', limit: 0.67 },
  { label: 'High-Irony Mutation', limit: 1 },
]

function clamp01(value) {
  if (value < 0) return 0
  if (value > 1) return 1
  return value
}

function TrendVelocityBadge({ trending }) {
  return (
    <div className={`radar-badge${trending ? ' is-trending' : ' is-stable'}`}>
      <span className="radar-badge-icon" aria-hidden="true">
        {trending ? (
          '🔥'
        ) : (
          <svg viewBox="0 0 24 24" width="18" height="18">
            <path d="M3 12h18" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" fill="none" />
          </svg>
        )}
      </span>
      <span className="radar-badge-text">
        <strong>{trending ? 'Trending Mutation' : 'Stable Format'}</strong>
        <small>{trending ? 'High Velocity' : 'Low drift velocity'}</small>
      </span>
      {trending && (
        <svg className="radar-badge-spark" viewBox="0 0 48 20" width="48" height="20" aria-hidden="true">
          <polyline
            points="2,18 12,14 20,15 30,7 38,9 46,2"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </div>
  )
}

function DriftVectorGauge({ score }) {
  const hasScore = typeof score === 'number'
  const fill = hasScore ? clamp01(score) : 0
  const pct = Math.round(fill * 100)
  const zone = hasScore
    ? DRIFT_ZONES.find((entry) => fill <= entry.limit) ?? DRIFT_ZONES[DRIFT_ZONES.length - 1]
    : null
  return (
    <section className="radar-gauge">
      <header className="radar-section-head">
        <span>Drift Vector</span>
        <span className="radar-gauge-value">{hasScore ? score.toFixed(3) : '—'}</span>
      </header>
      <div className="radar-gauge-track">
        <div className="radar-gauge-fill" style={{ width: `${pct}%` }} />
        {hasScore && <div className="radar-gauge-thumb" style={{ left: `${pct}%` }} />}
      </div>
      <div className="radar-gauge-scale">
        <span>0.0 · Canonical Template</span>
        <span>1.0 · Extreme Drift</span>
      </div>
      <p className="radar-gauge-zone">
        {hasScore ? `Cosine distance to centroid · ${zone.label}` : 'Drift telemetry unavailable'}
      </p>
    </section>
  )
}

function SmallSampleNotice({ minMembers }) {
  return (
    <section className="radar-notice" role="status">
      <span className="radar-notice-icon" aria-hidden="true">ⓘ</span>
      <p>
        <strong>Accumulating baseline data:</strong> This template requires at least {minMembers} instances for drift telemetry.
      </p>
    </section>
  )
}

function VelocityGraph({ velocity, threshold }) {
  if (typeof velocity !== 'number') {
    return (
      <section className="radar-velocity">
        <header className="radar-section-head"><span>Mutation Velocity</span></header>
        <p className="radar-empty">Mutation telemetry unavailable.</p>
      </section>
    )
  }
  const ceiling = Math.max(threshold ?? 0, velocity, 0.0001) * 1.25
  const pct = clamp01(velocity / ceiling) * 100
  const thresholdPct = threshold !== null ? clamp01(threshold / ceiling) * 100 : null
  const hot = threshold !== null && velocity > threshold
  return (
    <section className="radar-velocity">
      <header className="radar-section-head">
        <span>Mutation Velocity</span>
        <span className={`radar-velocity-value${hot ? ' is-hot' : ''}`}>{velocity.toFixed(3)}</span>
      </header>
      <div className="radar-velocity-track">
        <div className={`radar-velocity-fill${hot ? ' is-hot' : ''}`} style={{ width: `${pct}%` }} />
        {thresholdPct !== null && (
          <div className="radar-velocity-threshold" style={{ left: `${thresholdPct}%` }} />
        )}
      </div>
      <p className="radar-velocity-caption">
        {hot ? 'Above trending threshold' : 'Within stable range'}
        {threshold !== null ? ` · threshold ${threshold.toFixed(2)}` : ''}
      </p>
    </section>
  )
}

function scatterPoint(index, total) {
  if (total <= 1) return { x: 78, y: 50 }
  const angle = (index / total) * Math.PI * 2
  return { x: 50 + Math.cos(angle) * 34, y: 50 + Math.sin(angle) * 34 }
}

function EvolutionTimeline({ template, variants, onNodeClick }) {
  const [loadingNode, setLoadingNode] = useState(null)
  const hasLineage = Boolean(template) || variants.length > 0
  const clickable = typeof onNodeClick === 'function'

  async function handleNodeClick(name) {
    if (!clickable || loadingNode) return
    setLoadingNode(name)
    try {
      await onNodeClick(name)
    } finally {
      setLoadingNode(null)
    }
  }

  return (
    <section className="radar-timeline">
      <header className="radar-section-head">
        <span>Evolution Timeline</span>
        {hasLineage && (
          <span className="radar-count">{variants.length} variant{variants.length === 1 ? '' : 's'}</span>
        )}
      </header>
      {!hasLineage ? (
        <p className="radar-empty">No lineage recorded for this template.</p>
      ) : (
        <>
          <svg className="radar-scatter" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
            <circle
              className={`radar-scatter-core${clickable ? ' radar-node-clickable' : ''}`}
              cx="50" cy="50" r="6"
              onClick={() => template && handleNodeClick(template)}
            />
            {variants.map((variant, index) => {
              const point = scatterPoint(index, variants.length)
              const isLoading = loadingNode === variant
              return (
                <g key={`${variant}-${index}`} onClick={() => handleNodeClick(variant)} style={{ cursor: clickable ? 'pointer' : 'default' }}>
                  <line className="radar-scatter-link" x1="50" y1="50" x2={point.x} y2={point.y} />
                  <circle
                    className={`radar-scatter-dot${isLoading ? ' radar-node-loading' : ''}${clickable ? ' radar-node-clickable' : ''}`}
                    cx={point.x} cy={point.y} r={isLoading ? 4.5 : 3}
                  />
                </g>
              )
            })}
          </svg>
          <ol className="radar-lineage">
            <li
              className={`radar-lineage-root${clickable ? ' radar-lineage-item-clickable' : ''}`}
              onClick={() => template && handleNodeClick(template)}
            >
              <span className="radar-node-dot" />
              <span className="radar-node-label">{template ?? 'unknown template'}</span>
              <span className="radar-node-tag">canonical</span>
              {loadingNode === template && <span className="radar-node-spinner" />}
            </li>
            {variants.map((variant, index) => {
              const isLoading = loadingNode === variant
              return (
                <li
                  key={`${variant}-${index}`}
                  className={clickable ? 'radar-lineage-item-clickable' : ''}
                  onClick={() => handleNodeClick(variant)}
                >
                  <span className="radar-node-dot" />
                  <span className="radar-node-label">{variant}</span>
                  <span className="radar-node-tag">mutation</span>
                  {isLoading && <span className="radar-node-spinner" />}
                </li>
              )
            })}
          </ol>
        </>
      )}
    </section>
  )
}

export default function MutationRadar({ model, onNodeClick }) {
  if (!model) return null
  return (
    <aside className="radar-panel" aria-label="Meme Mutation Radar">
      <TrendVelocityBadge trending={model.trendingMutation} />
      <DriftVectorGauge score={model.templateDriftScore} />
      {model.accumulatingBaseline ? (
        <SmallSampleNotice minMembers={model.minMembers} />
      ) : (
        <VelocityGraph velocity={model.velocity} threshold={model.threshold} />
      )}
      <EvolutionTimeline template={model.template} variants={model.variants} onNodeClick={onNodeClick} />
    </aside>
  )
}
