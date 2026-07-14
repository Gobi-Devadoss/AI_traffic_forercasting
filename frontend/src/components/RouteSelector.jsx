import React, { useEffect, useState } from 'react'
import * as api from '../api/endpoints'

export default function RouteSelector({ value, onChange }) {
  const [routes, setRoutes] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .listRoutes()
      .then((res) => {
        setRoutes(res.data)
        if (!value && res.data.length) onChange(res.data[0])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <select disabled><option>Loading routes…</option></select>

  if (!routes.length) {
    return (
      <select disabled>
        <option>No routes yet — upload or seed data</option>
      </select>
    )
  }

  return (
    <select value={value || ''} onChange={(e) => onChange(e.target.value)}>
      {routes.map((r) => (
        <option key={r} value={r}>{r}</option>
      ))}
    </select>
  )
}
