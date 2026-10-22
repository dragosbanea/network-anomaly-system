import { useEffect, useState } from 'react'
import { modelApi } from '../api/api.js'

function MetricCell({ value }) {
  if (value === undefined || value === null) return <td>—</td>
  const pct = Math.round(value * 100)
  const cls = pct >= 90 ? 'success' : pct >= 70 ? 'warning' : 'danger'
  return (
    <td>
      <span style={{ fontWeight: 600 }} className={cls === 'success' ? '' : ''}>
        {(value * 100).toFixed(1)}%
      </span>
      <div className="metric-bar-wrap">
        <div className="metric-bar-fill" style={{
          width: `${pct}%`,
          background: cls === 'success' ? 'var(--success)' : cls === 'warning' ? 'var(--warning)' : 'var(--danger)'
        }} />
      </div>
    </td>
  )
}

export default function ModelMetrics() {
  const [metrics, setMetrics] = useState(null)
  const [info, setInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      modelApi.getMetrics().catch(e => ({ error: e.response?.data?.error || e.message })),
      modelApi.getInfo().catch(() => null),
    ]).then(([m, i]) => {
      if (m?.error) setError(m.error)
      else setMetrics(m)
      setInfo(i)
      setLoading(false)
    })
  }, [])

  if (loading) return <div className="content"><div className="spinner" /></div>

  return (
    <div className="content">
      <div className="topbar" style={{ margin: '-24px -24px 24px', padding: '14px 24px' }}>
        <h1>Model Performance</h1>
        {metrics && (
          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
            Trained {new Date(metrics.trainedAt).toLocaleString()} · {metrics.nFeatures} features
          </span>
        )}
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--warning)', marginBottom: 16 }}>
          <div style={{ color: 'var(--warning)', marginBottom: 8, fontWeight: 600 }}>Metrics not available</div>
          <div style={{ color: 'var(--text-dim)', fontSize: 13 }}>{error}</div>
          <div style={{ marginTop: 12, background: 'var(--surface2)', borderRadius: 6, padding: '10px 14px', fontFamily: 'monospace', fontSize: 13 }}>
            cd ai &amp;&amp; python model.py --compare
          </div>
        </div>
      )}

      {info && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-title">Active Model</div>
          <div className="grid grid-4">
            <div className="monitor-row"><span>Type</span><span style={{ fontWeight: 600 }}>{info.type}</span></div>
            <div className="monitor-row"><span>Estimators</span><span>{info.nEstimators}</span></div>
            <div className="monitor-row"><span>Features</span><span>{info.nFeatures}</span></div>
            {info.classes && (
              <div className="monitor-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
                <span style={{ color: 'var(--text-dim)', fontSize: 12 }}>Classes</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {info.classes.map(c => (
                    <span key={c} style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 4, padding: '1px 6px', fontSize: 11 }}>{c}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {metrics && (
        <>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="section-header" style={{ marginBottom: 14 }}>
              <div className="section-title">Model Comparison — Binary (Attack vs. Benign)</div>
              <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                Test set: {metrics.nSamplesTest?.toLocaleString()} flows
              </span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1 Score</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['RandomForest', 'Supervised — trained on all labeled CICIDS2017 data'],
                  ['IsolationForest', 'Unsupervised — trained only on BENIGN flows'],
                  ['OneClassSVM', 'Semi-supervised — trained only on BENIGN flows'],
                ].map(([name, note]) => {
                  const m = metrics.models?.[name]
                  if (!m) return null
                  return (
                    <tr key={name}>
                      <td style={{ fontWeight: 600 }}>{name}</td>
                      <MetricCell value={m.precision} />
                      <MetricCell value={m.recall} />
                      <MetricCell value={m.f1} />
                      <td style={{ color: 'var(--text-dim)', fontSize: 12 }}>{note}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {metrics.models?.RandomForest?.perClass && (
            <div className="card">
              <div className="section-header" style={{ marginBottom: 14 }}>
                <div className="section-title">Random Forest — Per-Class Breakdown</div>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Attack Class</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1 Score</th>
                    <th>Test Samples</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(metrics.models.RandomForest.perClass)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([label, m]) => (
                      <tr key={label}>
                        <td>
                          <span className={`badge-severity ${label === 'BENIGN' ? 'LOW' : 'HIGH'}`}>
                            {label}
                          </span>
                        </td>
                        <MetricCell value={m.precision} />
                        <MetricCell value={m.recall} />
                        <MetricCell value={m.f1} />
                        <td style={{ color: 'var(--text-dim)' }}>{m.support?.toLocaleString()}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-title">Feature Set ({metrics.nFeatures} features)</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
              {(metrics.featuresBase || []).map(f => (
                <span key={f} className="feature-chip base">{f}</span>
              ))}
              {(metrics.featuresExt || []).map(f => (
                <span key={f} className="feature-chip ext">{f}</span>
              ))}
            </div>
            <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-dim)' }}>
              <span className="feature-chip base" style={{ marginRight: 6 }}>base</span> Original 11 features &nbsp;|&nbsp;
              <span className="feature-chip ext" style={{ marginRight: 6 }}>ext</span> Extended 8 features
            </div>
          </div>
        </>
      )}
    </div>
  )
}
