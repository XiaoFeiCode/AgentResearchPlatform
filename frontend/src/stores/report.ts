import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as reportApi from '@/api/report'

export interface ReportTask {
  task_id: string
  query: string
  status: 'pending' | 'running' | 'completed' | 'error' | 'cancelled'
  progress: number
  error_message: string
  created_at: string
  updated_at: string
  has_result: boolean
  report_file_ready: boolean
  report_file_name: string
  report_file_path: string
  state_file_ready: boolean
  state_file_path: string
  ir_file_ready: boolean
  ir_file_path: string
  markdown_file_ready: boolean
  markdown_file_name: string
  markdown_file_path: string
}

export interface SSEEvent {
  id: number
  type: string
  task_id: string
  timestamp: string
  payload: Record<string, any>
}

export const useReportStore = defineStore('report', () => {
  const engineInitialized = ref(false)
  const enginesReady = ref(false)
  const missingFiles = ref<string[]>([])
  const currentTask = ref<ReportTask | null>(null)
  const streamEvents = ref<SSEEvent[]>([])
  const streamStatus = ref<'idle' | 'connecting' | 'connected' | 'reconnecting' | 'error'>('idle')
  const generateButtonDisabled = ref(false)
  const autoPreviewLoaded = ref(false)
  const MAX_STREAM_EVENTS = 2000

  async function fetchStatus() {
    try {
      const res = await reportApi.fetchReportStatus()
      if (res.data.success) {
        engineInitialized.value = res.data.initialized
        enginesReady.value = res.data.engines_ready
        missingFiles.value = res.data.missing_files || []
        currentTask.value = res.data.current_task
      }
      return res.data
    } catch {
      return null
    }
  }

  async function generateReport(query: string, customTemplate: string = '') {
    generateButtonDisabled.value = true
    try {
      const res = await reportApi.generateReport(query, customTemplate)
      if (res.data.success) {
        currentTask.value = res.data.task
        streamEvents.value = []
        autoPreviewLoaded.value = false
      }
      return res.data
    } finally {
      generateButtonDisabled.value = false
    }
  }

  async function cancelReport(taskId: string) {
    try {
      const res = await reportApi.cancelReport(taskId)
      return res.data
    } catch {
      return null
    }
  }

  async function fetchProgress(taskId: string) {
    try {
      const res = await reportApi.fetchReportProgress(taskId)
      if (res.data.success && res.data.task) {
        currentTask.value = res.data.task
      }
      return res.data
    } catch {
      return null
    }
  }

  async function fetchTemplates() {
    try {
      const res = await reportApi.fetchReportTemplates()
      return res.data
    } catch {
      return null
    }
  }

  async function fetchLog() {
    try {
      const res = await reportApi.fetchReportLog()
      return res.data
    } catch {
      return null
    }
  }

  function appendStreamEvent(event: SSEEvent) {
    streamEvents.value.push(event)
    if (streamEvents.value.length > MAX_STREAM_EVENTS) {
      streamEvents.value = streamEvents.value.slice(-MAX_STREAM_EVENTS)
    }
  }

  function handleSSEEvent(eventType: string, payload: Record<string, any>, task?: ReportTask) {
    appendStreamEvent({
      id: Date.now(),
      type: eventType,
      task_id: currentTask.value?.task_id || '',
      timestamp: new Date().toISOString(),
      payload,
    })

    switch (eventType) {
      case 'status':
        if (task) currentTask.value = task
        break
      case 'html_ready':
        if (task) currentTask.value = task
        else if (currentTask.value) currentTask.value.report_file_ready = true
        autoPreviewLoaded.value = true
        break
      case 'completed':
        if (task) currentTask.value = task
        autoPreviewLoaded.value = true
        break
      case 'error':
        if (task) currentTask.value = task
        break
      case 'cancelled':
        if (task) currentTask.value = task
        break
    }
  }

  return {
    engineInitialized, enginesReady, missingFiles,
    currentTask, streamEvents, streamStatus,
    generateButtonDisabled, autoPreviewLoaded,
    fetchStatus, generateReport, cancelReport, fetchProgress,
    fetchTemplates, fetchLog, appendStreamEvent, handleSSEEvent,
  }
})
