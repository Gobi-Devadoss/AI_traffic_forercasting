import React from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/forecast', label: 'Forecasting' },
  { to: '/anomalies', label: 'Anomaly Detection' },
  { to: '/optimization', label: 'Mobility Optimization' },
  { to: '/simulation', label: 'Scenario Simulation' },
  { to: '/data-upload', label: 'Data Upload' },
]

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">Traffic<span>AI</span></div>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
          >
            {item.label}
          </NavLink>
        ))}
        {user?.role === 'admin' && (
          <NavLink to="/admin" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
            Admin Panel
          </NavLink>
        )}
      </aside>

      <main className="main-content">
        <div className="topbar">
          <div />
          <div className="user-chip">
            <span>{user?.username}</span>
            <span className="role-badge">{user?.role}</span>
            <button className="btn secondary" onClick={logout}>Logout</button>
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  )
}
