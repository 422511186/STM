import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from '@/components/Layout'
import LoginPage from '@/pages/LoginPage'
import TunnelListPage from '@/pages/TunnelListPage'
import LogsPage from '@/pages/LogsPage'
import { useAuthStore } from '@/stores/authStore'

function AppRoutes() {
  const { isAuthenticated, init } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    init()
  }, [init])

  useEffect(() => {
    if (!isAuthenticated && window.location.pathname !== '/login') {
      navigate('/login')
    }
  }, [isAuthenticated, navigate])

  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
        }
      />
      <Route
        path="/"
        element={
          isAuthenticated ? <Layout /> : <Navigate to="/login" replace />
        }
      >
        <Route index element={<TunnelListPage />} />
        <Route path="logs" element={<LogsPage />} />
      </Route>
    </Routes>
  )
}

export default AppRoutes
