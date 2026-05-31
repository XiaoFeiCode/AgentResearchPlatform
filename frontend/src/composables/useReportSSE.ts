import { ref, onUnmounted } from 'vue'
import { useReportStore } from '@/stores/report'
import type { ReportTask } from '@/stores/report'

const REPORT_SSE_EVENTS = [
  'status', 'stage', 'chapter_status', 'chapter_chunk',
  'warning', 'error', 'debug', 'html_ready', 'completed',
  'log', 'cancelled', 'heartbeat',
] as const

export function useReportSSE() {
  const reportStore = useReportStore()
  const connected = ref(false)
  const lastEventId = ref<number>(0)
  let eventSource: EventSource | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let retryDelay = 3000

  function open(taskId: string) {
    close()

    // Append lastEventId header is handled via URL query or constructor option
    const url = `/api/report/stream/${taskId}`
    eventSource = new EventSource(url)

    REPORT_SSE_EVENTS.forEach((evt) => {
      eventSource!.addEventListener(evt, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data)
          const payload = data.payload || data
          let task: ReportTask | undefined

          if (payload.task) {
            task = payload.task
          }

          reportStore.handleSSEEvent(evt, payload, task)

          if (evt === 'completed' || evt === 'error' || evt === 'cancelled') {
            setTimeout(() => close(), 500)
          }

          connected.value = true
          lastEventId.value = data.id || lastEventId.value
        } catch {
          // skip unparseable events
        }
      })
    })

    eventSource.onopen = () => {
      connected.value = true
      retryDelay = 3000
      reportStore.streamStatus = 'connected'
    }

    eventSource.onerror = () => {
      connected.value = false
      reportStore.streamStatus = 'error'
      eventSource?.close()
      scheduleReconnect(taskId)
    }
  }

  function scheduleReconnect(taskId: string) {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reportStore.streamStatus = 'reconnecting'
    reconnectTimer = setTimeout(() => {
      retryDelay = Math.min(retryDelay * 2, 15000)
      open(taskId)
    }, retryDelay)
  }

  function close() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    connected.value = false
    reportStore.streamStatus = 'idle'
  }

  onUnmounted(() => close())

  return { connected, open, close }
}
