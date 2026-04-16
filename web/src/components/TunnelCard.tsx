import { useState } from 'react'
import { tunnelApi, TunnelData } from '@/services/tunnelService'

export type { TunnelData } from '@/services/tunnelService'

interface TunnelCardProps {
  tunnel: TunnelData
  name: string
  onStatusChange?: (name: string, newStatus: TunnelData['status']) => void
}

const STATUS_COLORS = {
  active: '#10B981',
  connecting: '#F59E0B',
  error: '#EF4444',
  inactive: '#6B7280'
}

const STATUS_LABELS = {
  active: 'Active',
  connecting: 'Connecting',
  error: 'Error',
  inactive: 'Inactive'
}

function TunnelCard({ tunnel, name, onStatusChange }: TunnelCardProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [optimisticStatus, setOptimisticStatus] = useState<TunnelData['status'] | null>(null)

  const currentStatus = optimisticStatus || tunnel.status
  const statusColor = STATUS_COLORS[currentStatus] || STATUS_COLORS.inactive
  const statusLabel = STATUS_LABELS[currentStatus] || 'Unknown'
  const isLocal = tunnel.config.tunnel_type === 'local'

  const description = isLocal
    ? `Local ${tunnel.config.local_bind_port} → ${tunnel.config.ssh_host}:${tunnel.config.ssh_port} → ${tunnel.config.remote_bind_host}:${tunnel.config.remote_bind_port}`
    : `Remote ${tunnel.config.local_bind_port} ← ${tunnel.config.ssh_host}:${tunnel.config.ssh_port} ← ${tunnel.config.remote_bind_host}:${tunnel.config.remote_bind_port}`

  const handleStart = async () => {
    if (isLoading || currentStatus === 'connecting' || currentStatus === 'active') return

    setIsLoading(true)
    setOptimisticStatus('connecting')
    onStatusChange?.(name, 'connecting')

    try {
      await tunnelApi.start(name)
    } catch (err) {
      console.error('Failed to start tunnel:', err)
      setOptimisticStatus('error')
      onStatusChange?.(name, 'error')
    } finally {
      setIsLoading(false)
    }
  }

  const handleStop = async () => {
    if (isLoading || currentStatus === 'inactive') return

    setIsLoading(true)
    setOptimisticStatus('inactive')
    onStatusChange?.(name, 'inactive')

    try {
      await tunnelApi.stop(name)
    } catch (err) {
      console.error('Failed to stop tunnel:', err)
      setOptimisticStatus(currentStatus)
      onStatusChange?.(name, currentStatus)
    } finally {
      setIsLoading(false)
    }
  }

  const canStart = currentStatus === 'inactive' || currentStatus === 'error'
  const canStop = currentStatus === 'active' || currentStatus === 'connecting'

  return (
    <div className="bg-bg-card dark:bg-bg-card-dark border border-border-light dark:border-border-light-dark rounded-lg p-4 hover:border-border dark:hover:border-border-dark transition-colors">
      <div className="flex items-center gap-3">
        {/* Status indicator */}
        <div
          className="w-3 h-3 rounded-full flex-shrink-0"
          style={{ backgroundColor: statusColor }}
        />

        {/* Tunnel info */}
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-text dark:text-text-dark truncate">
            {name}
          </h3>
          <p className="text-xs text-text-muted dark:text-text-muted truncate">
            {description}
          </p>
          {tunnel.error && (
            <p className="text-xs text-error mt-1 truncate">{tunnel.error}</p>
          )}
        </div>

        {/* Status badge */}
        <div className="flex-shrink-0">
          <span
            className="inline-flex items-center px-2 py-1 rounded text-xs font-medium"
            style={{
              backgroundColor: `${statusColor}20`,
              color: statusColor
            }}
          >
            {statusLabel}
          </span>
        </div>

        {/* Start/Stop buttons */}
        <div className="flex-shrink-0 flex gap-2">
          {canStart && (
            <button
              onClick={handleStart}
              disabled={isLoading}
              className="inline-flex items-center justify-center w-8 h-8 rounded bg-success/10 text-success hover:bg-success/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Start tunnel"
            >
              {isLoading && !canStop ? (
                <div className="w-4 h-4 border-2 border-success border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
            </button>
          )}

          {canStop && (
            <button
              onClick={handleStop}
              disabled={isLoading}
              className="inline-flex items-center justify-center w-8 h-8 rounded bg-error/10 text-error hover:bg-error/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Stop tunnel"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-error border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                </svg>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default TunnelCard
