import { Check, LoaderCircle, X } from 'lucide-react'
import { toolInfo } from './tools'

export interface TraceStep {
  name: string
  arguments: Record<string, unknown>
  status: 'running' | 'ok' | 'error'
  summary?: string
  duration_ms?: number
}

// Steps whose summary is useful to the customer ("Order #10014: shipped"). Search steps only show their
// label: which internal document matched is no business of the customer.
const SHOW_SUMMARY = new Set(['get_order_status', 'get_customer_orders', 'get_support_tickets', 'create_support_ticket', 'request_order_cancellation'])

/**
 * What the assistant did, as a short list:  ⟳ Checking your order…  →  ✓ Your order  Order #10014: shipped
 */
export function AgentTrace({ steps }: { steps: TraceStep[] }) {
  if (steps.length === 0) return null
  return (
    <ol aria-label="Steps the assistant took" className="mb-3 space-y-1.5">
      {steps.map((step, index) => {
        const info = toolInfo(step.name)
        const Icon = info.icon
        return (
          <li key={index} className="flex items-center gap-2 text-sm">
            <span
              className={`grid size-5 shrink-0 place-items-center rounded-full ${
                step.status === 'error' ? 'bg-bad-soft text-bad' : step.status === 'ok' ? 'bg-brand-soft text-brand' : 'bg-surface-2 text-muted'
              }`}
            >
              {step.status === 'running' ? (
                <LoaderCircle aria-hidden className="size-3 animate-spin" />
              ) : step.status === 'ok' ? (
                <Check aria-hidden className="size-3" />
              ) : (
                <X aria-hidden className="size-3" />
              )}
            </span>
            <Icon aria-hidden className="size-3.5 shrink-0 text-muted" />
            <span className="font-medium text-ink-2">{step.status === 'running' ? info.running : info.done}</span>
            <span className="sr-only">{step.status === 'running' ? ', in progress' : step.status === 'ok' ? ', done' : ', failed'}</span>
            {step.summary && step.status !== 'running' && SHOW_SUMMARY.has(step.name) && (
              <span className={`truncate text-xs ${step.status === 'error' ? 'text-bad' : 'text-muted'}`}>{step.summary}</span>
            )}
          </li>
        )
      })}
    </ol>
  )
}
