<template>
  <div class="console-wrap">
    <div class="console-toolbar">
      <span>运行日志</span>
      <el-button
        v-if="lines.length > 0"
        size="small"
        text
        @click="clearLog"
      >
        清空
      </el-button>
    </div>

    <div class="console-output" ref="consoleRef">
      <div v-if="lines.length === 0" class="console-empty">
        暂无日志输出
      </div>
      <div
        v-for="(line, idx) in lines"
        :key="idx"
        class="console-line"
      >
        <span class="line-no">{{ idx + 1 }}</span>
        <span class="line-text">{{ line }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, nextTick, ref } from 'vue'
import { useAppsStore } from '@/stores/apps'

const appsStore = useAppsStore()
const consoleRef = ref<HTMLElement | null>(null)

const lines = computed(() => {
  const app = appsStore.activeApp
  return appsStore.logBuffers[app] || []
})

function clearLog() {
  appsStore.clearLogBuffer(appsStore.activeApp)
}

watch(
  () => lines.value.length,
  async () => {
    await nextTick()
    if (consoleRef.value) {
      consoleRef.value.scrollTop = consoleRef.value.scrollHeight
    }
  },
)
</script>

<style scoped>
.console-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #121922;
}

.console-toolbar {
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 0 12px;
  color: #d9e2ec;
  font-size: 13px;
  font-weight: 700;
  border-bottom: 1px solid #273544;
}

.console-output {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 0 14px;
  color: #c8d6e5;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12px;
  background: #0f151d;
}

.console-empty {
  padding: 28px 16px;
  color: #697586;
  text-align: center;
}

.console-line {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 10px;
  min-height: 20px;
  padding: 2px 12px;
  line-height: 1.55;
}

.console-line:hover {
  background: rgba(255, 255, 255, 0.04);
}

.line-no {
  color: #546170;
  text-align: right;
  user-select: none;
}

.line-text {
  min-width: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
