import React, { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import * as api from '../api/endpoints'
import RouteSelector from '../components/RouteSelector'

const SCENARIO_LABELS = {
  road_closure: 'Road Closure',
  rain: 'Heavy Rain / Weather',
  event: 'Festival / Event Surge',
  load_increase: 'Increased Vehicle Load',
}

export default function Simulation() {
  const [route, setRoute] = useState(null)
  const [scenarios, setScenarios] = useState([])
  const [scenarioType, setScenarioType] = useState('road_closure')
  const [intensity, setIntensity] = useState(1.0)
  const [duration, setDuration] = useState(3)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listScenarios().then((res) => {
      setScenarios(res.data)
      if (res.data.length) setScenarioType(res.data[0])
    }).catch(() => setScenarios(Object.keys(SCENARIO_LABELS)))
  }, [])

  const handleRun = async () => {
    if (!route) return
    setLoading(true)
    setError('')
    try {
      const res = await api.runSimulation({
        route_id: route,
        scenario_type: scenarioType,
        intensity: Number(intensity),
        duration_hours: Number(duration),
      })
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not run this simulation.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const chartData = result ? [
    { name: 'Baseline', volume: result.baseline_volume },
    { name: 'Projected', volume: result.projected_volume },
  ] : []

  return (
    <div>
      <div className="page-title">Scenario Simulation</div>
      <div className="page-subtitle">Model road closures, weather events, festivals, and load surges</div>
      <div style={{ height: 20 }} />

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="form-row">
          <div className="form-group">
            <label>Route</label>
            <RouteSelector value={route} onChange={setRoute} />
          </div>
          <div className="form-group">
            <label>Scenario</label>
            <select value={scenarioType} onChange={(e) => setScenarioType(e.target.value)}>
              {scenarios.map((s) => (
                <option key={s} value={s}>{SCENARIO_LABELS[s] || s}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Intensity (0–5x)</label>
            <input type="number" min="0" max="5" step="0.1" value={intensity} onChange={(e) => setIntensity(e.target.value)} style={{ width: 90 }} />
          </div>
          <div className="form-group">
            <label>Duration (hours)</label>
            <input type="number" min="1" max="48" value={duration} onChange={(e) => setDuration(e.target.value)} style={{ width: 90 }} />
          </div>
          <button className="btn" onClick={handleRun} disabled={loading || !route}>
            {loading ? 'Simulating…' : 'Run Simulation'}
          </button>
        </div>
      </div>

      {error && <div className="auth-error" style={{ marginBottom: 20 }}>{error}</div>}

      {result && (
        <>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="section-title">Scenario Summary</div>
            <p style={{ fontSize: 13, color: '#c9d4e6', lineHeight: 1.6 }}>{result.narrative}</p>
          </div>

          <div className="grid grid-4" style={{ marginBottom: 20 }}>
            <div className="card">
              <div className="stat-label">Congestion Impact</div>
              <div className="stat-value" style={{ fontSize: 20 }}>{result.congestion_impact_pct > 0 ? '+' : ''}{result.congestion_impact_pct}%</div>
            </div>
            <div className="card">
              <div className="stat-label">Extra Delay</div>
              <div className="stat-value" style={{ fontSize: 20 }}>{result.delay_minutes} min</div>
            </div>
            <div className="card">
              <div className="stat-label">Travel Time Change</div>
              <div className="stat-value" style={{ fontSize: 20 }}>{result.travel_time_change_pct > 0 ? '+' : ''}{result.travel_time_change_pct}%</div>
            </div>
            <div className="card">
              <div className="stat-label">Projected Volume</div>
              <div className="stat-value" style={{ fontSize: 20 }}>{result.projected_volume}/hr</div>
            </div>
          </div>

          <div className="card">
            <div className="section-title">Baseline vs Projected Volume</div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#24324d" />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#8fa0bd' }} />
                <YAxis tick={{ fontSize: 10, fill: '#8fa0bd' }} />
                <Tooltip contentStyle={{ background: '#16223a', border: '1px solid #24324d' }} />
                <Legend />
                <Bar dataKey="volume" fill="#4f8cff" radius={[4, 4, 0, 0]} name="Vehicles/hr" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {!result && !loading && !error && (
        <div className="empty-state">Configure a scenario and click "Run Simulation" to see the projected impact.</div>
      )}
    </div>
  )
}
