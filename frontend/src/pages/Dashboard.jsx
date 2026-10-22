import { useEffect, useState, useCallback } from 'react'
import { statsApi, alertsApi } from '../api/api.js'
import { useAlertWebSocket } from '../hooks/useAlertWebSocket.js'

function StatCard({ title, value, sub, className }) {
  return (
    <div className="card">
      <div className="card-title">{title}</div>
      <div className={`stat-value ${className || ''}`}>{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [recentAlerts, setRecentAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [wsStatus, setWsStatus] = useState('connecting')

  const load = useCallback(async () => {
    try {
      const [s, a] = await Promise.all([
        statsApi.getDashboard(),
        alertsApi.getRecent(60),
      ])
      setStats(s)
      setRecentAlerts(a.slice(0, 8))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 10000)
    return () => clearInterval(id)
  }, [load])

  // Real-time alerts via WebSocket — prepend new alert without waiting for poll
  useAlertWebSocket(useCallback((alert) => {
    setRecentAlerts(prev => [alert, ...prev].slice(0, 8))
    setStats(prev => prev ? {
      ...prev,
      totalAnomalies: (prev.totalAnomalies || 0) + 1,
      unresolvedAlerts: (prev.unresolvedAlerts || 0) + 1,
      ...(alert.severity === 'CRITICAL' ? { criticalAlerts: (prev.criticalAlerts || 0) + 1 } : {}),
    } : prev)
  }, []), useCallback(() => setWsStatus('connected'), []))

  if (loading) return <div className="content"><div className="spinner" /></div>

  const anomalyRate = stats?.anomalyRate?.toFixed(1) ?? '0.0'

  return (
    <div className="content">
      <div className="topbar" style={{ margin: '-24px -24px 24px', padding: '14px 24px' }}>
        <h1>Dashboard</h1>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span className={`ws-indicator ${wsStatus}`} title={`WebSocket: ${wsStatus}`}>
            {wsStatus === 'connected' ? 'Live' : 'Connecting...'}
          </span>
          <button className="refresh-btn" onClick={load}>Refresh</button>
        </div>
      </div>

      <div className="grid grid-4" style={{ marginBottom: 24 }}>
        <StatCard title="Total Flows Analyzed" value={stats?.totalFlows ?? 0} className="accent" />
        <StatCard title="Anomalies Detected" value={stats?.totalAnomalies ?? 0} sub={`${anomalyRate}% anomaly rate`} className="danger" />
        <StatCard title="Unresolved Alerts" value={stats?.unresolvedAlerts ?? 0} className="warning" />
        <StatCard title="Critical Alerts" value={stats?.criticalAlerts ?? 0} className="danger" />
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="section-header">
            <div className="section-title">Alert Severity Breakdown</div>
          </div>
          <table>
            <thead><tr><th>Severity</th><th>Count</th></tr></thead>
            <tbody>
              {['CRITICAL','HIGH','MEDIUM','LOW'].map(s => (
                <tr key={s}>
                  <td><span className={`badge-severity ${s}`}>{s}</span></td>
                  <td>{stats?.[s.toLowerCase() + 'Alerts'] ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="section-header">
            <div className="section-title">Recent Alerts (live)</div>
          </div>
          {recentAlerts.length === 0 ? (
            <div className="empty">No recent alerts</div>
          ) : (
            <table>
              <thead><tr><th>Source IP</th><th>Type</th><th>Severity</th><th>Score</th></tr></thead>
              <tbody>
                {recentAlerts.map(a => (
                  <tr key={a.id}>
                    <td>{a.sourceIp}</td>
                    <td>{a.alertType}</td>
                    <td><span className={`badge-severity ${a.severity}`}>{a.severity}</span></td>
                    <td>{a.anomalyScore?.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
