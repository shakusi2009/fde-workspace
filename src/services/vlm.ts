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
  prompt_id: number | null
  prompt_title: string | null
  task_input: string | null
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

export type VlmTaskItem = {
  id: number
  task_id: number
  model_id: string
  task_input: string
  total_tokens: number | null
  input_tokens: number | null
  output_tokens: number | null
  cached_tokens: number | null
  task_status: number | null
  output_text: string | null
}

export type VlmTaskItemPage = {
  items: VlmTaskItem[]
  total: number
  page: number
  page_size: number
  task_id: number
}

export type VlmTaskExecutionContext = {
  task_id: number
  prompt_id: number
  prompt_title: string
  prompt_content: string
  task_input: string
}

export type VlmTaskCreatePayload = {
  prompt_id: number
  task_type: 'label' | 'dig'
  task_input: string
  remarks: string
}

export type VlmTaskUpdatePayload = VlmTaskCreatePayload & {
  task_status: 0 | 1 | 2
}

export type VlmPrompt = {
  id: number
  title: string
  vlm_type: string
  content: string
  is_closed: boolean
  update_date: string
  create_by: string
}

export type VlmPromptPayload = {
  title: string
  vlm_type: 'label' | 'dig'
  content: string
  is_closed: boolean
}

export type VlmModel = {
  id: number
  model_id: string
  created_at: string
  updated_at: string
}

export function getVlmOverview() {
  return api<VlmOverview>('/vlm/overview')
}

export function getVlmTasks(page = 1) {
  return api<VlmTaskPage>(`/vlm/tasks?page=${page}`)
}

export function getVlmTaskItems(taskId: number, page = 1) {
  return api<VlmTaskItemPage>(`/vlm/tasks/${taskId}/items?page=${page}`)
}

export function getVlmTaskExecutionContext(taskId: number) {
  return api<VlmTaskExecutionContext>(`/vlm/tasks/${taskId}/execution-context`)
}

export function executeVlmTask(taskId: number, modelId: string) {
  return api<VlmTaskItem>(`/vlm/tasks/${taskId}/executions`, {
    method: 'POST',
    body: JSON.stringify({ model_id: modelId }),
  })
}

export function createVlmTask(payload: VlmTaskCreatePayload) {
  return api<{ id: number; message: string }>('/vlm/tasks', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateVlmTask(taskId: number, payload: VlmTaskUpdatePayload) {
  return api<{ message: string }>(`/vlm/tasks/${taskId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteVlmTask(taskId: number) {
  return api<{ message: string }>(`/vlm/tasks/${taskId}`, {
    method: 'DELETE',
  })
}

export function generateTosPrivateSignedUrl(originalUrl: string) {
  return api<{ signed_url: string }>('/vlm/tos/private-sign', {
    method: 'POST',
    body: JSON.stringify({ original_url: originalUrl }),
  })
}

export function getVlmPrompts() {
  return api<VlmPrompt[]>('/vlm/prompts')
}

export function createVlmPrompt(payload: VlmPromptPayload) {
  return api<{ id: number; message: string }>('/vlm/prompts', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateVlmPrompt(promptId: number, payload: VlmPromptPayload) {
  return api<{ message: string }>(`/vlm/prompts/${promptId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteVlmPrompt(promptId: number) {
  return api<{ message: string }>(`/vlm/prompts/${promptId}`, {
    method: 'DELETE',
  })
}

export function getVlmModels() {
  return api<VlmModel[]>('/vlm-models')
}

export function createVlmModel(modelId: string) {
  return api<{ id: number; message: string }>('/vlm-models', {
    method: 'POST',
    body: JSON.stringify({ model_id: modelId }),
  })
}

export function updateVlmModel(id: number, modelId: string) {
  return api<{ message: string }>(`/vlm-models/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ model_id: modelId }),
  })
}

export function deleteVlmModel(id: number) {
  return api<{ message: string }>(`/vlm-models/${id}`, {
    method: 'DELETE',
  })
}
