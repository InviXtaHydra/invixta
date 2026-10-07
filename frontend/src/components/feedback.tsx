// Loading, empty and error states, used on every page so they look and behave the same.
import { CircleAlert, LoaderCircle, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from './ui'

export function Spinner({ label = 'Loading', className = '' }: { label?: string; className?: string }) {
  return (
    <span role="status" className={`inline-flex items-center gap-2 text-muted ${className}`}>
      <LoaderCircle aria-hidden className="size-4 animate-spin" />
      <span className="sr-only">{label}</span>
    </span>
  )
}

export function FullPageSpinner() {
  return (
    <div className="grid min-h-dvh place-items-center">
      <Spinner label="Loading SupportAI" />
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-md bg-line/70 ${className}`} />
}

export function SkeletonRows({ rows = 4 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading" className="space-y-3 p-4">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  )
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: LucideIcon
  title: string
  children?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <span className="mb-3 grid size-11 place-items-center rounded-full bg-brand-soft text-brand">
        <Icon aria-hidden className="size-5" />
      </span>
      <h3 className="font-medium text-ink">{title}</h3>
      {children && <p className="mt-1 max-w-sm text-sm text-muted">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center px-6 py-10 text-center">
      <CircleAlert aria-hidden className="mb-2 size-6 text-bad" />
      <p className="font-medium text-ink">This couldn't be loaded</p>
      <p className="mt-1 max-w-sm text-sm text-muted">{error.message}</p>
      {onRetry && (
        <Button variant="secondary" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}
