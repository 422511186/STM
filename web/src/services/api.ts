import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

const TOKEN_KEY = 'ssh_tunnel_token'

const api = axios.create({
  baseURL: 'http://127.0.0.1:50051',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - add Authorization header
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - handle 401 and errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - logout
      const { logout } = useAuthStore.getState()
      logout()
      // Redirect to login if not already there
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

// Config API functions
export const configApi = {
  exportConfig: () => {
    return api.get('/config/export', {
      responseType: 'blob',
    })
  },

  importConfig: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/config/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  reloadConfig: () => {
    return api.post('/config/reload')
  },
}

// Auth API functions
export const authApi = {
  login: async (password: string) => {
    const response = await api.post('/auth/login', { password })
    return response.data
  },

  logout: async () => {
    try {
      await api.post('/auth/logout')
    } finally {
      const { logout } = useAuthStore.getState()
      logout()
    }
  },

  checkStatus: async () => {
    const response = await api.get('/auth/status')
    return response.data
  }
}
