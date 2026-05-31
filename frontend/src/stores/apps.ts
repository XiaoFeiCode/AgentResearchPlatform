import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'

export interface AppInfo {
  status: 'running' | 'stopped' | 'starting' | 'error'
  port: number
  outputLines: number
}

export const useAppsStore = defineStore('apps', () => {
  const apps = reactive<Record<string, AppInfo>>({
    insight: { status: 'stopped', port: 0, outputLines: 0 },
    media: { status: 'stopped', port: 0, outputLines: 0 },
    query: { status: 'stopped', port: 0, outputLines: 0 },
    forum: { status: 'stopped', port: 0, outputLines: 0 },
    report: { status: 'stopped', port: 0, outputLines: 0 },
  })

  const logBuffers = reactive<Record<string, string[]>>({
    insight: [],
    media: [],
    query: [],
    forum: [],
    report: [],
  })

  const MAX_LOG_LINES = 5000
  const activeApp = ref<string>('insight')

  function updateAppStatus(name: string, status: 'running' | 'stopped' | 'starting' | 'error') {
    if (apps[name]) {
      apps[name].status = status
    }
  }

  function appendConsoleLine(appName: string, line: string) {
    if (logBuffers[appName]) {
      logBuffers[appName].push(line)
      if (logBuffers[appName].length > MAX_LOG_LINES) {
        logBuffers[appName] = logBuffers[appName].slice(-MAX_LOG_LINES)
      }
      apps[appName].outputLines = logBuffers[appName].length
    }
  }

  function clearLogBuffer(appName: string) {
    if (logBuffers[appName]) {
      logBuffers[appName] = []
      apps[appName].outputLines = 0
    }
  }

  function setActiveApp(appName: string) {
    activeApp.value = appName
  }

  return {
    apps, logBuffers, activeApp,
    updateAppStatus, appendConsoleLine, clearLogBuffer, setActiveApp,
  }
})
