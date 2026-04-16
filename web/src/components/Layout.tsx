import { useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { authApi, configApi } from '@/services/api'

function Layout() {
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } finally {
      logout()
      navigate('/login')
    }
  }

  const handleExport = async () => {
    try {
      const response = await configApi.exportConfig()
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'config.yaml')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
    }
  }

  const handleImportClick = () => {
    setImportError(null)
    setShowImportDialog(true)
  }

  const handleImportConfirm = async (file: File) => {
    try {
      setImportError(null)
      await configApi.importConfig(file)
      setShowImportDialog(false)
      window.location.reload()
    } catch (err: any) {
      setImportError(err.response?.data?.detail || 'Import failed')
    }
  }

  const handleImportCancel = () => {
    setShowImportDialog(false)
    setImportError(null)
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-[230px] bg-bg-sidebar border-r border-border-light dark:bg-bg-sidebar-dark dark:border-border-light-dark flex flex-col">
        <div className="p-4">
          <h1 className="text-lg font-bold text-text dark:text-text-dark">SSH Tunnel Manager</h1>
        </div>
        <nav className="mt-4 flex-1">
          <a
            href="/"
            className="block px-4 py-2 text-text-secondary hover:bg-bg-hover dark:text-text-secondary dark:hover:bg-bg-hover-dark"
          >
            隧道列表
          </a>
          <a
            href="/logs"
            className="block px-4 py-2 text-text-secondary hover:bg-bg-hover dark:text-text-secondary dark:hover:bg-bg-hover-dark"
          >
            日志
          </a>
        </nav>
        <div className="p-4 border-t border-border-light dark:border-border-light-dark space-y-2">
          <button
            onClick={handleExport}
            className="w-full px-4 py-2 text-sm text-text-secondary hover:bg-bg-hover dark:text-text-secondary dark:hover:bg-bg-hover-dark rounded-md text-left"
          >
            导出配置
          </button>
          <button
            onClick={handleImportClick}
            className="w-full px-4 py-2 text-sm text-text-secondary hover:bg-bg-hover dark:text-text-secondary dark:hover:bg-bg-hover-dark rounded-md text-left"
          >
            导入配置
          </button>
          <button
            onClick={handleLogout}
            className="w-full px-4 py-2 text-sm text-text-secondary hover:bg-bg-hover dark:text-text-secondary dark:hover:bg-bg-hover-dark rounded-md text-left"
          >
            退出登录
          </button>
        </div>
      </aside>

      {showImportDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-bg-primary dark:bg-bg-primary-dark rounded-lg shadow-xl p-6 w-[400px] border border-border-light dark:border-border-light-dark">
            <h2 className="text-lg font-semibold text-text dark:text-text-dark mb-4">导入配置</h2>
            <p className="text-sm text-text-secondary dark:text-text-secondary mb-4">
              这将覆盖您当前的配置。确定要继续吗？
            </p>
            {importError && (
              <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-md">
                <p className="text-sm text-error">{importError}</p>
              </div>
            )}
            <div className="flex gap-3 justify-end">
              <button
                onClick={handleImportCancel}
                className="px-4 py-2 text-sm text-text-secondary hover:bg-bg-hover dark:text-text-secondary dark:hover:bg-bg-hover-dark rounded-md"
              >
                取消
              </button>
              <label className="px-4 py-2 text-sm bg-primary hover:bg-primary-hover text-white rounded-md cursor-pointer">
                选择文件
                <input
                  type="file"
                  accept=".yaml,.yml"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) {
                      handleImportConfirm(file)
                    }
                  }}
                />
              </label>
            </div>
          </div>
        </div>
      )}

      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}

export default Layout