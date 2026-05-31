import client from './client'

export function fetchSystemStatus() {
  return client.get('/api/system/status')
}
