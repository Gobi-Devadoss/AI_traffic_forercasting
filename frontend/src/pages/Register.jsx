import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await register(form)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-title">Create an account</div>
        <div className="auth-subtitle">The first registered user becomes an admin automatically</div>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="auth-field">
            <label>Username</label>
            <input style={{ width: '100%' }} value={form.username} onChange={update('username')} required minLength={3} />
          </div>
          <div className="auth-field">
            <label>Email</label>
            <input style={{ width: '100%' }} type="email" value={form.email} onChange={update('email')} required />
          </div>
          <div className="auth-field">
            <label>Password</label>
            <input style={{ width: '100%' }} type="password" value={form.password} onChange={update('password')} required minLength={6} />
          </div>
          <button className="btn" style={{ width: '100%' }} disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <div className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  )
}
