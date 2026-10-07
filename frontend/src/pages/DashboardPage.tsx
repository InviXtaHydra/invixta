import { ArrowUpRight, Bot, LifeBuoy, MessageSquare, Package, Send } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { api } from '../api/endpoints'
import type { User } from '../api/types'
import { isStaff, useUser } from '../auth/useAuth'
import { PageContainer } from '../components/AppShell'
import { EmptyState, ErrorState, Skeleton, SkeletonRows } from '../components/feedback'
import { Button, Mono, OrderStatusBadge, PageHeader, Panel, PriorityBadge, TicketStatusBadge } from '../components/ui'
import { formatDate, formatMoney, formatRelative } from '../lib/format'
import { useApi } from '../lib/useApi'

export function DashboardPage() {
  const user = useUser()
  return <PageContainer>{isStaff(user) ? <StaffDashboard user={user} /> : <CustomerDashboard user={user} />}</PageContainer>
}

function Stat({ label, value, to, loading }: { label: string; value: number | undefined; to: string; loading: boolean }) {
  return (
    <Link to={to} className="group rounded-xl border border-line bg-surface px-4 py-3.5 hover:border-line-strong">
      <span className="flex items-center justify-between text-sm text-muted">
        {label}
        <ArrowUpRight aria-hidden className="size-4 opacity-0 transition-opacity group-hover:opacity-100" />
      </span>
      {loading ? <Skeleton className="mt-2 h-8 w-14" /> : <span className="mt-1 block text-3xl font-semibold tabular-nums">{value ?? '—'}</span>}
    </Link>
  )
}

function useCounts() {
  return useApi(async () => {
    const [orders, open, inProgress, conversations] = await Promise.all([
      api.orders({ limit: 5 }),
      api.tickets({ status: 'open', limit: 5 }),
      api.tickets({ status: 'in_progress', limit: 5 }),
      api.conversations({ limit: 5 }),
    ])
    return { orders, open, inProgress, conversations }
  }, [])
}

function RecentOrders({ state }: { state: ReturnType<typeof useCounts> }) {
  const orders = state.data?.orders.items
  return (
    <Panel title="Recent orders" flush action={<Link to="/orders" className="text-sm font-medium text-brand hover:underline">View all</Link>}>
      {state.loading ? (
        <SkeletonRows rows={4} />
      ) : state.error ? (
        <ErrorState error={state.error} onRetry={state.reload} />
      ) : !orders?.length ? (
        <EmptyState icon={Package} title="No orders yet" />
      ) : (
        <ul className="divide-y divide-line">
          {orders.map((order) => (
            <li key={order.id}>
              <Link to={`/orders/${order.id}`} className="flex items-center gap-4 px-4 py-3 hover:bg-surface-2">
                <Mono className="font-medium text-ink">#{order.id}</Mono>
                <span className="hidden text-sm text-muted sm:inline">{formatDate(order.created_at)}</span>
                <span className="ml-auto text-sm tabular-nums">{formatMoney(order.total_amount)}</span>
                <span className="w-24 text-right">
                  <OrderStatusBadge status={order.status} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}

function CustomerDashboard({ user }: { user: User }) {
  const state = useCounts()
  const navigate = useNavigate()
  const [question, setQuestion] = useState('')
  const openTickets = state.data ? state.data.open.total + state.data.inProgress.total : undefined

  function ask(event: FormEvent) {
    event.preventDefault()
    if (question.trim()) navigate('/chat', { state: { prompt: question.trim() } })
  }

  return (
    <>
      <PageHeader title={`Welcome back${user.name ? `, ${user.name.split(' ')[0]}` : ''}`} description="Your orders, tickets and conversations at a glance." />

      <form onSubmit={ask} className="mb-6 rounded-xl border border-brand/25 bg-brand-soft/60 p-4 sm:p-5">
        <label htmlFor="quick-ask" className="flex items-center gap-2 font-medium text-ink">
          <Bot aria-hidden className="size-4 text-brand" /> Ask the AI assistant
        </label>
        <p className="mt-0.5 text-sm text-muted">It checks your orders and our policies before it answers.</p>
        <div className="mt-3 flex gap-2">
          <input
            id="quick-ask"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. When will order #10012 arrive?"
            className="min-w-0 flex-1 rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm focus:border-brand focus:outline-none"
          />
          <Button type="submit" disabled={!question.trim()}>
            <Send aria-hidden className="size-4" /> Ask
          </Button>
        </div>
      </form>

      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Stat label="Orders" value={state.data?.orders.total} to="/orders" loading={state.loading} />
        <Stat label="Open tickets" value={openTickets} to="/tickets" loading={state.loading} />
        <Stat label="Conversations" value={state.data?.conversations.total} to="/chat" loading={state.loading} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <RecentOrders state={state} />
        <Panel title="Recent conversations" flush action={<Link to="/chat" className="text-sm font-medium text-brand hover:underline">Open chat</Link>}>
          {state.loading ? (
            <SkeletonRows rows={3} />
          ) : !state.data?.conversations.items.length ? (
            <EmptyState icon={MessageSquare} title="No conversations yet">
              Ask the assistant something to get started.
            </EmptyState>
          ) : (
            <ul className="divide-y divide-line">
              {state.data.conversations.items.map((c) => (
                <li key={c.id}>
                  <Link to={`/chat/${c.id}`} className="block px-4 py-3 hover:bg-surface-2">
                    <span className="block truncate text-sm font-medium">{c.title ?? `Conversation #${c.id}`}</span>
                    <span className="text-xs text-muted">
                      {formatRelative(c.updated_at)}, {c.message_count} messages
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </>
  )
}

function StaffDashboard({ user }: { user: User }) {
  const state = useCounts()
  const queue = useApi(() => api.tickets({ limit: 8 }), [])
  return (
    <>
      <PageHeader
        title="Support overview"
        description={user.role === 'ADMIN' ? 'All customers. Usage of the AI assistant is under Metrics.' : 'All customers.'}
      />
      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Stat label="Open tickets" value={state.data?.open.total} to="/tickets?status=open" loading={state.loading} />
        <Stat label="In progress" value={state.data?.inProgress.total} to="/tickets?status=in_progress" loading={state.loading} />
        <Stat label="Orders" value={state.data?.orders.total} to="/orders" loading={state.loading} />
      </div>
      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <Panel title="Latest tickets" flush action={<Link to="/tickets" className="text-sm font-medium text-brand hover:underline">View all</Link>}>
          {queue.loading ? (
            <SkeletonRows rows={5} />
          ) : queue.error ? (
            <ErrorState error={queue.error} onRetry={queue.reload} />
          ) : !queue.data?.items.length ? (
            <EmptyState icon={LifeBuoy} title="No tickets" />
          ) : (
            <ul className="divide-y divide-line">
              {queue.data.items.map((t) => (
                <li key={t.id}>
                  <Link to={`/tickets/${t.id}`} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 hover:bg-surface-2">
                    <span className="min-w-0 flex-1 truncate text-sm font-medium">{t.subject}</span>
                    <PriorityBadge priority={t.priority} />
                    <TicketStatusBadge status={t.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <RecentOrders state={state} />
      </div>
    </>
  )
}
