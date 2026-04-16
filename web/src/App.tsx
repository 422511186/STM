import { BrowserRouter } from 'react-router-dom'
import AppRoutes from './routes'
import Toast from './components/Toast'
import { useToast } from './hooks/useToast'

function App() {
  const { toasts, removeToast } = useToast()

  return (
    <BrowserRouter>
      <AppRoutes />
      <Toast toasts={toasts} removeToast={removeToast} />
    </BrowserRouter>
  )
}

export default App
