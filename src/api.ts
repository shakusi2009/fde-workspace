export type ApiError = Error & { status?: number }

const API_BASE = '/api'

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('fde_token')
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(payload.message || '请求失败') as ApiError
    error.status = response.status
    if (response.status === 401) {
      localStorage.removeItem('fde_token')
    }
    throw error
  }
  return payload as T
}
