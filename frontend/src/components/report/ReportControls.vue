<template>
  <div class="report-controls">
    <div class="controls-row">
      <el-input
        v-model="reportQuery"
        placeholder="输入报告主题..."
        size="default"
        style="flex:1"
      />
      <el-button
        type="primary"
        :disabled="reportStore.generateButtonDisabled"
        :loading="reportStore.currentTask?.status === 'running'"
        @click="handleGenerate"
      >
        生成报告
      </el-button>
    </div>

    <div v-if="task" class="task-progress">
      <div class="task-info">
        <el-tag :type="statusTagType" size="small">{{ task.status }}</el-tag>
        <span class="task-id">任务: {{ task.task_id }}</span>
      </div>
      <el-progress
        :percentage="task.progress"
        :status="task.status === 'error' ? 'exception' : undefined"
        :stroke-width="12"
      />
      <div v-if="task.error_message" class="task-error">
        {{ task.error_message }}
      </div>
    </div>

    <div v-if="task?.status === 'completed'" class="report-actions">
      <el-button
        size="small"
        @click="handleViewReport"
        :disabled="!task.report_file_ready"
      >
        <el-icon><View /></el-icon> 查看报告
      </el-button>
      <el-button
        size="small"
        @click="handleDownloadReport"
        :disabled="!task.report_file_ready"
      >
        <el-icon><Download /></el-icon> 下载HTML
      </el-button>
      <el-button
        size="small"
        @click="handleExportPdf"
        :disabled="!task.ir_file_ready"
      >
        <el-icon><Document /></el-icon> 导出PDF
      </el-button>
      <el-button
        size="small"
        @click="handleExportMd"
        :disabled="!task.ir_file_ready"
      >
        <el-icon><EditPen /></el-icon> 导出MD
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { View, Download, Document, EditPen } from '@element-plus/icons-vue'
import { useReportStore } from '@/stores/report'
import { useAppsStore } from '@/stores/apps'
import { ElMessage } from 'element-plus'

const reportStore = useReportStore()
const appsStore = useAppsStore()

const reportQuery = ref('智能舆情分析报告')

const task = computed(() => reportStore.currentTask)

const statusTagType = computed(() => {
  switch (task.value?.status) {
    case 'running': case 'pending': return 'warning'
    case 'completed': return 'success'
    case 'error': case 'cancelled': return 'danger'
    default: return 'info'
  }
})

async function handleGenerate() {
  appsStore.setActiveApp('report')
  const res = await reportStore.generateReport(reportQuery.value)
  if (res?.success) {
    ElMessage.success('报告生成已启动')
  }
}

function handleViewReport() {
  if (task.value?.report_file_path) {
    window.open(`/api/report/result/${task.value.task_id}`, '_blank')
  }
}

function handleDownloadReport() {
  if (task.value) {
    const a = document.createElement('a')
    a.href = `/api/report/download/${task.value.task_id}`
    a.click()
  }
}

function handleExportPdf() {
  if (task.value) {
    const a = document.createElement('a')
    a.href = `/api/report/export/pdf/${task.value.task_id}`
    a.click()
  }
}

function handleExportMd() {
  if (task.value) {
    const a = document.createElement('a')
    a.href = `/api/report/export/md/${task.value.task_id}`
    a.click()
  }
}
</script>

<style scoped>
.report-controls {
  padding: 12px;
  background: #fff;
  border-radius: 4px;
}
.controls-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.task-progress {
  margin-bottom: 12px;
}
.task-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}
.task-id {
  color: #909399;
  font-family: monospace;
}
.task-error {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 4px;
}
.report-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>
