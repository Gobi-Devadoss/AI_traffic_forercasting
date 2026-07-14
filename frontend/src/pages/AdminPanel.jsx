import React, { useEffect, useState } from 'react'
import * as api from '../api/endpoints'
import { useAuth } from '../context/AuthContext'

export default function AdminPanel() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    Promise.all([api.adminListUsers(), api.adminStats()])
      .then(([u, s]) => {
        setUsers(u.data)
        setStats(s.data)
      })
      .catch((err) => setError(err.response?.data?.detail || 'Could not load admin data.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const toggleRole = async (u) => {
    const newRole = u.role === 'admin' ? 'user' : 'admin'
    try {
      await api.adminUpdateRole(u.id, newRole)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not update role.')
    }
  }

  const toggleStatus = async (u) => {
    try {
      await api.adminUpdateStatus(u.id, !u.is_active)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not update status.')
    }
  }

  const removeUser = async (u) => {
    if (!window.confirm(`Delete user "${u.username}"? This cannot be undone.`)) return
    try {
      await api.adminDeleteUser(u.id)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Could not delete user.')
    }
  }

  return (
    <div>
      <div className="page-title">Admin Panel</div>
      <div className="page-subtitle">User management and platform-wide statistics</div>
      <div style={{ height: 20 }} />

      {error && <div className="auth-error" style={{ marginBottom: 20 }}>{error}</div>}

      {stats && (
        <div className="grid grid-4" style={{ marginBottom: 20 }}>
          <div className="card"><div className="stat-label">Total Users</div><div className="stat-value">{stats.total_users}</div></div>
          <div className="card"><div className="stat-label">Traffic Records</div><div className="stat-value">{stats.total_traffic_records}</div></div>
          <div className="card"><div className="stat-label">Forecasts Generated</div><div className="stat-value">{stats.total_forecasts_generated}</div></div>
          <div className="card"><div className="stat-label">Simulations Run</div><div className="stat-value">{stats.total_simulations}</div></div>
        </div>
      )}

      <div className="card">
        <div className="section-title">Users</div>
        {loading ? (
          <div className="loading-state">Loading users…</div>
        ) : (
          <table>
            <thead>
              <tr><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th>Joined</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}{u.id === currentUser.id && ' (you)'}</td>
                  <td>{u.email}</td>
                  <td><span className={`badge ${u.role === 'admin' ? 'high' : 'low'}`}>{u.role}</span></td>
                  <td><span className={`badge ${u.is_active ? 'low' : 'medium'}`}>{u.is_active ? 'active' : 'disabled'}</span></td>
                  <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  <td style={{ display: 'flex', gap: 6 }}>
                    <button className="btn secondary" onClick={() => toggleRole(u)} disabled={u.id === currentUser.id}>
                      Make {u.role === 'admin' ? 'User' : 'Admin'}
                    </button>
                    <button className="btn secondary" onClick={() => toggleStatus(u)} disabled={u.id === currentUser.id}>
                      {u.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button className="btn danger" onClick={() => removeUser(u)} disabled={u.id === currentUser.id}>
                      Delete
                    </button>
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
