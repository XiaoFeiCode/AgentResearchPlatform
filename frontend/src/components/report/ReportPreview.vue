<template>
  <div class="report-preview">
    <iframe
      v-if="reportStore.currentTask?.report_file_ready"
      :src="previewUrl"
      class="preview-iframe"
      frameborder="0"
    />
    <div v-else class="preview-empty">
      <el-icon :size="48"><Document /></el-icon>
      <p>报告完成后将在此处显示预览</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { useReportStore } from '@/stores/report'

const reportStore = useReportStore()

const previewUrl = computed(() => {
  const taskId = reportStore.currentTask?.task_id
  return taskId ? `/api/report/result/${taskId}` : ''
})
</script>

<style scoped>
.report-preview {
  flex: 1;
  overflow: hidden;
}
.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  gap: 12px;
}
.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
