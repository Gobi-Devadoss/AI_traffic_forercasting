import React, { useEffect, useState } from 'react'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar,
} from 'recharts'
import * as api from '../api/endpoints'
import RouteSelector from '../components/RouteSelector'

const HORIZONS = [
  { value: '24h', label: 'Next 24 Hours' },
  { value: '7d', label: 'Next 7 Days' },
]
const MODELS = [
  { value: 'auto', label: 'Auto (best of 3)' },
  { value: 'moving_average', label: 'Moving Average' },
  { value: 'linear', label: 'Linear Regression' },
  { value: 'seasonal', label: 'Seasonal Naive' },
]

export default function Forecast() {
  const [route, setRoute] = useState(null)
  const [horizon, setHorizon] = useState('24h')
  const [modelType, setModelType] = useState('auto')
  const [forecast, setForecast] = useState(null)
  const [peakHours, setPeakHours] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    if (!route) return
    setLoading(true)
    setError('')
    try {
      const [fRes, pRes] = await Promise.all([
        api.generateForecast(route, horizon, modelType),
        api.getPeakHours(route),
      ])
      setForecast(fRes.data)
      setPeakHours(pRes.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not generate a forecast for this route.')
      setForecast(null)
    } finally {
      setLoading(false)
    }
  }

  const chartData = (forecast?.points || []).map((p) => ({
    time: new Date(p.timestamp).toLocaleString([], {
      month: 'short', day: 'numeric', hour: '2-digit', minute: horizon === '24h' ? '2-digit' : undefined,
    }),
    predicted_volume: p.predicted_volume,
    lower_bound: p.lower_bound,
    range: Math.max(0, p.upper_bound - p.lower_bound),
    congestion_level: Math.round(p.congestion_level * 100),
  }))

  return (
    <div>
      <div className="page-title">Traffic Volume Forecasting</div>
      <div className="page-subtitle">Hourly / daily predictions with confidence bounds and auto model selection</div>
      <div style={{ height: 20 }} />

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="form-row" style={{ marginBottom: 0 }}>
          <div className="form-group">
            <label>Route</label>
            <RouteSelector value={route} onChange={setRoute} />
          </div>
          <div className="form-group">
            <label>Horizon</label>
            <select value={horizon} onChange={(e) => setHorizon(e.target.value)}>
              {HORIZONS.map((h) => <option key={h.value} value={h.value}>{h.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Model</label>
            <select value={modelType} onChange={(e) => setModelType(e.target.value)}>
              {MODELS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>
          <button className="btn" onClick={handleGenerate} disabled={loading || !route}>
            {loading ? 'Generating…' : 'Generate Forecast'}
          </button>
        </div>
      </div>

      {error && <div className="auth-error" style={{ marginBottom: 20 }}>{error}</div>}

      {forecast && (
        <>
          <div className="grid grid-4" style={{ marginBottom: 20 }}>
            <div className="card">
              <div className="stat-label">Model Used</div>
              <div className="stat-value" style={{ fontSize: 18 }}>{forecast.model_used}</div>
            </div>
            <div className="card">
              <div className="stat-label">Forecast Accuracy (MAE)</div>
              <div className="stat-value" style={{ fontSize: 18 }}>{forecast.accuracy_mae} vehicles/hr</div>
            </div>
            <div className="card">
              <div className="stat-label">Forecast Accuracy (MAPE)</div>
              <div className="stat-value" style={{ fontSize: 18 }}>{forecast.accuracy_mape}%</div>
            </div>
            <div className="card">
              <div className="stat-label">Alerts Generated</div>
              <div className="stat-value" style={{ fontSize: 18 }}>{forecast.alerts.length}</div>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="section-title">Predicted Traffic Volume ({horizon === '24h' ? 'Next 24 Hours' : 'Next 7 Days'})</div>
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#24324d" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#8fa0bd' }} interval={Math.ceil(chartData.length / 10)} />
                <YAxis tick={{ fontSize: 10, fill: '#8fa0bd' }} />
                <Tooltip contentStyle={{ background: '#16223a', border: '1px solid #24324d' }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Area dataKey="lower_bound" stackId="band" stroke="none" fill="transparent" name="" legendType="none" />
                <Area dataKey="range" stackId="band" stroke="none" fill="#4f8cff22" name="Confidence band" />
                <Line dataKey="predicted_volume" stroke="#4f8cff" strokeWidth={2} dot={false} name="Predicted volume" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-2">
            <div className="card">
              <div className="section-title">Congestion Level (%)</div>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#24324d" />
                  <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#8fa0bd' }} interval={Math.ceil(chartData.length / 8)} />
                  <YAxis tick={{ fontSize: 10, fill: '#8fa0bd' }} />
                  <Tooltip contentStyle={{ background: '#16223a', border: '1px solid #24324d' }} />
                  <Bar dataKey="congestion_level" fill="#22d3ee" radius={[4, 4, 0, 0]} name="Congestion %" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="section-title">Congestion & Risk Alerts</div>
              {forecast.alerts.length === 0 ? (
                <div className="empty-state">No congestion or spike alerts for this forecast window.</div>
              ) : (
                forecast.alerts.map((msg, i) => (
                  <div key={i} className="alert-item medium">{msg}</div>
                ))
              )}
            </div>
          </div>

          {peakHours && (
            <div className="card" style={{ marginTop: 20 }}>
              <div className="section-title">Historical Peak Hours</div>
              <table>
                <thead>
                  <tr><th>Hour Window</th><th>Avg Volume</th><th>Volatility</th></tr>
                </thead>
                <tbody>
                  {peakHours.peak_hours.map((p) => (
                    <tr key={p.hour}>
                      <td>{p.label}</td>
                      <td>{p.avg_volume}</td>
                      <td>{p.volatility}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {!forecast && !loading && !error && (
        <div className="empty-state">Select a route and click "Generate Forecast" to get started.</div>
      )}
    </div>
  )
}
