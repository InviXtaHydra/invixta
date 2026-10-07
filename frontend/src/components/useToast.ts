import { createContext, useContext } from 'react'

export type ToastTone = 'success' | 'error'

export const ToastContext = createContext<((message: string, tone?: ToastTone) => void) | null>(null)

/** toast("Ticket #12 created") or toast("Upload failed", "error") */
export function useToast() {
  const show = useContext(ToastContext)
  if (!show) throw new Error('useToast must be used inside <ToastProvider>')
  return show
}
