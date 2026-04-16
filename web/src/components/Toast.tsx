import { useEffect } from 'react'
import type { Toast as ToastType } from '@/hooks/useToast'

interface ToastProps {
  toasts: ToastType[]
  removeToast: (id: string) => void
}

const variantStyles = {
  success: {
    bg: 'bg-success/10',
    border: 'border-success/30',
    icon: '✓',
    iconColor: 'text-success',
    dark: {
      bg: 'dark:bg-success/10',
      border: 'dark:border-success/30',
    }
  },
  error: {
    bg: 'bg-error/10',
    border: 'border-error/30',
    icon: '✕',
    iconColor: 'text-error',
    dark: {
      bg: 'dark:bg-error/10',
      border: 'dark:border-error/30',
    }
  },
  warning: {
    bg: 'bg-warning/10',
    border: 'border-warning/30',
    icon: '⚠',
    iconColor: 'text-warning',
    dark: {
      bg: 'dark:bg-warning/10',
      border: 'dark:border-warning/30',
    }
  },
  info: {
    bg: 'bg-primary/10',
    border: 'border-primary/30',
    icon: 'ℹ',
    iconColor: 'text-primary',
    dark: {
      bg: 'dark:bg-primary/10',
      border: 'dark:border-primary/30',
    }
  }
}

function ToastItem({ toast, onClose }: { toast: ToastType; onClose: () => void }) {
  const style = variantStyles[toast.type]

  useEffect(() => {
    const timer = setTimeout(onClose, 3000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div
      className={`
        flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg
        ${style.bg} ${style.border}
        dark:${style.bg} dark:${style.border}
        animate-in slide-in-from-right fade-in duration-300
      `}
    >
      <span className={`text-lg ${style.iconColor}`}>{style.icon}</span>
      <span className="text-sm text-text dark:text-text-dark flex-1">{toast.message}</span>
      <button
        onClick={onClose}
        className="text-text-muted hover:text-text dark:text-text-muted dark:hover:text-text-dark text-xs"
      >
        ✕
      </button>
    </div>
  )
}

export default function Toast({ toasts, removeToast }: ToastProps) {
  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  )
}