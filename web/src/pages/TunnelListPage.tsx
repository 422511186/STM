import { useEffect, useState, useCallback, useRef } from 'react'
import api from '@/services/api'
import { TunnelData, tunnelApi } from '@/services/tunnelService'
import TunnelCard from '@/components/TunnelCard'

interface TunnelMap {
  [name: string]: TunnelData
}

function TunnelListPage() {
  const [tunnels, setTunnels] = useState<TunnelMap>({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [isPollingPaused, setIsPollingPaused] = useState(false)

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
      setError('Failed to load tunnels')
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
    if (diff < 5) return 'just now'
    if (diff < 60) return `${diff}s ago`
    return date.toLocaleTimeString()
  }

  const tunnelEntries = Object.entries(tunnels)

  if (isLoading && tunnelEntries.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-text-secondary dark:text-text-secondary">Loading tunnels...</p>
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
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text dark:text-text-dark">Tunnels</h1>
          <p className="text-sm text-text-secondary dark:text-text-secondary mt-1">
            Manage your SSH tunnel connections
          </p>
        </div>
        {lastUpdated && (
          <div className="text-xs text-text-muted dark:text-text-muted">
            {isPollingPaused ? (
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-warning" />
                Paused
              </span>
            ) : (
              <span>Updated {formatLastUpdated(lastUpdated)}</span>
            )}
          </div>
        )}
      </div>

      {tunnelEntries.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-text-muted dark:text-text-muted">No tunnels configured</p>
          <p className="text-sm text-text-muted dark:text-text-muted mt-1">
            Add a tunnel using the CLI to get started
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
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default TunnelListPage
