import { Check, LoaderCircle, X } from 'lucide-react'
import { formatMs } from '../../lib/format'
import { toolInfo } from './tools'

export interface TraceStep {
  name: string
  arguments: Record<string, unknown>
  status: 'running' | 'ok' | 'error'
  summary?: string
  duration_ms?: number
}

/**
 * The steps the agent took, as a small timeline:
 *   ⟳ Checking your order…   →   ✓ Order database   Order #10012: shipped
 */
export function AgentTrace({ steps }: { steps: TraceStep[] }) {
  if (steps.length === 0) return null
  return (
    <ol aria-label="Steps the assistant took" className="mb-3 space-y-0">
      {steps.map((step, index) => {
        const info = toolInfo(step.name)
        const Icon = info.icon
        const last = index === steps.length - 1
        return (
          <li key={index} className="relative flex gap-3 pb-3 last:pb-0">
            {!last && <span aria-hidden className="absolute left-[0.6875rem] top-6 bottom-0 w-px bg-line" />}
            <span
              className={`relative z-10 grid size-6 shrink-0 place-items-center rounded-full border ${
                step.status === 'error'
                  ? 'border-bad/30 bg-bad-soft text-bad'
                  : step.status === 'ok'
                    ? 'border-ok/25 bg-ok-soft text-ok'
                    : 'border-line bg-surface text-muted'
              }`}
            >
              {step.status === 'running' ? (
                <LoaderCircle aria-hidden className="size-3.5 animate-spin" />
              ) : step.status === 'ok' ? (
                <Check aria-hidden className="size-3.5" />
              ) : (
                <X aria-hidden className="size-3.5" />
              )}
            </span>
            <details className="group min-w-0 flex-1 text-sm">
              <summary className="flex cursor-pointer list-none flex-wrap items-baseline gap-x-2 rounded marker:hidden">
                <span className="flex items-center gap-1.5 font-medium text-ink-2">
                  <Icon aria-hidden className="size-3.5 text-muted" />
                  {step.status === 'running' ? info.running : info.done}
                  <span className="sr-only">
                    {step.status === 'running' ? ', in progress' : step.status === 'ok' ? ', done' : ', failed'}
                  </span>
                </span>
                {step.summary && (
                  <span className={`font-mono text-xs ${step.status === 'error' ? 'text-bad' : 'text-muted'}`}>{step.summary}</span>
                )}
              </summary>
              <div className="mt-1.5 rounded-md bg-surface-2 px-3 py-2 font-mono text-xs text-ink-2">
                <p>
                  {step.name}({formatArguments(step.arguments)})
                </p>
                {step.duration_ms !== undefined && <p className="mt-0.5 text-muted">took {formatMs(step.duration_ms)}</p>}
              </div>
            </details>
          </li>
        )
      })}
    </ol>
  )
}

function formatArguments(args: Record<string, unknown>) {
  return Object.entries(args)
    .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
    .join(', ')
}
