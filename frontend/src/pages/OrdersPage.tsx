import { ArrowLeft, Check, Package, Truck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { api } from '../api/endpoints'
import type { Order, OrderStatus } from '../api/types'
import { isStaff, useUser } from '../auth/useAuth'
import { PageContainer } from '../components/AppShell'
import { EmptyState, ErrorState, SkeletonRows } from '../components/feedback'
import { Pagination } from '../components/Pagination'
import { ProductArt } from '../components/shop/ProductArt'
import { useToast } from '../components/useToast'
import { Button, ButtonLink, Dialog, Mono, OrderStatusBadge, PageHeader, Panel, Select } from '../components/ui'
import { formatDate, formatDateTime, formatMoney, humanize } from '../lib/format'
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

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">{children}</dd>
    </div>
  )
}

const FINAL: OrderStatus[] = ['delivered', 'cancelled']

export function OrderDetailPage() {
  const { orderId } = useParams()
  const id = Number(orderId)
  const [tick, setTick] = useState(0)
  const state = useApi(() => api.order(id), [id, tick])
  const user = useUser()
  const status = state.data?.status

  // While the order is still moving (it gets shipped and delivered), refresh it.
  useEffect(() => {
    if (!status || FINAL.includes(status)) return
    const timer = window.setInterval(() => setTick((t) => t + 1), 15000)
    return () => window.clearInterval(timer)
  }, [status])

  return (
    <PageContainer>
      <Link to="/orders" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeft aria-hidden className="size-4" /> Orders
      </Link>
      {state.loading && !state.data ? (
        <Panel>
          <SkeletonRows rows={5} />
        </Panel>
      ) : state.error && !state.data ? (
        <Panel>
          <ErrorState error={state.error} onRetry={state.reload} />
        </Panel>
      ) : state.data ? (
        <OrderView order={state.data} customer={!isStaff(user)} onChanged={() => setTick((t) => t + 1)} />
      ) : null}
    </PageContainer>
  )
}

function Timeline({ order }: { order: Order }) {
  const steps =
    order.status === 'cancelled'
      ? [
          { label: 'Ordered', at: order.created_at },
          { label: 'Cancelled', at: order.cancelled_at },
        ]
      : [
          { label: 'Ordered', at: order.created_at },
          { label: 'Paid', at: order.paid_at },
          { label: 'Shipped', at: order.shipped_at },
          { label: 'Delivered', at: order.delivered_at },
        ]
  return (
    <ol className="grid grid-cols-4 gap-2" aria-label="Order progress">
      {steps.map((step) => (
        <li key={step.label} className="text-xs">
          <span className={`mb-2 block h-1.5 rounded-full ${step.at ? (order.status === 'cancelled' && step.label === 'Cancelled' ? 'bg-bad' : 'bg-brand') : 'bg-line'}`} />
          <span className={`flex items-center gap-1 ${step.at ? 'font-medium text-ink' : 'text-muted'}`}>
            {step.at && <Check aria-hidden className="size-3" />}
            {step.label}
          </span>
          {step.at && <span className="text-muted">{formatDateTime(step.at)}</span>}
        </li>
      ))}
    </ol>
  )
}

const PAYMENT_LABEL = { ideal: 'iDEAL', bancontact: 'Bancontact', card: 'Credit card', paypal: 'PayPal' }

