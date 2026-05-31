<template>
  <div class="tab-content">
    <ReportControls />
    <div class="report-body">
      <ReportPreview />
    </div>
  </div>
</template>

<script setup lang="ts">
import ReportControls from '@/components/report/ReportControls.vue'
import ReportPreview from '@/components/report/ReportPreview.vue'
</script>

<style scoped>
.tab-content {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.report-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
</style>
