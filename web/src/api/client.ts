export interface DashboardStatus {
  thread_id: string
  has_checkpoint?: boolean
  phase: string
  complete?: boolean
  next_nodes?: string[]
  current_chapter?: { id: number; title: string } | null
  chapters_written?: number
  total_chapters?: number
  progress?: number
  rag?: RagStatus
}

export interface RagStatus {
  chunk_count?: number
  healthy?: boolean
  persist_dir?: string
  collection?: string
}

export interface ChapterSummary {
  id: number
  title: string
  status: string
  written: boolean
  word_count: number
  revision_count: number
  feedback: { fact: string; style: string; review: string }
}

export interface ChapterPart {
  name: string
  prefix: string
  chapters: ChapterSummary[]
}

export interface ChapterTree {
  book_title: string
  parts: ChapterPart[]
}

export interface ChapterDetail extends ChapterSummary {
  markdown: string
}

export interface LogEntry {
  timestamp: string
  level: string
  logger: string
  agent: string
  message: string
  raw: string
  chapter_id: number | null
}

export interface Metrics {
  agent_durations: Record<string, number>
  chapter_durations: Record<string, number>
  log_entries?: number
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  status: (threadId = 'book-1') => getJson<DashboardStatus>(`/api/status?thread_id=${encodeURIComponent(threadId)}`),
  chapters: (threadId = 'book-1') => getJson<ChapterTree>(`/api/chapters?thread_id=${encodeURIComponent(threadId)}`),
  chapter: (chapterId: number, threadId = 'book-1') =>
    getJson<ChapterDetail>(`/api/chapters/${chapterId}?thread_id=${encodeURIComponent(threadId)}`),
  logs: (params = '') => getJson<LogEntry[]>(`/api/logs${params}`),
  metrics: () => getJson<Metrics>('/api/metrics'),
  ragStatus: () => getJson<RagStatus>('/api/rag/status'),
}
