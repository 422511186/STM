import { useEffect, useState, useCallback, useRef } from 'react'
import api from '@/services/api'
import { TunnelData, tunnelApi } from '@/services/tunnelService'
import TunnelCard from '@/components/TunnelCard'
import AddTunnelDialog from '@/components/AddTunnelDialog'
import EditTunnelDialog from '@/components/EditTunnelDialog'
import DeleteConfirmDialog from '@/components/DeleteConfirmDialog'

interface TunnelMap {
  [name: string]: TunnelData
}

function TunnelListPage() {
  const [tunnels, setTunnels] = useState<TunnelMap>({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [isPollingPaused, setIsPollingPaused] = useState(false)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [selectedTunnel, setSelectedTunnel] = useState<{name: string; data: TunnelData} | null>(null)

  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const fetchTunnelsRef = useRef<() => Promise<void>>(async () => {})

  const fetchTunnels = useCallback(async () => {
    try {
      const response = await api.get('/tunnels')
      setTunnels(response.data)
      setError(null)
      setLastUpdated(new Date())
    } catch (err) {
      console.error('Failed to fetch tunnels:', err)
      setError('加载隧道失败')
    } finally {
      setIsLoading(false)
    }
  }, [])

  fetchTunnelsRef.current = fetchTunnels

  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) return
    pollingIntervalRef.current = setInterval(() => {
      fetchTunnelsRef.current()
    }, 3000)
  }, [])

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
  }, [])

  useEffect(() => {
    fetchTunnels()

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        setIsPollingPaused(true)
        stopPolling()
      } else {
        setIsPollingPaused(false)
        fetchTunnelsRef.current()
        startPolling()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    startPolling()

    return () => {
      stopPolling()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [fetchTunnels, startPolling, stopPolling])

  const handleTunnelStatusChange = useCallback(async (_name: string, _newStatus: TunnelData['status']) => {
    // Optimistic update is handled by TunnelCard
    // Refresh tunnel list after operation to get actual server state
    setTimeout(() => {
      tunnelApi.getAll().then((data) => {
        setTunnels(data)
        setLastUpdated(new Date())
      }).catch(console.error)
    }, 1000)
  }, [])

  const formatLastUpdated = (date: Date | null) => {
    if (!date) return ''
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diff < 5) return '刚刚'
    if (diff < 60) return `${diff}秒前`
    return date.toLocaleTimeString()
  }

  const tunnelEntries = Object.entries(tunnels)

  if (isLoading && tunnelEntries.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-text-secondary dark:text-text-secondary">加载隧道中...</p>
        </div>
      </div>
    )
  }

  if (error && tunnelEntries.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-error mb-2">{error}</p>
          <button
            onClick={fetchTunnels}
            className="text-primary hover:text-primary-hover text-sm"
          >
            重试
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text dark:text-text-dark">隧道列表</h1>
          <p className="text-sm text-text-secondary dark:text-text-secondary mt-1">
            管理您的 SSH 隧道连接
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddDialog(true)}
            className="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-sm rounded-md transition-colors"
          >
            + 添加隧道
          </button>
          {lastUpdated && (
            <div className="text-xs text-text-muted dark:text-text-muted">
              {isPollingPaused ? (
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-warning" />
                  已暂停
                </span>
              ) : (
                <span>更新于 {formatLastUpdated(lastUpdated)}</span>
              )}
            </div>
          )}
        </div>
      </div>

      {tunnelEntries.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-text-muted dark:text-text-muted">暂无隧道配置</p>
          <p className="text-sm text-text-muted dark:text-text-muted mt-1">
            点击上方「添加隧道」按钮创建
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {tunnelEntries.map(([name, data]) => (
            <TunnelCard
              key={name}
              name={name}
              tunnel={data}
              onStatusChange={handleTunnelStatusChange}
              onEdit={() => {
                setSelectedTunnel({ name, data })
                setShowEditDialog(true)
              }}
              onDelete={() => {
                setSelectedTunnel({ name, data })
                setShowDeleteDialog(true)
              }}
            />
          ))}
        </div>
      )}

      {/* Dialogs */}
      <AddTunnelDialog
        isOpen={showAddDialog}
        onClose={() => setShowAddDialog(false)}
        onSuccess={() => {
          setShowAddDialog(false)
          fetchTunnels()
        }}
      />

      <EditTunnelDialog
        isOpen={showEditDialog}
        tunnelName={selectedTunnel?.name || ''}
        tunnelData={selectedTunnel?.data || null}
        onClose={() => {
          setShowEditDialog(false)
          setSelectedTunnel(null)
        }}
        onSuccess={() => {
          setShowEditDialog(false)
          setSelectedTunnel(null)
          fetchTunnels()
        }}
      />

      <DeleteConfirmDialog
        isOpen={showDeleteDialog}
        tunnelName={selectedTunnel?.name || ''}
        onClose={() => {
          setShowDeleteDialog(false)
          setSelectedTunnel(null)
        }}
        onSuccess={() => {
          setShowDeleteDialog(false)
          setSelectedTunnel(null)
          fetchTunnels()
        }}
      />
    </div>
  )
}

export default TunnelListPage
