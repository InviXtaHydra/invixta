// Small, accessible building blocks. Styling lives here so pages stay readable.
import { X } from 'lucide-react'
import {
  useEffect,
  useId,
  useRef,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react'
import { Link, type LinkProps } from 'react-router'
import type { OrderStatus, TicketPriority, TicketStatus } from '../api/types'
import { humanize } from '../lib/format'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

const variants: Record<Variant, string> = {
  primary: 'bg-brand text-brand-ink hover:bg-brand-hover',
  secondary: 'border border-line-strong bg-surface text-ink hover:bg-surface-2',
  ghost: 'text-ink-2 hover:bg-surface-2 hover:text-ink',
  danger: 'bg-bad text-white hover:opacity-90',
}

const buttonBase =
  'inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-55'

export function Button({
  variant = 'primary',
  className = '',
  type = 'button',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button type={type} className={`${buttonBase} ${variants[variant]} ${className}`} {...props} />
}

export function ButtonLink({ variant = 'primary', className = '', ...props }: LinkProps & { variant?: Variant }) {
  return <Link className={`${buttonBase} ${variants[variant]} ${className}`} {...props} />
}

const control =
  'w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink placeholder:text-muted/80 focus:border-brand focus:outline-none focus-visible:outline-2 aria-invalid:border-bad'

/** A label + control + optional hint/error, wired together with ids for screen readers. */
export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string
  hint?: string
  error?: string
  children: (props: { id: string; 'aria-describedby'?: string; 'aria-invalid'?: boolean }) => ReactNode
}) {
  const id = useId()
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-ink-2">
        {label}
      </label>
      {children({ id, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined })}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-bad">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="text-xs text-muted">
            {hint}
          </p>
        )
      )}
    </div>
  )
}

export function Input({ className = '', ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${control} ${className}`} {...props} />
}

export function Textarea({ className = '', ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${control} ${className}`} {...props} />
}

export function Select({ className = '', ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`${control} pr-8 ${className}`} {...props} />
}

type Tone = 'neutral' | 'brand' | 'ok' | 'warn' | 'bad' | 'info'

const tones: Record<Tone, string> = {
  neutral: 'bg-surface-2 text-ink-2 border-line',
  brand: 'bg-brand-soft text-brand border-transparent',
  ok: 'bg-ok-soft text-ok border-transparent',
  warn: 'bg-warn-soft text-warn border-transparent',
  bad: 'bg-bad-soft text-bad border-transparent',
  info: 'bg-info-soft text-info border-transparent',
}

/** Colored label that always includes text, so meaning never depends on color alone. */
export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>
      <span aria-hidden className="size-1.5 rounded-full bg-current" />
      {children}
    </span>
  )
}

const orderTones: Record<OrderStatus, Tone> = {
  pending: 'neutral',
  processing: 'info',
  shipped: 'brand',
  delivered: 'ok',
  cancelled: 'bad',
}
const ticketTones: Record<TicketStatus, Tone> = { open: 'warn', in_progress: 'info', resolved: 'ok', closed: 'neutral' }
const priorityTones: Record<TicketPriority, Tone> = { low: 'neutral', medium: 'info', high: 'warn', urgent: 'bad' }

export const OrderStatusBadge = ({ status }: { status: OrderStatus }) => <Badge tone={orderTones[status]}>{humanize(status)}</Badge>
export const TicketStatusBadge = ({ status }: { status: TicketStatus }) => <Badge tone={ticketTones[status]}>{humanize(status)}</Badge>
export const PriorityBadge = ({ priority }: { priority: TicketPriority }) => (
  <Badge tone={priorityTones[priority]}>{humanize(priority)} priority</Badge>
)

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  )
}

/** A bordered surface. `title` adds a header row; `flush` removes the padding (for tables/lists). */
export function Panel({
  title,
  action,
  flush = false,
  className = '',
  children,
}: {
  title?: string
  action?: ReactNode
  flush?: boolean
  className?: string
  children: ReactNode
}) {
  return (
    <section className={`rounded-xl border border-line bg-surface ${className}`}>
      {title && (
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          {action}
        </div>
      )}
      <div className={flush ? '' : 'p-4'}>{children}</div>
    </section>
  )
}

/** Modal dialog on the native <dialog> element: focus trapping, Escape and backdrop come for free. */
export function Dialog({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal?.()
    if (!open && dialog.open) dialog.close?.()
  }, [open])

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(event) => event.target === ref.current && onClose()}
      className="m-auto w-[min(32rem,calc(100vw-2rem))] rounded-xl border border-line bg-surface p-0 text-ink shadow-xl backdrop:bg-black/40"
    >
      {open && (
        <div className="p-5">
          <div className="mb-4 flex items-start justify-between gap-4">
            <h2 id={titleId} className="text-lg font-semibold">
              {title}
            </h2>
            <button type="button" onClick={onClose} className="rounded-md p-1 text-muted hover:bg-surface-2 hover:text-ink">
              <X aria-hidden className="size-4" />
              <span className="sr-only">Close</span>
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  )
}

export function Mono({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <span className={`font-mono text-[0.92em] ${className}`}>{children}</span>
}
