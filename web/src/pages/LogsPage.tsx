import { useEffect, useState, useRef } from 'react'
import api from '@/services/api'

interface LogsResponse {
  logs: string[]
  total: number
}

function LogsPage() {
  const [logs, setLogs] = useState<string[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const preRef = useRef<HTMLPreElement>(null)

  const fetchLogs = async () => {
    try {
      const response = await api.get<LogsResponse>('/logs?lines=100')
      setLogs(response.data.logs)
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()

    const interval = setInterval(fetchLogs, 3000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (autoScroll && preRef.current) {
      preRef.current.scrollTop = preRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  const getLogColor = (line: string): string => {
    if (line.includes('ERROR')) return 'text-red-500'
    if (line.includes('WARN')) return 'text-orange-500'
    return 'text-text dark:text-text-dark'
  }

  if (isLoading && logs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-text-secondary dark:text-text-secondary">Loading logs...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text dark:text-text-dark">Logs</h1>
          <p className="text-sm text-text-secondary dark:text-text-secondary mt-1">
            Tunnel operation logs
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="w-4 h-4 rounded border-border-light dark:border-border-light-dark bg-bg-card dark:bg-bg-card-dark text-primary focus:ring-primary"
            />
            <span className="text-sm text-text-secondary dark:text-text-secondary">
              Auto-scroll
            </span>
          </label>
          <button
            onClick={fetchLogs}
            className="px-3 py-1.5 text-sm bg-primary hover:bg-primary-hover text-white rounded-md transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="flex-1 bg-bg-card dark:bg-bg-card-dark rounded-lg border border-border-light dark:border-border-light-dark overflow-hidden">
        <pre
          ref={preRef}
          className="h-full overflow-auto p-4 text-sm font-mono leading-relaxed"
        >
          {logs.length === 0 ? (
            <span className="text-text-muted dark:text-text-muted">No logs available</span>
          ) : (
            logs.map((line, index) => (
              <div key={index} className={getLogColor(line)}>
                {line}
              </div>
            ))
          )}
        </pre>
      </div>
    </div>
  )
}

export default LogsPage