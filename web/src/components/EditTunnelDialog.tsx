import { useState, useEffect } from 'react'
import api from '@/services/api'
import { TunnelData } from '@/components/TunnelCard'

interface TunnelFormData {
  name: string
  tunnel_type: 'local' | 'remote'
  ssh_host: string
  ssh_port: string
  ssh_user: string
  ssh_password: string
  ssh_pkey: string
  local_bind_port: string
  remote_bind_host: string
  remote_bind_port: string
}

interface FormErrors {
  name?: string
  ssh_host?: string
  ssh_port?: string
  ssh_user?: string
  local_bind_port?: string
  remote_bind_host?: string
  remote_bind_port?: string
}

interface EditTunnelDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  tunnelName: string
  tunnelData: TunnelData | null
}

const HELP_TEXTS = {
  local: '【正向隧道】访问远程服务器上的服务\n流向: 本机端口 -> SSH服务器 -> 远端目标端口\n示例: 本机13306 -> SSH服务器 -> 远端MySQL 3306',
  remote: '【反向隧道】让外网访问本机服务\n流向: SSH服务器监听端口 -> 本机服务端口\n示例: SSH服务器:8080 -> 本机Web应用:8080\n前提: SSH服务器需开启 GatewayPorts'
}

function validateForm(data: TunnelFormData): FormErrors {
  const errors: FormErrors = {}

  if (!data.name.trim()) {
    errors.name = '名称不能为空'
  }

  if (!data.ssh_host.trim()) {
    errors.ssh_host = 'SSH主机不能为空'
  }

  const port = parseInt(data.ssh_port)
  if (isNaN(port) || port < 1 || port > 65535) {
    errors.ssh_port = '端口必须是1-65535之间的数字'
  }

  if (!data.ssh_user.trim()) {
    errors.ssh_user = 'SSH用户不能为空'
  }

  const localPort = parseInt(data.local_bind_port)
  if (isNaN(localPort) || localPort < 1 || localPort > 65535) {
    errors.local_bind_port = '端口必须是1-65535之间的数字'
  }

  const remotePort = parseInt(data.remote_bind_port)
  if (isNaN(remotePort) || remotePort < 1 || remotePort > 65535) {
    errors.remote_bind_port = '端口必须是1-65535之间的数字'
  }

  const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/
  if (data.remote_bind_host && !ipRegex.test(data.remote_bind_host)) {
    errors.remote_bind_host = '请输入有效的IP地址'
  }

  return errors
}

