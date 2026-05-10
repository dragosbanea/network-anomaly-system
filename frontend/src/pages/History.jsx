import { useEffect, useState, useCallback } from 'react'
import { trafficApi } from '../api/api.js'

function fmt(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleString()
}

export default function History() {
  const [results, setResults] = useState([])
  const [showOnly, setShowOnly] = useState('all')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    const data = await trafficApi.getResults()
    setResults(data.reverse())
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const displayed = results.filter(r =>
    showOnly === 'all' ? true : showOnly === 'anomaly' ? r.anomaly : !r.anomaly
  )

  if (loading) return <div className="content"><div className="spinner" /></div>

  const totalAnomaly = results.filter(r => r.anomaly).length

  return (
    <div className="content">
      <div className="topbar" style={{ margin: '-24px -24px 24px', padding: '14px 24px' }}>
        <h1>Analysis History</h1>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ color: 'var(--text-dim)', fontSize: 13 }}>
            {results.length} total · {totalAnomaly} anomalies
          </span>
          {['all', 'anomaly', 'normal'].map(f => (
            <button
              key={f}
              className={`btn ${showOnly === f ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setShowOnly(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
          <button className="refresh-btn" onClick={load}>Refresh</button>
        </div>
      </div>

      <div className="card">
        {displayed.length === 0 ? (
          <div className="empty">No analysis results yet</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Analyzed At</th>
                <th>Source IP</th>
                <th>Destination IP</th>
                <th>Port</th>
                <th>Protocol</th>
                <th>Packets</th>
                <th>Bytes</th>
                <th>Duration</th>
                <th>Score</th>
                <th>Result</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {displayed.map(r => (
                <tr key={r.id}>
                  <td>{fmt(r.analyzedAt)}</td>
                  <td>{r.trafficFlow?.sourceIp ?? '-'}</td>
                  <td>{r.trafficFlow?.destinationIp ?? '-'}</td>
                  <td>{r.trafficFlow?.destinationPort ?? '-'}</td>
                  <td>{r.trafficFlow?.protocol ?? '-'}</td>
                  <td>{r.trafficFlow?.packetCount ?? '-'}</td>
                  <td>{r.trafficFlow?.byteCount?.toLocaleString() ?? '-'}</td>
                  <td>{r.trafficFlow?.duration?.toFixed(2) ?? '-'}s</td>
                  <td>{r.anomalyScore?.toFixed(3)}</td>
                  <td>
                    <span className={`badge-status ${r.anomaly ? 'anomaly' : 'normal'}`}>
                      {r.anomaly ? 'ANOMALY' : 'Normal'}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-dim)', fontSize: 12 }}>{r.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
