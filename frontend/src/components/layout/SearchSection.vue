<template>
  <div class="command-section">
    <div class="command-bar">
      <div class="query-box">
        <el-input
          v-model="query"
          size="large"
          clearable
          placeholder="输入舆情主题、事件名称或关键词"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <div class="command-actions">
        <el-button
          type="primary"
          size="large"
          :icon="VideoPlay"
          :loading="searchStore.searching"
          @click="handleSearch"
        >
          开始分析
        </el-button>

        <label class="template-upload">
          <input
            type="file"
            accept=".md,.txt"
            @change="handleFileUpload"
          />
          <el-tooltip content="上传报告模板" placement="bottom">
            <el-button size="large" :icon="Upload" />
          </el-tooltip>
        </label>

        <el-tooltip content="LLM 配置" placement="bottom">
          <el-button
            size="large"
            :icon="Setting"
            @click="configStore.openModal"
          />
        </el-tooltip>
      </div>
    </div>

    <div v-if="showProgress" class="progress-strip">
      <div
        v-for="item in progressItems"
        :key="item.key"
        class="progress-card"
        :class="item.state.status"
      >
        <div class="progress-card-head">
          <span>{{ item.label }}</span>
          <strong>{{ item.state.progressPct }}%</strong>
        </div>
        <el-progress
          :percentage="item.state.progressPct"
          :stroke-width="8"
          :show-text="false"
          :status="item.state.status === 'error' ? 'exception' : item.state.status === 'done' ? 'success' : undefined"
        />
        <p>{{ item.state.message || item.idleText }}</p>
        <small v-if="item.state.paragraphTotal > 0">
          段落 {{ item.state.paragraphCurrent }} / {{ item.state.paragraphTotal }}
        </small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Search, Setting, Upload, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useSearchStore } from '@/stores/search'
import { useConfigStore } from '@/stores/config'

const searchStore = useSearchStore()
const configStore = useConfigStore()
const query = ref('')

const progressItems = computed(() => [
  { key: 'insight', label: 'Insight 私域数据', idleText: '等待数据库分析', state: searchStore.engines.insight },
  { key: 'media', label: 'Media 媒体传播', idleText: '等待网络检索', state: searchStore.engines.media },
  { key: 'query', label: 'Query 权威核查', idleText: '等待事实核查', state: searchStore.engines.query },
])

const showProgress = computed(() => progressItems.value.some((item) => item.state.status !== 'idle'))

async function handleSearch() {
  const q = query.value.trim()
  if (!q) return
  try {
    await searchStore.performSearch(q)
    ElMessage.success('分析任务已分发')
  } catch {
    ElMessage.error('分析请求失败')
  }
}

function handleFileUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 1024 * 1024) {
    ElMessage.warning('模板文件不能超过 1MB')
    input.value = ''
    return
  }

  const reader = new FileReader()
  reader.onload = (ev) => {
    configStore.values.custom_template = ev.target?.result as string
    ElMessage.success('模板已载入')
  }
  reader.readAsText(file)
  input.value = ''
}
</script>

<style scoped>
.command-section {
  background: #ffffff;
}

.command-bar {
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 22px 14px;
}

.query-box {
  flex: 1;
  min-width: 260px;
}

.query-box :deep(.el-input__wrapper) {
  min-height: 44px;
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d7e0ea inset;
}

.query-box :deep(.el-input__inner) {
  font-size: 15px;
}

.command-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.template-upload input {
  display: none;
}

.command-actions :deep(.el-button) {
  border-radius: 8px;
}

.progress-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 0 22px 14px;
}

.progress-card {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #f8fafc;
}

.progress-card.running {
  border-color: #f1c77c;
  background: #fffaf0;
}

.progress-card.done {
  border-color: #aad8bd;
  background: #f0f8f3;
}

.progress-card.error {
  border-color: #f2b4aa;
  background: #fff0ed;
}

.progress-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.progress-card-head span {
  min-width: 0;
  color: #344054;
  font-size: 13px;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-card-head strong {
  color: #17212b;
  font-size: 13px;
}

.progress-card p,
.progress-card small {
  display: block;
  margin: 7px 0 0;
  color: #697586;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .command-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .command-actions {
    justify-content: flex-end;
  }

  .progress-strip {
    grid-template-columns: 1fr;
  }
}
</style>
