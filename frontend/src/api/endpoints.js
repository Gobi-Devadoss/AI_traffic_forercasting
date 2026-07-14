import client from './client'

// ---- Auth ----
export const login = (username, password) => {
  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)
  return client.post('/api/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export const register = (payload) => client.post('/api/auth/register', payload)
export const getMe = () => client.get('/api/auth/me')

// ---- Traffic data ----
export const uploadTrafficCsv = (file) => {
  const form = new FormData()
  form.append('file', file)
  return client.post('/api/traffic/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export const listRoutes = () => client.get('/api/traffic/routes')
export const getDashboardSummary = () => client.get('/api/traffic/summary')
export const listRecords = (params) => client.get('/api/traffic/records', { params })

// ---- Forecasting ----
export const generateForecast = (route_id, horizon = '24h', model_type = 'auto') =>
  client.get('/api/forecast/generate', { params: { route_id, horizon, model_type } })
export const getPeakHours = (route_id) =>
  client.get('/api/forecast/peak-hours', { params: { route_id } })
export const getForecastHistory = (route_id) =>
  client.get('/api/forecast/history', { params: { route_id } })

// ---- Anomaly detection ----
export const detectAnomalies = (route_id) =>
  client.get('/api/anomaly/detect', { params: { route_id } })
export const listAnomalies = (route_id) =>
  client.get('/api/anomaly/list', { params: route_id ? { route_id } : {} })

// ---- Optimization ----
export const getRecommendations = (route_id, compare_routes = []) =>
  client.get('/api/optimization/recommendations', {
    params: { route_id, compare_routes },
    paramsSerializer: { indexes: null },
  })

// ---- Simulation ----
export const listScenarios = () => client.get('/api/simulation/scenarios')
export const runSimulation = (payload) => client.post('/api/simulation/run', payload)
export const getSimulationHistory = (route_id) =>
  client.get('/api/simulation/history', { params: route_id ? { route_id } : {} })

// ---- Alerts ----
export const listAlerts = (params) => client.get('/api/alerts', { params })

// ---- Admin ----
export const adminListUsers = () => client.get('/api/admin/users')
export const adminUpdateRole = (userId, role) =>
  client.put(`/api/admin/users/${userId}/role`, { role })
export const adminUpdateStatus = (userId, is_active) =>
  client.put(`/api/admin/users/${userId}/status`, { is_active })
export const adminDeleteUser = (userId) => client.delete(`/api/admin/users/${userId}`)
export const adminStats = () => client.get('/api/admin/stats')
export const adminSeedDemoData = (days = 30) =>
  client.post('/api/admin/seed-demo-data', null, { params: { days } })
