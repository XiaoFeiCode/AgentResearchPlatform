<template>
  <section class="engine-panel">
    <header class="engine-head">
      <div>
        <p class="eyebrow">{{ engineMeta.role }}</p>
        <h2>{{ engineMeta.title }}</h2>
      </div>
      <el-tag :type="tagType" effect="plain">{{ statusText }}</el-tag>
    </header>

    <div v-if="state.status === 'idle'" class="state-empty">
      <el-icon :size="46"><Search /></el-icon>
      <strong>{{ engineMeta.title }}</strong>
      <span>等待任务输入</span>
    </div>

    <div v-else-if="state.status === 'running'" class="state-running">
      <div class="progress-box">
        <el-progress
          :percentage="state.progressPct"
          :stroke-width="14"
          :show-text="false"
          :status="state.progressPct === 100 ? 'success' : undefined"
        />
        <div class="progress-meta">
          <strong>{{ state.progressPct }}%</strong>
          <span>{{ state.message }}</span>
        </div>
      </div>
      <div v-if="state.paragraphTotal > 0" class="paragraph-chip">
        段落 {{ state.paragraphCurrent }} / {{ state.paragraphTotal }}
      </div>
    </div>

    <div v-else-if="state.status === 'error'" class="state-error">
      <el-alert :title="state.error" type="error" show-icon :closable="false" />
    </div>

    <div v-else-if="state.status === 'done'" class="state-done">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="分析摘要" name="summary">
          <article class="markdown-body" v-html="renderedReport" />
        </el-tab-pane>
        <el-tab-pane label="引用来源" name="citations">
          <div v-if="state.citations.length === 0" class="empty-citations">
            暂无引用信息
          </div>
          <el-collapse v-else>
            <el-collapse-item
              v-for="(citation, idx) in state.citations"
              :key="idx"
              :title="`搜索 ${idx + 1}: ${citation.query || '未记录查询'}`"
            >
              <p><strong>段落:</strong> {{ citation.paragraph_title }}</p>
              <p><strong>URL:</strong> {{ citation.url || '无' }}</p>
              <p><strong>标题:</strong> {{ citation.title || '无' }}</p>
              <p><strong>内容预览:</strong> {{ citation.content || '无可用内容' }}</p>
              <p v-if="citation.score"><strong>相关度:</strong> {{ citation.score }}</p>
              <p><strong>搜索次数:</strong> {{ citation.search_count }}</p>
              <p><strong>反思次数:</strong> {{ citation.reflection_count }}</p>
            </el-collapse-item>
          </el-collapse>
        </el-tab-pane>
      </el-tabs>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { useSearchStore, type EngineState } from '@/stores/search'

const props = withDefaults(defineProps<{
  engine: 'insight' | 'media' | 'query'
}>(), {})

const meta: Record<string, { title: string; role: string }> = {
  insight: { title: 'Insight Agent', role: '私域舆情数据库' },
  media: { title: 'Media Agent', role: '媒体报道与传播路径' },
  query: { title: 'Query Agent', role: '权威信息与事实核查' },
}

const searchStore = useSearchStore()
const state = computed<EngineState>(() => searchStore.engines[props.engine])
const engineMeta = computed(() => meta[props.engine])
const activeTab = ref('summary')

const statusText = computed(() => {
  const status = state.value.status
  if (status === 'running') return '运行中'
  if (status === 'done') return '已完成'
  if (status === 'error') return '异常'
  return '待命'
})

const tagType = computed(() => {
  const status = state.value.status
  if (status === 'running') return 'warning'
  if (status === 'done') return 'success'
  if (status === 'error') return 'danger'
  return 'info'
})

const renderedReport = computed(() => {
  if (!state.value.finalReport) return ''
  return marked(state.value.finalReport) as string
})

watch(() => state.value.status, (newStatus) => {
  if (newStatus === 'running') {
    activeTab.value = 'summary'
  }
})
</script>

<style scoped>
.engine-panel {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
}

.engine-head {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
  padding: 18px 22px;
  border-bottom: 1px solid #e5e9f0;
  background: #fbfcfe;
}

.eyebrow {
  margin: 0 0 4px;
  color: #697586;
  font-size: 12px;
  font-weight: 700;
}

.engine-head h2 {
  margin: 0;
  color: #17212b;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0;
}

.state-empty,
.state-running,
.state-error {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 24px;
}

.state-empty {
  gap: 8px;
  color: #8b98a7;
}

.state-empty strong {
  color: #344054;
  font-size: 18px;
}

.state-empty span {
  font-size: 13px;
}

.state-running {
  gap: 18px;
}

.progress-box {
  width: min(720px, 78%);
}

.progress-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-top: 12px;
}

.progress-meta strong {
  color: #17212b;
  font-size: 22px;
}

.progress-meta span {
  min-width: 0;
  color: #52606d;
  text-align: right;
  overflow-wrap: anywhere;
}

.paragraph-chip {
  padding: 6px 12px;
  color: #2b5f48;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid #b9dfca;
  border-radius: 16px;
  background: #edf9f1;
}

.state-done {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0 22px 18px;
}

.state-done :deep(.el-tabs) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.state-done :deep(.el-tabs__header) {
  flex-shrink: 0;
}

.state-done :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: 32px;
}

.markdown-body {
  max-width: 980px;
  padding: 8px 0 48px;
  color: #24313f;
  line-height: 1.78;
  overflow-wrap: anywhere;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 1em 0 0.5em;
  color: #17212b;
  letter-spacing: 0;
}

.markdown-body :deep(p) {
  margin: 0.55em 0;
}

.markdown-body :deep(code) {
  padding: 2px 6px;
  border-radius: 4px;
  background: #eef2f6;
}

.markdown-body :deep(pre) {
  padding: 12px;
  overflow-x: auto;
  border-radius: 6px;
  background: #eef2f6;
}

.markdown-body :deep(blockquote) {
  margin: 0.6em 0;
  padding: 6px 14px;
  color: #52606d;
  border-left: 4px solid #26a269;
  background: #f0f8f3;
}

.empty-citations {
  padding: 40px 0;
  color: #8b98a7;
  text-align: center;
}
</style>
