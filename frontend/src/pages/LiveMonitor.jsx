import { useEffect, useState, useCallback } from 'react'
import { trafficApi, monitoringApi } from '../api/api.js'

function fmt(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleTimeString()
}

export default function LiveMonitor() {
  const [flows, setFlows] = useState([])
  const [session, setSession] = useState(null)
  const [iface, setIface] = useState('eth0')
  const [loading, setLoading] = useState(true)
  const [actionBusy, setActionBusy] = useState(false)

  const loadFlows = useCallback(async () => {
    const data = await trafficApi.getRecent(5)
    setFlows(data)
  }, [])

  const loadSession = useCallback(async () => {
    try {
      const s = await monitoringApi.getActive()
      setSession(s)
    } catch {
      setSession(null)
    }
  }, [])

  useEffect(() => {
    Promise.all([loadFlows(), loadSession()]).finally(() => setLoading(false))
    const id = setInterval(() => { loadFlows(); loadSession() }, 5000)
    return () => clearInterval(id)
  }, [loadFlows, loadSession])

  async function startSession() {
    setActionBusy(true)
    try { setSession(await monitoringApi.start(iface)) } finally { setActionBusy(false) }
  }

  async function stopSession() {
    setActionBusy(true)
    try { await monitoringApi.stop(); setSession(null) } finally { setActionBusy(false) }
  }

  if (loading) return <div className="content"><div className="spinner" /></div>

  return (
    <div className="content">
      <div className="topbar" style={{ margin: '-24px -24px 24px', padding: '14px 24px' }}>
        <h1>Live Monitor</h1>
        <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>Auto-refresh every 5s</span>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="card-title">Session Control</div>
          <div className="form-row">
            <label>Interface</label>
            <input value={iface} onChange={e => setIface(e.target.value)} style={{ width: 120 }} disabled={!!session} />
            {session
              ? <button className="btn btn-danger" onClick={stopSession} disabled={actionBusy}>Stop</button>
              : <button className="btn btn-primary" onClick={startSession} disabled={actionBusy}>Start</button>
            }
          </div>
          {session && (
            <div className="monitor-card">
              <div className="monitor-row">
                <span>Status</span>
                <span><span className="status-dot active" />Active</span>
              </div>
              <div className="monitor-row">
                <span>Interface</span>
                <span>{session.networkInterface}</span>
              </div>
              <div className="monitor-row">
                <span>Started</span>
                <span>{fmt(session.startedAt)}</span>
              </div>
              <div className="monitor-row">
                <span>Flows analyzed</span>
                <span>{session.totalFlowsAnalyzed}</span>
              </div>
              <div className="monitor-row">
                <span>Anomalies</span>
                <span style={{ color: session.anomaliesDetected > 0 ? 'var(--danger)' : 'inherit' }}>
                  {session.anomaliesDetected}
                </span>
              </div>
            </div>
          )}
          {!session && <div className="empty" style={{ padding: 16 }}>No active session</div>}
        </div>

        <div className="card">
          <div className="card-title">Traffic Summary (last 5 min)</div>
          <div className="monitor-row" style={{ paddingTop: 8 }}>
            <span>Total flows</span><span>{flows.length}</span>
          </div>
          <div className="monitor-row">
            <span>Unique sources</span>
            <span>{new Set(flows.map(f => f.sourceIp)).size}</span>
          </div>
          <div className="monitor-row">
            <span>Protocols</span>
            <span>{[...new Set(flows.map(f => f.protocol))].join(', ') || '-'}</span>
          </div>
          <div className="monitor-row">
            <span>Total bytes</span>
            <span>{flows.reduce((a, f) => a + (f.byteCount || 0), 0).toLocaleString()}</span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="section-header">
          <div className="section-title">Recent Traffic Flows (last 5 min)</div>
          <button className="refresh-btn" onClick={loadFlows}>Refresh</button>
        </div>
        {flows.length === 0 ? (
          <div className="empty">No traffic captured yet</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Source IP</th>
                <th>Destination IP</th>
                <th>Port</th>
                <th>Protocol</th>
                <th>Packets</th>
                <th>Bytes</th>
                <th>Duration</th>
                <th>Conn/s</th>
              </tr>
            </thead>
            <tbody>
              {flows.map(f => (
                <tr key={f.id}>
                  <td>{fmt(f.timestamp)}</td>
                  <td>{f.sourceIp}</td>
                  <td>{f.destinationIp}</td>
                  <td>{f.destinationPort}</td>
                  <td>{f.protocol}</td>
                  <td>{f.packetCount}</td>
                  <td>{f.byteCount?.toLocaleString()}</td>
                  <td>{f.duration?.toFixed(2)}s</td>
                  <td>{f.connectionsPerSecond?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
