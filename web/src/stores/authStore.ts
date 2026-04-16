import { create } from 'zustand'

const TOKEN_KEY = 'ssh_tunnel_token'

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  login: (token: string) => void
  logout: () => void
  init: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,

  init: () => {
    const token = localStorage.getItem(TOKEN_KEY)
    set({
      token,
      isAuthenticated: !!token
    })
  },

  login: (token: string) => {
    localStorage.setItem(TOKEN_KEY, token)
    set({
      token,
      isAuthenticated: true
    })
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    set({
      token: null,
      isAuthenticated: false
    })
  }
}))
