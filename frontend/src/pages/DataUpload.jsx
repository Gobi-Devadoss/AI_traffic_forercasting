import React, { useState } from 'react'
import * as api from '../api/endpoints'
import { useAuth } from '../context/AuthContext'

export default function DataUpload() {
  const { user } = useAuth()
  const [file, setFile] = useState(null)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [seedMsg, setSeedMsg] = useState('')

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    setError('')
    setSummary(null)
    try {
      const res = await api.uploadTrafficCsv(file)
      setSummary(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Check the file format and try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSeed = async () => {
    setSeeding(true)
    setSeedMsg('')
    try {
      const res = await api.adminSeedDemoData(30)
      setSeedMsg(`Seeded ${res.data.records_inserted} records across routes: ${res.data.routes.join(', ')}`)
    } catch (err) {
      setSeedMsg(err.response?.data?.detail || 'Could not seed demo data.')
    } finally {
      setSeeding(false)
    }
  }

  return (
    <div>
      <div className="page-title">Data Upload</div>
      <div className="page-subtitle">Upload historical traffic CSV data, or seed synthetic demo data</div>
      <div style={{ height: 20 }} />

      <div className="grid grid-2">
        <div className="card">
          <div className="section-title">Upload CSV</div>
          <p style={{ fontSize: 12, color: '#8fa0bd', marginTop: -6, marginBottom: 14 }}>
            Required columns: <code>timestamp, route_id, vehicle_count</code>. Optional:{' '}
            <code>location, avg_speed, congestion_level, weather</code>.
          </p>
          <form onSubmit={handleUpload}>
            <div className="auth-field">
              <input type="file" accept=".csv,.txt" onChange={(e) => setFile(e.target.files[0])} />
            </div>
            <button className="btn" disabled={!file || loading}>
              {loading ? 'Uploading…' : 'Upload File'}
            </button>
          </form>

          {error && <div className="auth-error" style={{ marginTop: 14 }}>{error}</div>}

          {summary && (
            <div style={{ marginTop: 16 }}>
              <div className="stat-label">Rows received: {summary.rows_received}</div>
              <div className="stat-label">Rows inserted: {summary.rows_inserted}</div>
              <div className="stat-label">Rows skipped: {summary.rows_skipped}</div>
              <div className="stat-label">Routes: {summary.routes.join(', ')}</div>
              {summary.warnings.length > 0 && (
                <ul style={{ marginTop: 10, fontSize: 12, color: '#fbbf24' }}>
                  {summary.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <div className="section-title">Seed Synthetic Demo Data</div>
          <p style={{ fontSize: 13, color: '#c9d4e6', lineHeight: 1.6 }}>
            No dataset handy? Generate 30 days of realistic multi-route synthetic traffic
            data (with commute peaks and injected anomalies) so you can immediately try
            forecasting, anomaly detection, optimization, and simulation.
          </p>
          {user?.role === 'admin' ? (
            <button className="btn secondary" onClick={handleSeed} disabled={seeding}>
              {seeding ? 'Seeding…' : 'Seed Demo Data'}
            </button>
          ) : (
            <div className="empty-state">Only admins can seed demo data. Ask an admin, or upload your own CSV above.</div>
          )}
          {seedMsg && <div style={{ marginTop: 14, fontSize: 13, color: '#8fa0bd' }}>{seedMsg}</div>}
        </div>
      </div>
    </div>
  )
}