function OrderView({ order, customer, onChanged }: { order: Order; customer: boolean; onChanged: () => void }) {
  const navigate = useNavigate()
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const [confirmCancel, setConfirmCancel] = useState(false)
  const [busy, setBusy] = useState(false)
  const justPaid = params.get('payment')
  const needsPayment = customer && order.status === 'pending' && order.payment_status !== 'paid'

  async function payAgain() {
    setBusy(true)
    try {
      const payment = await api.retryPayment(order.id)
      navigate(`/pay/${payment.id}`)
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Could not start a new payment', 'error')
      setBusy(false)
    }
  }

  async function cancel() {
    setBusy(true)
    try {
      await api.cancelOrder(order.id)
      toast(`Order #${order.id} cancelled`)
      setConfirmCancel(false)
      onChanged()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The order could not be cancelled', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {justPaid === 'paid' && (
        <div role="status" className="mb-6 flex items-start justify-between gap-4 rounded-xl border-l-4 border-accent bg-night px-5 py-4 text-night-ink">
          <div>
            <p className="font-display text-2xl font-bold uppercase tracking-wide">Thanks for your order!</p>
            <p className="text-sm text-white/80">
              Payment received. We'll ship order #{order.id} soon; this page updates by itself.
            </p>
          </div>
          <button type="button" onClick={() => setParams({}, { replace: true })} className="text-sm underline">
            Dismiss
          </button>
        </div>
      )}
      {needsPayment && (
        <div role="alert" className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-warn-soft px-5 py-4 text-warn">
          <p className="text-sm">
            {order.payment_status === 'failed' ? "The payment wasn't completed." : 'This order is waiting for payment.'} Unpaid orders are
            cancelled automatically after a while.
          </p>
          <Button onClick={() => void payAgain()} disabled={busy}>
            Pay now
          </Button>
        </div>
      )}

      <PageHeader
        title={`Order #${order.id}`}
        description={`Placed on ${formatDate(order.created_at)}`}
        actions={
          <>
            <OrderStatusBadge status={order.status} />
            {customer && (
              <ButtonLink variant="secondary" to="/chat" state={{ prompt: `I have a question about order #${order.id}: ` }}>
                Ask the assistant
              </ButtonLink>
            )}
            {order.can_cancel && (
              <Button variant="secondary" onClick={() => setConfirmCancel(true)}>
                Cancel order
              </Button>
            )}
          </>
        }
      />

      <Panel className="mb-6">
        <Timeline order={order} />
      </Panel>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Panel title="Items" flush>
          <ul className="divide-y divide-line">
            {order.items.map((item, i) => {
              const printed = [item.personalization_name, item.personalization_number].filter((x) => x !== null && x !== '').join(' ')
              return (
                <li key={i} className="flex gap-4 px-4 py-3">
                  <Link to={`/product/${item.product_slug}`} className="w-16 shrink-0 rounded-lg bg-surface-2 p-1.5">
                    <ProductArt
                      name={item.product_name}
                      category={item.category}
                      team={item.team}
                      season={item.season}
                      slug={item.product_slug}
                      view={printed ? 'back' : 'front'}
                      printName={item.personalization_name}
                      printNumber={item.personalization_number}
                    />
                  </Link>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{item.product_name}</p>
                    <p className="text-sm text-muted">
                      {item.size ? `Size ${item.size}` : ''}
                      {printed && <>, printed: <span className="font-medium text-ink-2">{printed}</span></>}
                    </p>
                  </div>
                  <div className="text-right text-sm">
                    <p className="tabular-nums">{formatMoney(item.line_total)}</p>
                    <p className="text-xs text-muted">
                      {item.quantity} × {formatMoney(item.unit_price)}
                    </p>
                  </div>
                </li>
              )
            })}
          </ul>
          <dl className="space-y-1 border-t border-line px-4 py-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted">Subtotal</dt>
              <dd className="tabular-nums">{formatMoney(order.subtotal)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Shipping ({order.shipping_method})</dt>
              <dd className="tabular-nums">{Number(order.shipping_cost) === 0 ? 'Free' : formatMoney(order.shipping_cost)}</dd>
            </div>
            <div className="flex justify-between font-semibold">
              <dt>Total</dt>
              <dd className="tabular-nums">{formatMoney(order.total_amount)}</dd>
            </div>
          </dl>
        </Panel>
        <Panel title="Delivery">
          <dl className="grid gap-4">
            {order.shipping_name && (
              <Detail label="Address">
                {order.shipping_name}
                <br />
                {order.shipping_street}
                <br />
                {order.shipping_postcode} {order.shipping_city}, {order.shipping_country}
              </Detail>
            )}
            <Detail label="Carrier">
              <span className="flex items-center gap-1.5">
                <Truck aria-hidden className="size-4 text-muted" />
                {order.carrier ?? 'Not shipped yet'}
              </span>
            </Detail>
            <Detail label="Tracking number">{order.tracking_number ? <Mono>{order.tracking_number}</Mono> : '—'}</Detail>
            <Detail label="Estimated delivery">{order.estimated_delivery ? formatDate(order.estimated_delivery) : '—'}</Detail>
            <Detail label="Payment">
              {order.payment_method ? PAYMENT_LABEL[order.payment_method] : '—'}, {humanize(order.payment_status)}
            </Detail>
          </dl>
        </Panel>
      </div>

      <Dialog open={confirmCancel} onClose={() => setConfirmCancel(false)} title={`Cancel order #${order.id}?`}>
        <p className="text-sm text-ink-2">
          The order won't be shipped{order.payment_status === 'paid' ? ' and the amount is refunded to your payment method' : ''}.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setConfirmCancel(false)}>
            Keep the order
          </Button>
          <Button variant="danger" onClick={() => void cancel()} disabled={busy}>
            Cancel order
          </Button>
        </div>
      </Dialog>
    </>
  )
}
