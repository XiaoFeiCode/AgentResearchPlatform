import client from './client'

export function fetchAppStatus() {
  return client.get('/api/status')
}
