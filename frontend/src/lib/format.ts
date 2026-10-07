const money = new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR' })
const day = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
const dayTime = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

export const formatMoney = (amount: string | number) => money.format(Number(amount))

/** Dates without a time ("2026-10-09") are calendar days: don't shift them by time zone. */
export function formatDate(value: string) {
  return day.format(/^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T12:00:00`) : new Date(value))
}

export const formatDateTime = (value: string) => dayTime.format(new Date(value))

export function formatRelative(value: string, now = Date.now()) {
  const seconds = Math.round((now - new Date(value).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days} d ago`
  return formatDate(value)
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export const formatMs = (ms: number | null) => (ms === null ? '—' : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`)

export const humanize = (value: string) => (value.charAt(0).toUpperCase() + value.slice(1)).replace(/_/g, ' ')
