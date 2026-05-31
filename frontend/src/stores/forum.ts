import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as forumApi from '@/api/forum'

export interface ForumMessage {
  id: string
  agent: string
  content: string
  timestamp: string
  type: 'user' | 'agent' | 'system' | 'host'
}

export const useForumStore = defineStore('forum', () => {
  const messages = ref<ForumMessage[]>([])
  const engineRunning = ref(false)
  const logPosition = ref(0)
  const MAX_MESSAGES = 2000

  async function startForumEngine() {
    try {
      const res = await forumApi.startForum()
      if (res.data.success) engineRunning.value = true
      return res.data
    } catch {
      return null
    }
  }

  async function stopForumEngine() {
    try {
      const res = await forumApi.stopForum()
      if (res.data.success) engineRunning.value = false
      return res.data
    } catch {
      return null
    }
  }

  async function fetchLog() {
    try {
      const res = await forumApi.fetchForumLog()
      if (res.data.success) {
        logPosition.value = res.data.total_lines || 0
        // Process parsed messages from backend
        const parsed = res.data.parsed_messages
        if (parsed && Array.isArray(parsed)) {
          const existingIds = new Set(messages.value.map(m => m.id))
          for (const raw of parsed) {
            const id = `${raw.timestamp}-${raw.sender}-${raw.content?.length || 0}`
            if (!existingIds.has(id)) {
              existingIds.add(id)
              messages.value.push({
                id,
                agent: raw.sender || raw.source || 'unknown',
                content: raw.content || '',
                timestamp: raw.timestamp || '',
                type: raw.type === 'host' ? 'host' : raw.type === 'agent' ? 'agent' : 'system',
              })
            }
          }
          // Trim overflow
          if (messages.value.length > MAX_MESSAGES) {
            messages.value = messages.value.slice(-MAX_MESSAGES)
          }
        }
      }
      return res.data
    } catch {
      return null
    }
  }

  function handleForumMessage(eventData: any) {
    const raw = eventData
    const id = `${raw.timestamp || Date.now()}-${raw.sender}-${(raw.content || '').length}`
    const existingIds = new Set(messages.value.map(m => m.id))
    if (!existingIds.has(id)) {
      messages.value.push({
        id,
        agent: raw.sender || raw.source || 'unknown',
        content: raw.content || '',
        timestamp: raw.timestamp || '',
        type: raw.type === 'host' ? 'host' : raw.type === 'agent' ? 'agent' : 'system',
      })
      if (messages.value.length > MAX_MESSAGES) {
        messages.value = messages.value.slice(-MAX_MESSAGES)
      }
    }
  }

  function appendMessage(msg: ForumMessage) {
    messages.value.push(msg)
    if (messages.value.length > MAX_MESSAGES) {
      messages.value = messages.value.slice(-MAX_MESSAGES)
    }
  }

  function clearMessages() {
    messages.value = []
    logPosition.value = 0
  }

  return {
    messages, engineRunning, logPosition,
    startForumEngine, stopForumEngine, fetchLog, handleForumMessage, appendMessage, clearMessages,
  }
})
