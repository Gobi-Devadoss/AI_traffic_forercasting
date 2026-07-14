import React, { useState } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis, Cell,
} from 'recharts'
import * as api from '../api/endpoints'
import RouteSelector from '../components/RouteSelector'

const TYPE_COLORS = {
  spike: '#f87171',
  drop: '#fbbf24',
  sensor_error: '#a78bfa',
  event_surge: '#f87171',
}

export default function Anomalies() {
  const [route, setRoute] = useState(null)
  const [anomalies, setAnomalies] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleDetect = async () => {
    if (!route) return
    setLoading(true)
    setError('')
    try {
      const res = await api.detectAnomalies(route)
      setAnomalies(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not run anomaly detection for this route.')
      setAnomalies(null)
    } finally {
      setLoading(false)
    }
  }

  const chartData = (anomalies || []).map((a) => ({
    x: new Date(a.timestamp).getTime(),
    y: a.observed_value,
    z: a.score * 30,
    type: a.anomaly_type,
    label: new Date(a.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit' }),
  }))

  return (
    <div>
      <div className="page-title">Traffic Anomaly Detection</div>
      <div className="page-subtitle">Z-score + Isolation Forest detection over historical route data</div>
      <div style={{ height: 20 }} />

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="form-row" style={{ marginBottom: 0 }}>
          <div className="form-group">
            <label>Route</label>
            <RouteSelector value={route} onChange={setRoute} />
          </div>
          <button className="btn" onClick={handleDetect} disabled={loading || !route}>
            {loading ? 'Scanning…' : 'Run Detection'}
          </button>
        </div>
      </div>

      {error && <div className="auth-error" style={{ marginBottom: 20 }}>{error}</div>}

      {anomalies && (
        <>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="section-title">Anomalies Over Time (bubble size = anomaly score)</div>
            {chartData.length === 0 ? (
              <div className="empty-state">No anomalies detected for this route — traffic looks consistent with historical patterns.</div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#24324d" />
                  <XAxis
                    dataKey="x"
                    type="number"
                    domain={['dataMin', 'dataMax']}
                    tickFormatter={(v) => new Date(v).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                    tick={{ fontSize: 10, fill: '#8fa0bd' }}
                  />
                  <YAxis dataKey="y" name="Vehicle count" tick={{ fontSize: 10, fill: '#8fa0bd' }} />
                  <ZAxis dataKey="z" range={[60, 400]} />
                  <Tooltip
                    contentStyle={{ background: '#16223a', border: '1px solid #24324d' }}
                    formatter={(value, name) => [value, name]}
                    labelFormatter={() => ''}
                  />
                  <Scatter data={chartData} fill="#f87171">
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={TYPE_COLORS[entry.type] || '#f87171'} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="card">
            <div className="section-title">Detected Anomalies ({anomalies.length})</div>
            {anomalies.length === 0 ? (
              <div className="empty-state">Nothing to show yet.</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Timestamp</th><th>Type</th><th>Observed</th><th>Expected</th><th>Score</th><th>Method</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map((a) => (
                    <tr key={a.id}>
                      <td>{new Date(a.timestamp).toLocaleString()}</td>
                      <td style={{ color: TYPE_COLORS[a.anomaly_type] || '#e6ecf5', textTransform: 'capitalize' }}>
                        {a.anomaly_type.replace('_', ' ')}
                      </td>
                      <td>{a.observed_value}</td>
                      <td>{a.expected_value ?? '—'}</td>
                      <td>{a.score}</td>
                      <td>{a.method === 'isolation_forest' ? 'Isolation Forest' : 'Z-score'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {!anomalies && !loading && !error && (
        <div className="empty-state">Select a route and click "Run Detection" to scan for anomalies.</div>
      )}
    </div>
  )
}