export default function EditTunnelDialog({
  isOpen,
  onClose,
  onSuccess,
  tunnelName,
  tunnelData
}: EditTunnelDialogProps) {
  const [formData, setFormData] = useState<TunnelFormData>({
    name: tunnelName,
    tunnel_type: 'local',
    ssh_host: '',
    ssh_port: '22',
    ssh_user: '',
    ssh_password: '',
    ssh_pkey: '',
    local_bind_port: '',
    remote_bind_host: '127.0.0.1',
    remote_bind_port: ''
  })

  const [errors, setErrors] = useState<FormErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && tunnelData) {
      const config = tunnelData.config
      setFormData({
        name: tunnelName,
        tunnel_type: config.tunnel_type || 'local',
        ssh_host: config.ssh_host || '',
        ssh_port: String(config.ssh_port || '22'),
        ssh_user: config.ssh_user || '',
        ssh_password: '',
        ssh_pkey: config.ssh_pkey || '',
        local_bind_port: String(config.local_bind_port || ''),
        remote_bind_host: config.remote_bind_host || '127.0.0.1',
        remote_bind_port: String(config.remote_bind_port || '')
      })
      setErrors({})
      setSubmitError(null)
    }
  }, [isOpen, tunnelName, tunnelData])

  const handleChange = (field: keyof TunnelFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (errors[field as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }

  const handleTunnelTypeChange = (type: 'local' | 'remote') => {
    setFormData(prev => ({ ...prev, tunnel_type: type }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const validationErrors = validateForm(formData)
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setIsSubmitting(true)
    setSubmitError(null)

    try {
      // Build tunnel config
      const tunnelConfig = {
        ssh_host: formData.ssh_host.trim(),
        ssh_port: parseInt(formData.ssh_port),
        ssh_user: formData.ssh_user.trim(),
        ssh_password: formData.ssh_password.trim() || null,
        ssh_pkey: formData.ssh_pkey.trim() || null,
        local_bind_host: '127.0.0.1',
        local_bind_port: parseInt(formData.local_bind_port),
        remote_bind_host: formData.remote_bind_host.trim(),
        remote_bind_port: parseInt(formData.remote_bind_port),
        autostart: tunnelData?.config?.autostart || false,
        tunnel_type: formData.tunnel_type
      }

      // If name changed, delete old tunnel first (like GUI does)
      if (tunnelName !== formData.name) {
        try {
          await api.delete(`/tunnels/${tunnelName}`)
        } catch (err) {
          // Ignore delete errors if old tunnel doesn't exist
        }
      }

      // Save tunnel via PUT endpoint
      await api.put(`/tunnels/${formData.name}`, tunnelConfig)

      onSuccess()
      onClose()
    } catch (err: any) {
      console.error('Failed to update tunnel:', err)
      setSubmitError(err.response?.data?.message || '更新隧道失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    setErrors({})
    setSubmitError(null)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleClose}
      />

      {/* Dialog */}
      <div className="relative bg-bg-card dark:bg-bg-card-dark rounded-lg shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border-light dark:border-border-light-dark">
          <h2 className="text-lg font-semibold text-text dark:text-text-dark">编辑隧道</h2>
        </div>

        {/* Help Text */}
        <div className="mx-6 mt-4 px-4 py-3 bg-bg-input dark:bg-bg-input-dark rounded-md border border-border-light dark:border-border-light-dark">
          <p className="text-xs text-text-secondary dark:text-text-secondary whitespace-pre-line">
            {HELP_TEXTS[formData.tunnel_type]}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6">
          {/* Name */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1.5">
              名称 <span className="text-error">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="隧道的唯一标识"
              className={`w-full px-3 py-2 bg-bg-input dark:bg-bg-input-dark border rounded-md text-text dark:text-text-dark placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary ${
                errors.name ? 'border-error' : 'border-border-light dark:border-border-light-dark'
              }`}
            />
            {errors.name && <p className="mt-1 text-xs text-error">{errors.name}</p>}
          </div>

          {/* Tunnel Type */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1.5">
              隧道类型
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => handleTunnelTypeChange('local')}
                className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                  formData.tunnel_type === 'local'
                    ? 'bg-primary text-white'
                    : 'bg-bg-input dark:bg-bg-input-dark border border-border-light dark:border-border-light-dark text-text-secondary hover:border-primary'
                }`}
              >
                正向隧道 (Local)
              </button>
              <button
                type="button"
                onClick={() => handleTunnelTypeChange('remote')}
                className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                  formData.tunnel_type === 'remote'
                    ? 'bg-primary text-white'
                    : 'bg-bg-input dark:bg-bg-input-dark border border-border-light dark:border-border-light-dark text-text-secondary hover:border-primary'
                }`}
              >
                反向隧道 (Remote)
              </button>
            </div>
          </div>

          {/* Section: SSH 连接 */}
          <div className="mb-4">
            <p className="text-xs text-text-muted dark:text-text-muted uppercase tracking-wider mb-2">SSH 连接</p>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1.5">
                  SSH 主机 <span className="text-error">*</span>
                </label>
                <input
                  type="text"
                  value={formData.ssh_host}
                  onChange={(e) => handleChange('ssh_host', e.target.value)}
                  placeholder="SSH服务器地址"
                  className={`w-full px-3 py-2 bg-bg-input dark:bg-bg-input-dark border rounded-md text-text dark:text-text-dark placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary ${
                    errors.ssh_host ? 'border-error' : 'border-border-light dark:border-border-light-dark'
                  }`}
                />
                {errors.ssh_host && <p className="mt-1 text-xs text-error">{errors.ssh_host}</p>}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1.5">
                    SSH 端口
                  </label>
                  <input
                    type="number"
                    value={formData.ssh_port}
                    onChange={(e) => handleChange('ssh_port', e.target.value)}
                    min="1"
                    max="65535"
                    placeholder="22"
                    className={`w-full px-3 py-2 bg-bg-input dark:bg-bg-input-dark border rounded-md text-text dark:text-text-dark placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary ${
                      errors.ssh_port ? 'border-error' : 'border-border-light dark:border-border-light-dark'
                    }`}
                  />
                  {errors.ssh_port && <p className="mt-1 text-xs text-error">{errors.ssh_port}</p>}
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1.5">
                    SSH 用户 <span className="text-error">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.ssh_user}
                    onChange={(e) => handleChange('ssh_user', e.target.value)}
                    placeholder="用户名"
                    className={`w-full px-3 py-2 bg-bg-input dark:bg-bg-input-dark border rounded-md text-text dark:text-text-dark placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary ${
                      errors.ssh_user ? 'border-error' : 'border-border-light dark:border-border-light-dark'
                    }`}
                  />
                  {errors.ssh_user && <p className="mt-1 text-xs text-error">{errors.ssh_user}</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1.5">
                  SSH 私钥路径
                </label>
                <input
                  type="text"
                  value={formData.ssh_pkey}
                  onChange={(e) => handleChange('ssh_pkey', e.target.value)}
                  placeholder="~/.ssh/id_rsa"
                  className="w-full px-3 py-2 bg-bg-input dark:bg-bg-input-dark border border-border-light dark:border-border-light-dark rounded-md text-text dark:text-text-dark placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1.5">
                  SSH 密码
                </label>
                <input
                  type="password"
                  value={formData.ssh_password}
                  onChange={(e) => handleChange('ssh_password', e.target.value)}
                  placeholder="留空保持不变"
                  className="w-full px-3 py-2 bg-bg-input dark:bg-bg-input-dark border border-border-light dark:border-border-light-dark rounded-md text-text dark:text-text-dark placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <p className="mt-1 text-xs text-text-muted">留空将保持原有密码</p>
              </div>
            </div>
          </div>

          {/* Section: 隧道设置 */}
          <div className="mb-4">
            <p className="text-xs text-text-muted dark:text-text-muted uppercase tracking-wider mb-2">隧道设置</p>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1.5">
                  本地端口 <span className="text-error">*</span>
                </label>
                <input
                  type="number"
                  value={formData.local_bind_port}
                  onChange={(e) => handleChange('local_bind_port', e.target.value)}
                  min="1"
                  max="65535"
                  placeholder="本机监听端口"
                  className={`w-full px-3 py-2 bg-bg-input dark:bg-bg-input-dark border rounded-md text-text dark:text-text-dark placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary ${
                    errors.local_bind_port ? 'border-error' : 'border-border-light dark:border-border-light-dark'
                  }`}
                />
                {errors.local_bind_port && <p className="mt-1 text-xs text-error">{errors.local_bind_port}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1.5">
                  远端主机
                </label>
                <input
                  type="text"
                  value={formData.remote_bind_host}
                  onChange={(e) => handleChange('remote_bind_host', e.target.value)}
                  placeholder="127.0.0.1"
                  className={`w-full px-3 py-2 bg-bg-input dark:bg-bg-input-dark border rounded-md text-text dark:text-text-dark placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary ${
                    errors.remote_bind_host ? 'border-error' : 'border-border-light dark:border-border-light-dark'
                  }`}
                />
                {errors.remote_bind_host && <p className="mt-1 text-xs text-error">{errors.remote_bind_host}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1.5">
                  远端端口 <span className="text-error">*</span>
                </label>
                <input
                  type="number"
                  value={formData.remote_bind_port}
                  onChange={(e) => handleChange('remote_bind_port', e.target.value)}
                  min="1"
                  max="65535"
                  placeholder="目标端口"
                  className={`w-full px-3 py-2 bg-bg-input dark:bg-bg-input-dark border rounded-md text-text dark:text-text-dark placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary ${
                    errors.remote_bind_port ? 'border-error' : 'border-border-light dark:border-border-light-dark'
                  }`}
                />
                {errors.remote_bind_port && <p className="mt-1 text-xs text-error">{errors.remote_bind_port}</p>}
              </div>
            </div>
          </div>

          {/* Submit Error */}
          {submitError && (
            <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-md">
              <p className="text-sm text-error">{submitError}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-text-secondary dark:text-text-secondary bg-transparent border border-border-light dark:border-border-light-dark rounded-md hover:bg-bg-hover dark:hover:bg-bg-hover-dark transition-colors disabled:opacity-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-primary rounded-md hover:bg-primary-hover transition-colors disabled:opacity-50"
            >
              {isSubmitting ? '保存中...' : '保存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}