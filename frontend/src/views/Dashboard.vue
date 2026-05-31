<template>
  <AppShell @refresh="handleRefresh">
    <template #content>
      <KeepAlive>
        <component :is="activeComponent" :key="activeTab" />
      </KeepAlive>
    </template>
  </AppShell>
  <ConfigModal />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppsStore } from '@/stores/apps'
import { useSystemStore } from '@/stores/system'
import * as appsApi from '@/api/apps'
import AppShell from '@/components/layout/AppShell.vue'
import ConfigModal from '@/components/config/ConfigModal.vue'
import InsightTab from './InsightTab.vue'
import MediaTab from './MediaTab.vue'
import QueryTab from './QueryTab.vue'
import ForumTab from './ForumTab.vue'
import ReportTab from './ReportTab.vue'

const appsStore = useAppsStore()
const systemStore = useSystemStore()

const activeTab = computed(() => appsStore.activeApp)

const tabComponents: Record<string, any> = {
  insight: InsightTab,
  media: MediaTab,
  query: QueryTab,
  forum: ForumTab,
  report: ReportTab,
}

const activeComponent = computed(() => tabComponents[activeTab.value] || InsightTab)

async function handleRefresh() {
  try {
    await systemStore.fetchStatus()
    const res = await appsApi.fetchAppStatus()
    if (res.data) {
      for (const [name, info] of Object.entries(res.data)) {
        if (appsStore.apps[name]) {
          appsStore.updateAppStatus(name, (info as any).status)
        }
      }
    }
  } catch {
    // ignore
  }
}
</script>
