import { ref, onUnmounted } from 'vue'

export function usePolling(fn: () => Promise<void>, intervalMs: number) {
  const running = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null
  let paused = false

  function handleVisibility() {
    paused = document.hidden
  }

  function start() {
    if (running.value) return
    running.value = true
    document.addEventListener('visibilitychange', handleVisibility)
    const loop = () => {
      if (!paused) fn()
    }
    // Run immediately
    fn()
    timer = setInterval(loop, intervalMs)
  }

  function stop() {
    running.value = false
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    document.removeEventListener('visibilitychange', handleVisibility)
  }

  onUnmounted(() => stop())

  return { start, stop, running }
}
