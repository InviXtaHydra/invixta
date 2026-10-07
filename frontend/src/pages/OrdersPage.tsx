import { ArrowLeft, Check, Package, Truck } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router'
import { api } from '../api/endpoints'
import type { Order, OrderStatus } from '../api/types'
import { isStaff, useUser } from '../auth/useAuth'
import { PageContainer } from '../components/AppShell'
import { EmptyState, ErrorState, SkeletonRows } from '../components/feedback'
import { Pagination } from '../components/Pagination'
import { ButtonLink, Mono, OrderStatusBadge, PageHeader, Panel, Select } from '../components/ui'
import { formatDate, formatMoney, humanize } from '../lib/format'
import { useApi } from '../lib/useApi'

const STATUSES: OrderStatus[] = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
const PAGE_SIZE = 10

export function OrdersPage() {
  const user = useUser()
  const [params, setParams] = useSearchParams()
  const status = (params.get('status') ?? '') as OrderStatus | ''
  const offset = Number(params.get('offset') ?? 0)
  const state = useApi(() => api.orders({ status, limit: PAGE_SIZE, offset }), [status, offset])

  const update = (next: Record<string, string>) => setParams({ ...Object.fromEntries(params), ...next }, { replace: true })

  return (
    <PageContainer>
      <PageHeader
        title="Orders"
        description={isStaff(user) ? 'Orders of all customers.' : 'Everything you ordered, with delivery details.'}
        actions={
          <div className="w-44">
            <label htmlFor="status-filter" className="sr-only">
              Filter by status
            </label>
            <Select id="status-filter" value={status} onChange={(e) => update({ status: e.target.value, offset: '0' })}>
              <option value="">All statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {humanize(s)}
                </option>
              ))}
            </Select>
          </div>
        }
      />
      <Panel flush>
        {state.loading && !state.data ? (
          <SkeletonRows rows={6} />
        ) : state.error ? (
          <ErrorState error={state.error} onRetry={state.reload} />
        ) : !state.data?.items.length ? (
          <EmptyState icon={Package} title={status ? `No ${humanize(status).toLowerCase()} orders` : 'No orders yet'}>
            {status ? 'Try another status filter.' : 'Orders you place will show up here.'}
          </EmptyState>
        ) : (
          <div aria-busy={state.loading} className={state.loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <caption className="sr-only">Orders</caption>
                <thead className="border-b border-line text-xs text-muted">
                  <tr>
                    <th scope="col" className="px-4 py-2.5 font-medium">Order</th>
                    <th scope="col" className="px-4 py-2.5 font-medium">Date</th>
                    <th scope="col" className="px-4 py-2.5 font-medium">Status</th>
                    <th scope="col" className="hidden px-4 py-2.5 font-medium md:table-cell">Carrier</th>
                    <th scope="col" className="hidden px-4 py-2.5 font-medium md:table-cell">Estimated delivery</th>
                    <th scope="col" className="px-4 py-2.5 text-right font-medium">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {state.data.items.map((order) => (
                    <tr key={order.id} className="relative hover:bg-surface-2">
                      <td className="px-4 py-3">
                        <Link to={`/orders/${order.id}`} className="font-mono font-medium text-ink after:absolute after:inset-0">
                          #{order.id}
                        </Link>
                        <span className="block text-xs text-muted">
                          {order.item_count} {order.item_count === 1 ? 'item' : 'items'}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-ink-2">{formatDate(order.created_at)}</td>
                      <td className="px-4 py-3">
                        <OrderStatusBadge status={order.status} />
                      </td>
                      <td className="hidden px-4 py-3 text-ink-2 md:table-cell">{order.carrier ?? '—'}</td>
                      <td className="hidden px-4 py-3 text-ink-2 md:table-cell">
                        {order.estimated_delivery ? formatDate(order.estimated_delivery) : '—'}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums">{formatMoney(order.total_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination total={state.data.total} limit={PAGE_SIZE} offset={offset} onChange={(o) => update({ offset: String(o) })} />
          </div>
        )}
      </Panel>
    </PageContainer>
  )
}

const PROGRESS: OrderStatus[] = ['pending', 'processing', 'shipped', 'delivered']

function DeliveryProgress({ status }: { status: OrderStatus }) {
  if (status === 'cancelled') return <p className="text-sm text-bad">This order was cancelled.</p>
  const current = PROGRESS.indexOf(status)
  return (
    <ol className="grid grid-cols-4 gap-2" aria-label="Delivery progress">
      {PROGRESS.map((step, index) => {
        const reached = index <= current
        return (
          <li key={step} className="text-xs" aria-current={index === current ? 'step' : undefined}>
            <span className={`mb-2 block h-1.5 rounded-full ${reached ? 'bg-brand' : 'bg-line'}`} />
            <span className={`flex items-center gap-1 ${reached ? 'font-medium text-ink' : 'text-muted'}`}>
              {index < current && <Check aria-hidden className="size-3" />}
              {humanize(step)}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">{children}</dd>
    </div>
  )
}

export function OrderDetailPage() {
  const { orderId } = useParams()
  const id = Number(orderId)
  const state = useApi(() => api.order(id), [id])
  const user = useUser()

  return (
    <PageContainer>
      <Link to="/orders" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeft aria-hidden className="size-4" /> Orders
      </Link>
      {state.loading ? (
        <Panel>
          <SkeletonRows rows={5} />
        </Panel>
      ) : state.error ? (
        <Panel>
          <ErrorState error={state.error} onRetry={state.reload} />
        </Panel>
      ) : state.data ? (
        <OrderView order={state.data} canAsk={!isStaff(user)} />
      ) : null}
    </PageContainer>
  )
}

function OrderView({ order, canAsk }: { order: Order; canAsk: boolean }) {
  return (
    <>
      <PageHeader
        title={`Order #${order.id}`}
        description={`Placed on ${formatDate(order.created_at)}`}
        actions={
          <>
            <OrderStatusBadge status={order.status} />
            {canAsk && (
              <ButtonLink variant="secondary" to="/chat" state={{ prompt: `I have a question about order #${order.id}.` }}>
                Ask the assistant about this order
              </ButtonLink>
            )}
          </>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Panel title="Items" flush>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Items in this order</caption>
            <thead className="border-b border-line text-xs text-muted">
              <tr>
                <th scope="col" className="px-4 py-2.5 font-medium">Product</th>
                <th scope="col" className="px-4 py-2.5 text-right font-medium">Qty</th>
                <th scope="col" className="hidden px-4 py-2.5 text-right font-medium sm:table-cell">Price</th>
                <th scope="col" className="px-4 py-2.5 text-right font-medium">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {order.items.map((item) => (
                <tr key={item.product_id}>
                  <td className="px-4 py-3 text-ink">{item.product_name}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{item.quantity}</td>
                  <td className="hidden px-4 py-3 text-right tabular-nums text-ink-2 sm:table-cell">{formatMoney(item.unit_price)}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatMoney(item.line_total)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t border-line-strong">
              <tr>
                <th scope="row" colSpan={2} className="px-4 py-3 text-left font-medium">
                  Order total
                </th>
                <td className="hidden sm:table-cell" />
                <td className="px-4 py-3 text-right font-semibold tabular-nums">{formatMoney(order.total_amount)}</td>
              </tr>
            </tfoot>
          </table>
        </Panel>
        <Panel title="Delivery">
          <DeliveryProgress status={order.status} />
          <dl className="mt-5 grid gap-4">
            <Detail label="Carrier">
              <span className="flex items-center gap-1.5">
                <Truck aria-hidden className="size-4 text-muted" />
                {order.carrier ?? 'Not shipped yet'}
              </span>
            </Detail>
            <Detail label="Tracking number">{order.tracking_number ? <Mono>{order.tracking_number}</Mono> : '—'}</Detail>
            <Detail label="Estimated delivery">{order.estimated_delivery ? formatDate(order.estimated_delivery) : '—'}</Detail>
            <Detail label="Last update">{formatDate(order.updated_at)}</Detail>
          </dl>
        </Panel>
      </div>
    </>
  )
}
