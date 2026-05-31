import client from './client'

export function fetchConfig() {
  return client.get('/api/config')
}

export function saveConfig(updates: Record<string, any>) {
  return client.post('/api/config', updates)
}
