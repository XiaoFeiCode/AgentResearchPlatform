<template>
  <div class="topbar">
    <div class="brand">
      <div class="brand-copy">
        <h1>多源舆情智能分析系统</h1>
        <span>Multi-Agent Public Opinion Intelligence Platform</span>
      </div>
    </div>

    <div class="top-actions">
      <div class="runtime-chip">
        <span class="pulse" />
        <span>实时链路</span>
      </div>
      <el-tooltip content="刷新状态" placement="bottom">
        <el-button :icon="Refresh" circle @click="$emit('refresh')" />
      </el-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'

defineEmits<{
  refresh: []
}>()
</script>

<style scoped>
.topbar {
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  color: #17212b;
  background: linear-gradient(90deg, #ffffff 0%, #f8fafc 58%, #edf7f0 100%);
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.brand-copy {
  min-width: 0;
}

.brand-copy h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1.25;
}

.brand-copy span {
  display: block;
  margin-top: 2px;
  color: #697586;
  font-size: 12px;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.runtime-chip {
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  color: #2b5f48;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid #b9dfca;
  border-radius: 16px;
  background: #edf9f1;
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #26a269;
  box-shadow: 0 0 0 4px rgba(38, 162, 105, 0.16);
}
</style>
