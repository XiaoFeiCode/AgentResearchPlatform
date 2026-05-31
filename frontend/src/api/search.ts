import client from './client'

export function search(query: string) {
  return client.post('/api/search', { query })
}

export function fetchLatestResults() {
  return client.get('/api/search/latest')
}
