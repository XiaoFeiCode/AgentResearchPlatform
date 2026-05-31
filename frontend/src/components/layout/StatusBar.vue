<template>
  <div class="status-bar">
    <div class="status-left">
      <span class="status-pill" :class="systemStore.connectionStatus">
        {{ systemStore.connectionStatus === 'connected' ? 'SSE 已连接' : 'SSE 已断开' }}
      </span>
      <span
        v-if="reportStore.currentTask?.status === 'running'"
        class="status-pill report"
      >
        {{ reportStreamText }}
      </span>
    </div>
    <div class="status-right">
      <span>{{ currentTime }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import { useReportStore } from '@/stores/report'

const systemStore = useSystemStore()
const reportStore = useReportStore()
const currentTime = ref('')
let clockTimer: ReturnType<typeof setInterval> | null = null

const reportStreamText = computed(() => {
  const pct = reportStore.currentTask?.progress || 0
  switch (reportStore.streamStatus) {
    case 'connected': return `报告流 ${pct}%`
    case 'reconnecting': return '报告流重连中'
    case 'connecting': return '报告流连接中'
    case 'error': return '报告流异常'
    default: return '报告流待命'
  }
})

function updateClock() {
  currentTime.value = new Date().toLocaleTimeString()
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<style scoped>
.status-bar {
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 0 16px;
  color: #5f6b7a;
  font-size: 12px;
  background: #ffffff;
  border-top: 1px solid #d8dee9;
}

.status-left,
.status-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 9px;
  color: #a64232;
  font-weight: 700;
  border-radius: 11px;
  background: #fff0ed;
}

.status-pill.connected,
.status-pill.report {
  color: #2b5f48;
  background: #edf9f1;
}
</style>
