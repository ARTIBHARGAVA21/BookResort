import { useEffect, useState, useCallback, useRef } from 'react'
import { auditApi } from '../api.js'

const THREAT_LEVELS = ['LOW', 'MEDIUM', 'HIGH']

function levelClass(level) {
  return `threat threat-${String(level).toLowerCase()}`
}

function fmtTime(ts) {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts
  return d.toLocaleString()
}

export default function AuditLogs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Query filters
  const [threatLevel, setThreatLevel] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [limit, setLimit] = useState(50)

  // Live polling ("real-time" viewer)
  const [live, setLive] = useState(true)
  const timerRef = useRef(null)

  const loadLogs = useCallback(async () => {
    try {
      const params = { limit }
      if (threatLevel) params.threat_level = threatLevel
      if (endpoint) params.endpoint = endpoint
      const { data } = await auditApi.query(params)
      setLogs(data)
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }, [threatLevel, endpoint, limit])

  useEffect(() => {
    loadLogs()
  }, [loadLogs])

  useEffect(() => {
    if (live) {
      timerRef.current = setInterval(loadLogs, 5000)
    }
    return () => clearInterval(timerRef.current)
  }, [live, loadLogs])

  const resetFilters = () => {
    setThreatLevel('')
    setEndpoint('')
  }

  const counts = logs.reduce(
    (acc, l) => {
      acc[l.threat_level] = (acc[l.threat_level] || 0) + 1
      return acc
    },
    {}
  )

  return (
    <div className="dashboard">
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Security Audit Trail</h2>
            <p className="muted">
              Automated threat logging across every request. {live ? 'Live (refreshes every 5s)' : 'Paused'}
            </p>
          </div>
          <label className="live-toggle">
            <input
              type="checkbox"
              checked={live}
              onChange={(e) => setLive(e.target.checked)}
            />
            Live
          </label>
        </div>

        <div className="stats">
          {THREAT_LEVELS.map((lvl) => (
            <div key={lvl} className="stat-card">
              <span className={levelClass(lvl)}>{lvl}</span>
              <strong>{counts[lvl] || 0}</strong>
            </div>
          ))}
        </div>

        <div className="filters">
          <label>
            Threat level
            <select value={threatLevel} onChange={(e) => setThreatLevel(e.target.value)}>
              <option value="">All levels</option>
              {THREAT_LEVELS.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label>
            Endpoint contains
            <input
              type="text"
              placeholder="/api/bookings"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
            />
          </label>
          <label>
            Rows
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              {[25, 50, 100, 250].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <button className="btn btn-ghost" onClick={resetFilters}>
            Reset
          </button>
          <button className="btn btn-outline" onClick={loadLogs} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="loading">Loading audit trail…</div>
        ) : logs.length === 0 ? (
          <div className="empty">
            <p className="muted">No audit entries match the current filters.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Threat</th>
                  <th>Event</th>
                  <th>Endpoint</th>
                  <th>Method</th>
                  <th>IP</th>
                  <th>User</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id}>
                    <td className="nowrap">{fmtTime(l.timestamp)}</td>
                    <td>
                      <span className={levelClass(l.threat_level)}>{l.threat_level}</span>
                    </td>
                    <td className="nowrap">{l.event}</td>
                    <td className="mono">{l.endpoint}</td>
                    <td className="mono">{l.method}</td>
                    <td className="mono">{l.ip_address || '—'}</td>
                    <td className="mono">{l.user_email || 'anonymous'}</td>
                    <td className="details">{l.details || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
