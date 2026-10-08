import { ChartColumn } from 'lucide-react'
import { api } from '../api/endpoints'
import type { Metrics, TicketStatus } from '../api/types'
import { PageContainer } from '../components/AppShell'
import { EmptyState, ErrorState, Skeleton } from '../components/feedback'
import { PageHeader, Panel, TicketStatusBadge } from '../components/ui'
import { formatDate, formatDateTime, formatMoney, formatMs } from '../lib/format'
import { useApi } from '../lib/useApi'
import { toolInfo } from '../components/chat/tools'

export function AdminMetricsPage() {
  const state = useApi(() => api.metrics(14), [])
  return (
    <PageContainer>
      <PageHeader title="Metrics" description="Sales of the shop and usage of the AI assistant, computed with SQL from the stored orders, conversations, tool calls and tickets." />
      {state.loading && !state.data ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : state.error ? (
        <Panel>
          <ErrorState error={state.error} onRetry={state.reload} />
        </Panel>
      ) : state.data ? (
        <MetricsView m={state.data} />
      ) : null}
    </PageContainer>
  )
}

function Tile({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface px-4 py-3.5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {note && <p className="mt-0.5 text-xs text-muted">{note}</p>}
    </div>
  )
}

function MetricsView({ m }: { m: Metrics }) {
  const unresolvedShare = m.chat_turns ? Math.round((m.unresolved_questions / m.chat_turns) * 100) : 0
  const openTickets = m.tickets_by_status.open + m.tickets_by_status.in_progress
  const sales = m.sales
  return (
    <div className="space-y-6">
      <h2 className="font-display text-2xl font-bold uppercase tracking-wide">Shop</h2>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile label="Revenue (paid orders)" value={formatMoney(sales.revenue_eur)} note="Fictional money: payments are simulated" />
        <Tile label="Orders" value={sales.orders} note={`${sales.cancelled_orders} cancelled`} />
        <Tile label="Average order value" value={sales.average_order_value_eur ? formatMoney(sales.average_order_value_eur) : '—'} />
        <Tile label="Sizes with low stock" value={sales.low_stock_sizes} note="3 or fewer left" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Panel title="Orders per day (last 14 days, UTC)">
          <DailyChart days={sales.orders_per_day} caption="Orders per day" />
        </Panel>
        <Panel title="Best sellers" flush>
          <ol className="divide-y divide-line">
            {sales.top_products.map((p, i) => (
              <li key={p.name} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
                <span className="min-w-0 truncate">
                  <span className="mr-2 font-display font-bold text-muted">{i + 1}</span>
                  {p.name}
                </span>
                <span className="shrink-0 tabular-nums">{p.units} sold</span>
              </li>
            ))}
          </ol>
        </Panel>
      </div>

      <h2 className="pt-4 font-display text-2xl font-bold uppercase tracking-wide">AI assistant</h2>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile label="Conversations" value={m.total_conversations} />
        <Tile label="Questions answered" value={m.chat_turns} />
        <Tile label="Average response time" value={formatMs(m.avg_latency_ms)} note={`95th percentile ${formatMs(m.p95_latency_ms)}`} />
        <Tile label="Unresolved questions" value={m.unresolved_questions} note={m.chat_turns ? `${unresolvedShare}% of answers` : undefined} />
        <Tile label="Tool calls" value={m.tool_calls} />
        <Tile label="Knowledge-base searches" value={m.rag_searches} />
        <Tile label="Support tickets" value={m.tickets_total} note={`${openTickets} open or in progress`} />
        <Tile label="Tool errors" value={m.tool_usage.reduce((sum, t) => sum + t.errors, 0)} note="e.g. an order that isn't on the account" />
      </div>

      <Panel title="Questions answered per day (last 14 days, UTC)">
        <DailyChart days={m.chat_turns_per_day} caption="Questions answered per day" />
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Tool usage">
          {m.tool_usage.length === 0 ? (
            <EmptyState icon={ChartColumn} title="No tool calls yet" />
          ) : (
            <ToolBars usage={m.tool_usage} />
          )}
        </Panel>
        <Panel title="Tickets by status" flush>
          <ul className="divide-y divide-line">
            {(Object.keys(m.tickets_by_status) as TicketStatus[]).map((status) => (
              <li key={status} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <TicketStatusBadge status={status} />
                <span className="tabular-nums">{m.tickets_by_status[status]}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel title="Recent questions the assistant couldn't answer" flush>
        {m.recent_unresolved.length === 0 ? (
          <EmptyState icon={ChartColumn} title="Nothing unresolved">
            Questions the knowledge base couldn't answer show up here, so you know which documents are missing.
          </EmptyState>
        ) : (
          <ul className="divide-y divide-line">
            {m.recent_unresolved.map((q, i) => (
              <li key={i} className="flex flex-col gap-0.5 px-4 py-3 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6">
                <p className="text-sm text-ink">{q.question ?? '(question not found)'}</p>
                <p className="shrink-0 text-xs text-muted">
                  {formatDateTime(q.answered_at)}, conversation {q.conversation_id}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}

/** One series of bars. Hover or focus a day to see its value; the same data is in a table for screen readers. */
function DailyChart({ days, caption }: { days: Metrics['chat_turns_per_day']; caption: string }) {
  const max = Math.max(1, ...days.map((d) => d.count))
  return (
    <figure>
      <div aria-hidden className="flex h-40 items-end gap-1 border-b border-line">
        {days.map((d) => (
          <div key={d.day} className="group relative flex h-full flex-1 items-end justify-center">
            <div
              className="w-full max-w-6 rounded-t bg-brand"
              style={{ height: `${(d.count / max) * 100}%`, minHeight: d.count ? 2 : 0 }}
            />
            <span className="pointer-events-none absolute bottom-full mb-1 hidden whitespace-nowrap rounded bg-ink px-2 py-1 text-xs text-canvas group-hover:block">
              {formatDate(d.day)}: {d.count}
            </span>
          </div>
        ))}
      </div>
      <div aria-hidden className="mt-1.5 flex justify-between text-xs text-muted">
        <span>{formatDate(days[0].day)}</span>
        <span>max {max} per day</span>
        <span>{formatDate(days[days.length - 1].day)}</span>
      </div>
      <table className="sr-only">
        <caption>{caption}</caption>
        <tbody>
          {days.map((d) => (
            <tr key={d.day}>
              <th scope="row">{formatDate(d.day)}</th>
              <td>{d.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}

function ToolBars({ usage }: { usage: Metrics['tool_usage'] }) {
  const max = Math.max(...usage.map((t) => t.calls))
  return (
    <ul className="space-y-3">
      {usage.map((tool) => (
        <li key={tool.name} className="text-sm">
          <div className="mb-1 flex items-baseline justify-between gap-2">
            <span className="text-ink-2">
              {toolInfo(tool.name).done} <span className="font-mono text-xs text-muted">{tool.name}</span>
            </span>
            <span className="tabular-nums">
              {tool.calls}
              {tool.errors > 0 && <span className="text-xs text-muted"> ({tool.errors} errors)</span>}
            </span>
          </div>
          <div aria-hidden className="h-2 rounded-full bg-surface-2">
            <div className="h-2 rounded-full bg-brand" style={{ width: `${(tool.calls / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  )
}
