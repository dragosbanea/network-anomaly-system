import { useEffect, useState, useCallback } from 'react'
import { alertsApi } from '../api/api.js'
import { useAlertWebSocket } from '../hooks/useAlertWebSocket.js'

function fmt(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleString()
}

function ScoreBar({ score }) {
  const w = Math.round((score || 0) * 100)
  const cls = w > 70 ? 'high' : w > 40 ? 'medium' : 'low'
  return (
    <div className="score-bar">
      <div className="score-fill" style={{ width: w * 0.8, height: 6, borderRadius: 3 }} data-cls={cls} />
      <span>{score?.toFixed(3)}</span>
    </div>
  )
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [newCount, setNewCount] = useState(0)

  const load = useCallback(async () => {
    const data = await alertsApi.getAll()
    setAlerts(data)
    setNewCount(0)
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [load])

  // Append new alert instantly via WebSocket
  useAlertWebSocket(useCallback((alert) => {
    setAlerts(prev => {
      if (prev.some(a => a.id === alert.id)) return prev
      return [alert, ...prev]
    })
    setNewCount(n => n + 1)
  }, []))

  async function resolve(id) {
    await alertsApi.resolve(id)
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, resolved: true } : a))
  }

  const displayed = alerts.filter(a =>
    filter === 'all' ? true : filter === 'active' ? !a.resolved : a.resolved
  )

  if (loading) return <div className="content"><div className="spinner" /></div>

  return (
    <div className="content">
      <div className="topbar" style={{ margin: '-24px -24px 24px', padding: '14px 24px' }}>
        <h1>
          Alerts
          {newCount > 0 && (
            <span className="badge" style={{ marginLeft: 8 }}>{newCount} new</span>
          )}
        </h1>
        <div style={{ display: 'flex', gap: 8 }}>
          {['all', 'active', 'resolved'].map(f => (
            <button
              key={f}
              className={`btn ${filter === f ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
          <button className="refresh-btn" onClick={load}>Refresh</button>
        </div>
      </div>

      <div className="card">
        <div className="section-header">
          <div className="section-title">{displayed.length} alert{displayed.length !== 1 ? 's' : ''}</div>
        </div>
        {displayed.length === 0 ? (
          <div className="empty">No alerts found</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Source IP</th>
                <th>Destination</th>
                <th>Protocol</th>
                <th>Score</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {displayed.map(a => (
                <tr key={a.id}>
                  <td>{fmt(a.createdAt)}</td>
                  <td>{a.alertType}</td>
                  <td><span className={`badge-severity ${a.severity}`}>{a.severity}</span></td>
                  <td>{a.sourceIp}</td>
                  <td>{a.destinationIp}:{a.destinationPort}</td>
                  <td>{a.protocol}</td>
                  <td><ScoreBar score={a.anomalyScore} /></td>
                  <td>
                    <span className={`badge-status ${a.resolved ? 'normal' : 'anomaly'}`}>
                      {a.resolved ? 'Resolved' : 'Active'}
                    </span>
                  </td>
                  <td>
                    {!a.resolved && (
                      <button className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }}
                        onClick={() => resolve(a.id)}>
                        Resolve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
