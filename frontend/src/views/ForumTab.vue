<template>
  <div class="tab-content">
    <ForumChat />
  </div>
</template>

<script setup lang="ts">
import ForumChat from '@/components/forum/ForumChat.vue'
</script>

<style scoped>
.tab-content { width: 100%; height: 100%; display: flex; flex-direction: column; }
</style>
