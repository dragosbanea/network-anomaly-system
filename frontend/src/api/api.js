import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

export const statsApi = {
  getDashboard: () => http.get('/statistics/dashboard').then(r => r.data),
  getRecent: (minutes = 60) => http.get(`/statistics/recent?minutes=${minutes}`).then(r => r.data),
}

export const alertsApi = {
  getAll: () => http.get('/alerts').then(r => r.data),
  getActive: () => http.get('/alerts/active').then(r => r.data),
  getRecent: (minutes = 60) => http.get(`/alerts/recent?minutes=${minutes}`).then(r => r.data),
  resolve: (id) => http.put(`/alerts/${id}/resolve`).then(r => r.data),
}

export const trafficApi = {
  getRecent: (minutes = 10) => http.get(`/traffic/recent?minutes=${minutes}`).then(r => r.data),
  getResults: () => http.get('/traffic/results').then(r => r.data),
  getAnomalies: () => http.get('/traffic/anomalies').then(r => r.data),
}

export const monitoringApi = {
  getActive: () => http.get('/monitoring/active').then(r => r.data),
  getSessions: () => http.get('/monitoring/sessions').then(r => r.data),
  start: (networkInterface) => http.post('/monitoring/start', { networkInterface }).then(r => r.data),
  stop: () => http.post('/monitoring/stop').then(r => r.data),
}
