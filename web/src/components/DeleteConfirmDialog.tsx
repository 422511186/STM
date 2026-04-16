import { useState } from 'react'
import api from '@/services/api'

interface DeleteConfirmDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  tunnelName: string
}

export default function DeleteConfirmDialog({
  isOpen,
  onClose,
  onSuccess,
  tunnelName
}: DeleteConfirmDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDelete = async () => {
    setIsDeleting(true)
    setError(null)

    try {
      // Get current tunnels
      const tunnelsResponse = await api.get('/tunnels')
      const currentTunnels = tunnelsResponse.data as Record<string, any>

      // Remove the tunnel
      if (currentTunnels[tunnelName]) {
        delete currentTunnels[tunnelName]
      }

      // Reload config to apply changes
      await api.post('/config/reload')

      onSuccess()
      onClose()
    } catch (err: any) {
      console.error('Failed to delete tunnel:', err)
      setError(err.response?.data?.message || '删除隧道失败')
    } finally {
      setIsDeleting(false)
    }
  }

  const handleClose = () => {
    setError(null)
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
      <div className="relative bg-bg-card dark:bg-bg-card-dark rounded-lg shadow-xl w-full max-w-sm mx-4">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border-light dark:border-border-light-dark">
          <h2 className="text-lg font-semibold text-text dark:text-text-dark">确认删除</h2>
        </div>

        {/* Content */}
        <div className="p-6">
          <div className="flex items-start gap-4">
            {/* Warning Icon */}
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-error/10 flex items-center justify-center">
              <svg
                className="w-5 h-5 text-error"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            {/* Text Content */}
            <div className="flex-1">
              <p className="text-sm text-text dark:text-text-dark">
                确定要删除隧道 <span className="font-semibold">"{tunnelName}"</span> 吗？
              </p>
              <p className="mt-2 text-xs text-text-muted dark:text-text-muted">
                此操作无法撤销。隧道配置将被永久删除。
              </p>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="mt-4 p-3 bg-error/10 border border-error/20 rounded-md">
              <p className="text-sm text-error">{error}</p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-6 py-4 bg-bg-input dark:bg-bg-input-dark rounded-b-lg border-t border-border-light dark:border-border-light-dark">
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isDeleting}
              className="px-4 py-2 text-sm font-medium text-text-secondary dark:text-text-secondary bg-transparent border border-border-light dark:border-border-light-dark rounded-md hover:bg-bg-hover dark:hover:bg-bg-hover-dark transition-colors disabled:opacity-50"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={isDeleting}
              className="px-4 py-2 text-sm font-medium text-white bg-error rounded-md hover:bg-error/90 transition-colors disabled:opacity-50"
            >
              {isDeleting ? '删除中...' : '删除'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}