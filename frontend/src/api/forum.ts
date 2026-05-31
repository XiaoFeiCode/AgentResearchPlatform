import client from './client'

export function startForum() {
  return client.get('/api/forum/start')
}

export function stopForum() {
  return client.get('/api/forum/stop')
}

export function fetchForumLog() {
  return client.get('/api/forum/log')
}

