<template>
  <div class="agent-switcher">
    <div class="rail-title">
      <span>Agent 运行队列</span>
      <small>{{ activeLabel }}</small>
    </div>

    <div class="agent-list">
      <button
        v-for="app in apps"
        :key="app.name"
        class="agent-item"
        :class="{ active: appsStore.activeApp === app.name, locked: app.locked }"
        type="button"
        @click="handleTabClick(app)"
      >
        <span class="agent-meta">
          <span class="agent-icon" :class="app.name">{{ app.short }}</span>
          <span class="agent-copy">
            <strong>{{ app.label }}</strong>
            <em>{{ app.role }}</em>
          </span>
        </span>
        <span class="status-dot" :class="appsStore.apps[app.name]?.status || 'stopped'" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppsStore } from '@/stores/apps'
import { useReportStore } from '@/stores/report'

const appsStore = useAppsStore()
const reportStore = useReportStore()

const apps = computed(() => [
  { name: 'insight', label: 'Insight', role: '私域数据', short: 'I', locked: false },
  { name: 'media', label: 'Media', role: '媒体传播', short: 'M', locked: false },
  { name: 'query', label: 'Query', role: '权威核查', short: 'Q', locked: false },
  { name: 'forum', label: 'Forum', role: '协作讨论', short: 'F', locked: false },
  { name: 'report', label: 'Report', role: '报告生成', short: 'R', locked: !reportStore.enginesReady },
])

const activeLabel = computed(() => apps.value.find((app) => app.name === appsStore.activeApp)?.label || 'Insight')

function handleTabClick(app: { name: string; locked: boolean }) {
  if (app.locked) {
    reportStore.fetchStatus()
    return
  }
  appsStore.setActiveApp(app.name)
}
</script>

<style scoped>
.agent-switcher {
  flex-shrink: 0;
  padding: 14px;
  border-bottom: 1px solid #273544;
  background: #18212b;
}

.rail-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
  color: #f2f6fb;
}

.rail-title span {
  font-size: 15px;
  font-weight: 800;
}

.rail-title small {
  color: #8fa1b3;
  font-size: 12px;
}

.agent-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.agent-item {
  min-width: 0;
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  color: #b7c4d2;
  text-align: left;
  cursor: pointer;
  border: 1px solid #2d3b4a;
  border-radius: 8px;
  background: #202b37;
  transition: border-color 0.16s, background 0.16s, transform 0.16s;
}

.agent-item:hover {
  border-color: #4f6b85;
  background: #243242;
}

.agent-item.active {
  color: #ffffff;
  border-color: #7cc99a;
  background: #233a34;
}

.agent-item.locked {
  opacity: 0.45;
  cursor: not-allowed;
}

.agent-meta {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-icon {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  color: #17212b;
  font-weight: 900;
  border-radius: 8px;
  background: #b9dfca;
}

.agent-icon.media { background: #ffd6a5; }
.agent-icon.query { background: #b8d8ff; }
.agent-icon.forum { background: #ffb7a8; }
.agent-icon.report { background: #d8c7ff; }

.agent-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-copy strong,
.agent-copy em {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-copy strong {
  font-size: 13px;
  line-height: 1.1;
}

.agent-copy em {
  color: #8fa1b3;
  font-size: 11px;
  font-style: normal;
}

.status-dot {
  width: 9px;
  height: 9px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #778492;
}

.status-dot.running { background: #26a269; box-shadow: 0 0 0 4px rgba(38, 162, 105, 0.14); }
.status-dot.starting { background: #d99a26; box-shadow: 0 0 0 4px rgba(217, 154, 38, 0.14); }
.status-dot.error,
.status-dot.stopped { background: #e26450; }
</style>
