import { CircleAlert, CircleCheck, X } from 'lucide-react'
import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { ToastContext, type ToastTone } from './useToast'

interface Toast {
  id: number
  tone: ToastTone
  message: string
}

/** Short confirmations ("Ticket #12 created") and errors, announced to screen readers. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => setToasts((all) => all.filter((t) => t.id !== id)), [])
  const show = useCallback(
    (message: string, tone: ToastTone = 'success') => {
      const id = nextId.current++
      setToasts((all) => [...all.slice(-2), { id, tone, message }])
      window.setTimeout(() => dismiss(id), tone === 'error' ? 7000 : 4000)
    },
    [dismiss],
  )

  const value = useMemo(() => show, [show])
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex flex-col items-end gap-2 sm:left-auto">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role={toast.tone === 'error' ? 'alert' : 'status'}
            className="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-lg border border-line bg-surface px-4 py-3 text-sm shadow-lg"
          >
            {toast.tone === 'success' ? (
              <CircleCheck aria-hidden className="mt-0.5 size-4 shrink-0 text-ok" />
            ) : (
              <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-bad" />
            )}
            <p className="flex-1 text-ink">{toast.message}</p>
            <button type="button" onClick={() => dismiss(toast.id)} className="text-muted hover:text-ink">
              <X aria-hidden className="size-4" />
              <span className="sr-only">Dismiss</span>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
