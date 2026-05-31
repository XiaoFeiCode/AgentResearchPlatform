import { ref, onUnmounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import { useAppsStore } from '@/stores/apps'
import { useSearchStore } from '@/stores/search'
import { useForumStore } from '@/stores/forum'

export function useSSE() {
  const systemStore = useSystemStore()
  const appsStore = useAppsStore()
  const searchStore = useSearchStore()
  const forumStore = useForumStore()

  const connected = ref(false)
  let eventSource: EventSource | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let retryDelay = 1000

  function connect() {
    if (eventSource) eventSource.close()

    eventSource = new EventSource('/api/events/stream')

    eventSource.addEventListener('connected', () => {
      connected.value = true
      systemStore.connectionStatus = 'connected'
      retryDelay = 1000
    })

    eventSource.addEventListener('error', () => {
      connected.value = false
      systemStore.connectionStatus = 'disconnected'
    })

    eventSource.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const eventType = msg.event
        const eventData = msg.data

        if (eventType === 'console_output') {
          const appName = eventData.app || eventData.app_name
          const line = eventData.line || eventData.output || eventData.message || ''
          if (appName && line) {
            appsStore.appendConsoleLine(appName, line)
          }
        } else if (eventType === 'engine_progress') {
          searchStore.handleEngineProgress(eventData)
          appsStore.appendConsoleLine(eventData.engine, `[${eventData.engine}] ${eventData.message || ''}`)
        } else if (eventType === 'engine_result') {
          searchStore.handleEngineResult(eventData)
          appsStore.appendConsoleLine(eventData.engine, `[${eventData.engine}] 研究完成`)
        } else if (eventType === 'engine_error') {
          searchStore.handleEngineError(eventData)
          appsStore.appendConsoleLine(eventData.engine, `[${eventData.engine}] 错误: ${eventData.error || '未知错误'}`)
        } else if (eventType === 'forum_message') {
          forumStore.handleForumMessage(eventData)
        }
      } catch {
        // skip malformed events
      }
    }

    eventSource.onerror = () => {
      connected.value = false
      systemStore.connectionStatus = 'disconnected'
      eventSource?.close()
      scheduleReconnect()
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => {
      retryDelay = Math.min(retryDelay * 2, 15000)
      connect()
    }, retryDelay)
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    connected.value = false
  }

  onUnmounted(() => disconnect())

  return { connected, connect, disconnect }
}
