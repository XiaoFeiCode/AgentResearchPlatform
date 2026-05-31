<template>
  <div class="forum-chat-wrapper">
    <div class="forum-chat-header">
      <span class="forum-title">
        <el-icon><ChatDotRound /></el-icon> Forum 消息
      </span>
      <el-button size="small" text :icon="Refresh" @click="manualRefresh" title="刷新消息" />
    </div>
    <div class="forum-chat" ref="chatRef" @scroll="onScroll">
      <div v-if="forumStore.messages.length === 0" class="forum-empty">
        <el-icon :size="36"><ChatDotRound /></el-icon>
        <p>Forum Engine 未启动或暂无消息</p>
      </div>
      <div
        v-for="msg in forumStore.messages"
        :key="msg.id"
        class="forum-message"
        :class="`msg-${msg.type}`"
      >
        <span class="msg-agent">{{ msg.agent }}</span>
        <span class="msg-time">{{ msg.timestamp }}</span>
        <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, ref, nextTick, onBeforeUnmount } from 'vue'
import { ChatDotRound, Refresh } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { useForumStore } from '@/stores/forum'

function renderMarkdown(text: string): string {
  if (!text) return ''
  return marked.parse(text, { breaks: true, gfm: true }) as string
}

const forumStore = useForumStore()
const chatRef = ref<HTMLElement | null>(null)

// Scroll detection
const userScrolledUp = ref(false)
let scrollRestTimer: ReturnType<typeof setTimeout> | null = null

function onScroll() {
  if (!chatRef.value) return
  const { scrollTop, scrollHeight, clientHeight } = chatRef.value
  if (scrollTop < scrollHeight - clientHeight - 60) {
    userScrolledUp.value = true
    // Re-enable auto-scroll after 3s idle
    if (scrollRestTimer) clearTimeout(scrollRestTimer)
    scrollRestTimer = setTimeout(() => { userScrolledUp.value = false }, 3000)
  } else {
    userScrolledUp.value = false
  }
}

function scrollToBottom() {
  if (userScrolledUp.value) return
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

onBeforeUnmount(() => {
  if (scrollRestTimer) clearTimeout(scrollRestTimer)
})

// Auto-scroll on new messages (respects user scroll position)
watch(() => forumStore.messages.length, scrollToBottom)

// Initial load on mount
forumStore.fetchLog()

async function manualRefresh() {
  await forumStore.fetchLog()
  scrollToBottom()
}
</script>

<style scoped>
.forum-chat-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.forum-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}
.forum-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}
.forum-chat {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  background: #fafafa;
}
.forum-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  gap: 8px;
}
.forum-message {
  margin-bottom: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.forum-message.msg-user {
  border-left: 3px solid #409eff;
}
.forum-message.msg-agent {
  border-left: 3px solid #67c23a;
}
.forum-message.msg-system {
  border-left: 3px solid #e6a23c;
  background: #fef9e7;
}
.forum-message.msg-host {
  border-left: 3px solid #909399;
}
.msg-agent {
  font-weight: 600;
  font-size: 12px;
  color: #303133;
}
.msg-time {
  font-size: 11px;
  color: #909399;
  margin-left: 8px;
}
.msg-content {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.6;
}
.msg-content :deep(p) {
  margin: 4px 0;
}
.msg-content :deep(strong) {
  font-weight: 600;
}
.msg-content :deep(ul), .msg-content :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}
.msg-content :deep(code) {
  background: #f4f4f5;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
}
.msg-content :deep(h1), .msg-content :deep(h2), .msg-content :deep(h3) {
  font-size: 14px;
  margin: 6px 0 4px;
}
.msg-content :deep(h1) { font-size: 15px; }
.msg-content :deep(h2) { font-size: 14px; }
.msg-content :deep(h3) { font-size: 13px; }
</style>
