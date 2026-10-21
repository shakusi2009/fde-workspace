import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api'

export type AuthUser = {
  id: number
  username: string
  display_name: string
  role_id: number
  role_name: string
  permissions: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const token = ref(localStorage.getItem('fde_token'))
  const ready = ref(false)
  const isAuthenticated = computed(() => Boolean(token.value && user.value))

  async function login(payload: {
    username: string
    password: string
    captchaId: string
    captchaCode: string
  }) {
    const result = await api<{ token: string; user: AuthUser }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    token.value = result.token
    user.value = result.user
    localStorage.setItem('fde_token', result.token)
  }

  async function restore() {
    if (!token.value) {
      ready.value = true
      return
    }
    try {
      const result = await api<{ user: AuthUser }>('/auth/me')
      user.value = result.user
    } catch {
      clear()
    } finally {
      ready.value = true
    }
  }

  async function logout() {
    try {
      await api('/auth/logout', { method: 'POST' })
    } finally {
      clear()
    }
  }

  function clear() {
    token.value = null
    user.value = null
    localStorage.removeItem('fde_token')
  }

  function can(permission: string) {
    return Boolean(user.value?.permissions.includes(permission))
  }

  return { user, token, ready, isAuthenticated, login, restore, logout, clear, can }
})
