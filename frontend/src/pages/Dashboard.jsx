import React, { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import * as api from '../api/endpoints'
import SeverityBadge from '../components/SeverityBadge'
import RouteSelector from '../components/RouteSelector'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [route, setRoute] = useState(null)
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.getDashboardSummary(), api.listAlerts({ limit: 6 })])
      .then(([s, a]) => {
        setSummary(s.data)
        setAlerts(a.data)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!route) return
    api
      .listRecords({ route_id: route, limit: 72 })
      .then((res) => setRecords([...res.data].reverse()))
      .catch(() => setRecords([]))
  }, [route])

  const chartData = records.map((r) => ({
    time: new Date(r.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit' }),
    vehicle_count: r.vehicle_count,
  }))

  return (
    <div>
      <div className="page-title">Dashboard</div>
      <div className="page-subtitle">Platform overview and recent activity</div>
      <div style={{ height: 20 }} />

      {loading ? (
        <div className="loading-state">Loading summary…</div>
      ) : (
        <div className="grid grid-4" style={{ marginBottom: 22 }}>
          <div className="card">
            <div className="stat-label">Total Records</div>
            <div className="stat-value">{summary?.total_records ?? 0}</div>
          </div>
          <div className="card">
            <div className="stat-label">Tracked Routes</div>
            <div className="stat-value">{summary?.total_routes ?? 0}</div>
          </div>
          <div className="card">
            <div className="stat-label">Active Alerts</div>
            <div className="stat-value">{summary?.active_alerts ?? 0}</div>
          </div>
          <div className="card">
            <div className="stat-label">Anomalies Detected</div>
            <div className="stat-value">{summary?.recent_anomalies ?? 0}</div>
          </div>
        </div>
      )}

      <div className="grid grid-2">
        <div className="card">
          <div className="form-row" style={{ marginBottom: 8, justifyContent: 'space-between' }}>
            <div className="section-title" style={{ margin: 0 }}>Recent Traffic Volume</div>
            <RouteSelector value={route} onChange={setRoute} />
          </div>
          {chartData.length === 0 ? (
            <div className="empty-state">No data yet for this route.</div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#24324d" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#8fa0bd' }} interval={Math.ceil(chartData.length / 8)} />
                <YAxis tick={{ fontSize: 10, fill: '#8fa0bd' }} />
                <Tooltip contentStyle={{ background: '#16223a', border: '1px solid #24324d' }} />
                <Line type="monotone" dataKey="vehicle_count" stroke="#4f8cff" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <div className="section-title">Recent Alerts</div>
          {alerts.length === 0 ? (
            <div className="empty-state">No alerts yet. Generate a forecast to create some.</div>
          ) : (
            alerts.map((a) => (
              <div key={a.id} className={`alert-item ${a.severity}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <strong>{a.route_id}</strong>
                  <SeverityBadge severity={a.severity} />
                </div>
                {a.message}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
