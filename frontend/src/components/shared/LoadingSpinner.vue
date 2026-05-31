<template>
  <div class="loading-spinner" v-if="visible">
    <el-icon class="is-loading" :size="size"><Loading /></el-icon>
    <span v-if="text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'

withDefaults(defineProps<{
  visible: boolean
  text?: string
  size?: number
}>(), {
  size: 32,
})
</script>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  color: #909399;
}
</style>
