import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import * as searchApi from '@/api/search'

export interface Citation {
  paragraph_index: number
  paragraph_title: string
  query: string
  url: string | null
  title: string | null
  content: string | null
  score: number | null
  search_count: number
  reflection_count: number
}

export interface EngineState {
  status: 'idle' | 'running' | 'done' | 'error'
  progressPct: number
  message: string
  paragraphCurrent: number
  paragraphTotal: number
  finalReport: string
  citations: Citation[]
  error: string
}

function emptyEngineState(): EngineState {
  return {
    status: 'idle',
    progressPct: 0,
    message: '',
    paragraphCurrent: 0,
    paragraphTotal: 0,
    finalReport: '',
    citations: [],
    error: '',
  }
}

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const searching = ref(false)
  const lastResult = ref<any>(null)

  const engines = reactive<Record<string, EngineState>>({
    insight: emptyEngineState(),
    media: emptyEngineState(),
    query: emptyEngineState(),
  })

  function resetEngine(engine: string) {
    Object.assign(engines[engine], emptyEngineState())
  }

  function handleEngineProgress(data: any) {
    const engine = data.engine
    if (!engines[engine]) return
    engines[engine].status = 'running'
    engines[engine].progressPct = data.progress_pct ?? 0
    engines[engine].message = data.message ?? ''
    engines[engine].paragraphCurrent = data.paragraph_current ?? 0
    engines[engine].paragraphTotal = data.paragraph_total ?? 0
  }

  function handleEngineResult(data: any) {
    const engine = data.engine
    if (!engines[engine]) return
    engines[engine].status = 'done'
    engines[engine].progressPct = 100
    engines[engine].finalReport = data.final_report ?? ''
    engines[engine].citations = data.citations ?? []
    engines[engine].message = '研究完成'
  }

  function handleEngineError(data: any) {
    const engine = data.engine
    if (!engines[engine]) return
    engines[engine].status = 'error'
    engines[engine].error = data.error ?? '未知错误'
    engines[engine].message = data.error ?? '研究出错'
  }

  async function fetchLatestResults() {
    const res = await searchApi.fetchLatestResults()
    const results = res.data?.results || {}
    Object.entries(results).forEach(([engine, data]: [string, any]) => {
      if (engines[engine] && data?.final_report) {
        handleEngineResult(data)
      }
    })
    return res.data
  }

  async function performSearch(q: string) {
    query.value = q
    searching.value = true
    // Reset all engines for new search
    resetEngine('insight')
    resetEngine('media')
    resetEngine('query')
    try {
      const res = await searchApi.search(q)
      lastResult.value = res.data
      return res.data
    } finally {
      searching.value = false
    }
  }

  return {
    query, searching, lastResult, engines,
    resetEngine, handleEngineProgress, handleEngineResult, handleEngineError,
    performSearch, fetchLatestResults,
  }
})
