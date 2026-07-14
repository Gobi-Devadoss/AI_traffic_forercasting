import React, { useState } from 'react'
import * as api from '../api/endpoints'
import RouteSelector from '../components/RouteSelector'

export default function Optimization() {
  const [route, setRoute] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleFetch = async () => {
    if (!route) return
    setLoading(true)
    setError('')
    try {
      const res = await api.getRecommendations(route)
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not generate recommendations for this route.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="page-title">Mobility Optimization Engine</div>
      <div className="page-subtitle">Best travel windows, congestion-reduction tips, and route load-balancing</div>
      <div style={{ height: 20 }} />

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="form-row" style={{ marginBottom: 0 }}>
          <div className="form-group">
            <label>Route</label>
            <RouteSelector value={route} onChange={setRoute} />
          </div>
          <button className="btn" onClick={handleFetch} disabled={loading || !route}>
            {loading ? 'Analyzing…' : 'Get Recommendations'}
          </button>
        </div>
      </div>

      {error && <div className="auth-error" style={{ marginBottom: 20 }}>{error}</div>}

      {result && (
        <div className="grid grid-2">
          <div className="card">
            <div className="section-title">AI Recommendations</div>
            <ul className="recommendation-list">
              {result.recommendations.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>

          <div className="card">
            <div className="section-title">Best Travel Windows</div>
            <table>
              <thead><tr><th>Hour Window</th><th>Avg Volume</th><th>Est. Time Savings</th></tr></thead>
              <tbody>
                {result.best_travel_windows.map((w) => (
                  <tr key={w.hour}>
                    <td>{w.label}</td>
                    <td>{w.avg_volume}</td>
                    <td>{w.estimated_time_savings_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card" style={{ gridColumn: '1 / -1' }}>
            <div className="section-title">Route Load-Balancing Suggestions</div>
            <ul className="recommendation-list">
              {result.load_balancing.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        </div>
      )}

      {!result && !loading && !error && (
        <div className="empty-state">Select a route and click "Get Recommendations" to see optimization insights.</div>
      )}
    </div>
  )
}
