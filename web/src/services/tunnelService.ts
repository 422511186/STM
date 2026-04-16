import api from '@/services/api'

export interface TunnelConfig {
  ssh_host: string
  ssh_port: number
  ssh_user: string
  ssh_password: string | null
  ssh_pkey: string | null
  local_bind_host: string
  local_bind_port: number
  remote_bind_host: string
  remote_bind_port: number
  autostart: boolean
  tunnel_type: 'local' | 'remote'
}

export interface TunnelData {
  config: TunnelConfig
  status: 'active' | 'connecting' | 'error' | 'inactive'
  error: string
  local_port: number | null
}

export interface TunnelMap {
  [name: string]: TunnelData
}

export const tunnelApi = {
  getAll: async (): Promise<TunnelMap> => {
    const response = await api.get('/tunnels')
    return response.data
  },

  start: async (name: string): Promise<void> => {
    await api.post(`/tunnels/${name}/start`)
  },

  stop: async (name: string): Promise<void> => {
    await api.post(`/tunnels/${name}/stop`)
  }
}