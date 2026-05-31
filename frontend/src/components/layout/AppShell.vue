<template>
  <el-container class="ops-shell">
    <el-header height="auto" class="ops-top">
      <TheHeader @refresh="$emit('refresh')" />
      <SearchSection />
    </el-header>

    <el-container class="ops-body">
      <el-main class="workspace">
        <slot name="content" />
      </el-main>

      <el-aside width="420px" class="agent-rail">
        <AppSwitcher />
        <ConsoleOutput />
      </el-aside>
    </el-container>

    <StatusBar />
  </el-container>
</template>

<script setup lang="ts">
import TheHeader from './TheHeader.vue'
import SearchSection from './SearchSection.vue'
import AppSwitcher from './AppSwitcher.vue'
import ConsoleOutput from '../console/ConsoleOutput.vue'
import StatusBar from './StatusBar.vue'

defineEmits<{
  refresh: []
}>()
</script>

<style scoped>
.ops-shell {
  height: 100vh;
  min-width: 1080px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #1f2933;
  background:
    linear-gradient(180deg, rgba(245, 247, 250, 0.96), rgba(238, 242, 247, 0.96)),
    radial-gradient(circle at 12% 20%, rgba(60, 179, 113, 0.08), transparent 28%),
    radial-gradient(circle at 88% 8%, rgba(238, 111, 87, 0.08), transparent 24%);
}

.ops-top {
  flex-shrink: 0;
  padding: 0;
  background: #ffffff;
  border-bottom: 1px solid #d8dee9;
  box-shadow: 0 2px 14px rgba(34, 42, 53, 0.06);
  z-index: 3;
}

.ops-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 16px;
  gap: 16px;
}

.workspace {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  padding: 0;
  background: #ffffff;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  box-shadow: 0 12px 30px rgba(28, 39, 49, 0.08);
}

.agent-rail {
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #18212b;
  border: 1px solid #273544;
  border-radius: 8px;
  box-shadow: 0 12px 30px rgba(28, 39, 49, 0.12);
}

@media (max-width: 1180px) {
  .ops-shell {
    min-width: 0;
  }

  .ops-body {
    flex-direction: column;
  }

  .agent-rail {
    width: auto !important;
    height: 38%;
  }
}
</style>
