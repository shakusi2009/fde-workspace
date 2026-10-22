import { api } from '@/api'

export type TrendPoint = {
  label: string
  value: number
}

export type VlmOverview = {
  task_total: number
  overall_accuracy: number | null
  token_total: number
  task_trend: TrendPoint[]
  token_trend: TrendPoint[]
  data_status: 'pending' | 'ready'
}

export type VlmTask = {
  sequence: number
  task_type: string
  created_at: string
  token_usage: number
  accuracy: number | null
  remark: string
  task_status: number
  updated_at: string | null
}

export type VlmTaskPage = {
  items: VlmTask[]
  total: number
  page: number
  page_size: number
}

export function getVlmOverview() {
  return api<VlmOverview>('/vlm/overview')
}

export function getVlmTasks(page = 1) {
  return api<VlmTaskPage>(`/vlm/tasks?page=${page}`)
}
