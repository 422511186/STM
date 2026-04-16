import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/services/api'

function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const data = await authApi.login(password)
      login(data.access_token)
      navigate('/')
    } catch (err: any) {
        if (err.response?.status === 401) {
        setError('密码错误')
      } else {
        setError('连接失败，请检查 Daemon 是否运行。')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-main dark:bg-bg-main-dark">
      <div className="bg-bg-card dark:bg-bg-card-dark p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6 text-text dark:text-text-dark">SSH Tunnel Manager</h1>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary mb-1">
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md bg-bg-input dark:bg-bg-input-dark text-text dark:text-text-dark focus:outline-none focus:border-border-focus"
              placeholder="请输入密码"
              disabled={isLoading}
              autoFocus
            />
          </div>
          {error && (
            <div className="mb-4 text-error text-sm">{error}</div>
          )}
          <button
            type="submit"
            disabled={isLoading || !password}
            className="w-full bg-primary hover:bg-primary-hover disabled:bg-primary/50 text-white py-2 px-4 rounded-md transition-colors"
          >
            {isLoading ? '登录中...' : '登录'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginPage
