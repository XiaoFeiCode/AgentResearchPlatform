import client from './client'

export function fetchReportStatus() {
  return client.get('/api/report/status')
}

export function generateReport(query: string, customTemplate: string = '') {
  return client.post('/api/report/generate', { query, custom_template: customTemplate })
}

export function fetchReportProgress(taskId: string) {
  return client.get(`/api/report/progress/${taskId}`)
}

export function fetchReportResult(taskId: string) {
  return client.get(`/api/report/result/${taskId}`)
}

export function fetchReportResultJson(taskId: string) {
  return client.get(`/api/report/result/${taskId}/json`)
}

export function downloadReport(taskId: string) {
  return client.get(`/api/report/download/${taskId}`, { responseType: 'blob' })
}

export function cancelReport(taskId: string) {
  return client.post(`/api/report/cancel/${taskId}`)
}

export function fetchReportTemplates() {
  return client.get('/api/report/templates')
}

export function fetchReportLog() {
  return client.get('/api/report/log')
}

export function clearReportLog() {
  return client.post('/api/report/log/clear')
}

export function exportMarkdown(taskId: string) {
  return client.get(`/api/report/export/md/${taskId}`, { responseType: 'blob' })
}

export function exportPdf(taskId: string, optimize: boolean = true) {
  return client.get(`/api/report/export/pdf/${taskId}`, {
    params: { optimize },
    responseType: 'blob',
  })
}

export function exportPdfFromIr(documentIr: Record<string, any>, optimize: boolean = true) {
  return client.post('/api/report/export/pdf-from-ir', {
    document_ir: documentIr,
    optimize,
  }, { responseType: 'blob' })
}
