import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as systemApi from '@/api/system'

export const useSystemStore = defineStore('system', () => {
  const connectionStatus = ref<'connected' | 'disconnected'>('disconnected')

  async function fetchStatus() {
    try {
      return await systemApi.fetchSystemStatus()
    } catch {
      return null
    }
  }

  return {
    connectionStatus,
    fetchStatus,
  }
})
