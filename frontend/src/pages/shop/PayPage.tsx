import { Lock, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api } from '../../api/endpoints'
import type { PaymentMethod } from '../../api/types'
import { ErrorState, Spinner } from '../../components/feedback'
import { Button } from '../../components/ui'
import { formatMoney } from '../../lib/format'
import { useApi } from '../../lib/useApi'

const LABEL: Record<PaymentMethod, string> = { ideal: 'iDEAL', bancontact: 'Bancontact', card: 'Credit card', paypal: 'PayPal' }

/**
 * The payment step. There is no payment provider connected yet: this page runs in test mode, where
 * "Pay" approves the payment (POST /payments/{id}/complete) the way a provider such as Mollie or
 * Stripe would report back. Connecting a real provider replaces this page with the provider's own.
 */
export function PayPage() {
  const { paymentId } = useParams()
  const id = Number(paymentId)
  const navigate = useNavigate()
  const payment = useApi(() => api.payment(id), [id])
  const [busy, setBusy] = useState<'approve' | 'decline' | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function decide(outcome: 'approve' | 'decline') {
    setBusy(outcome)
    setError(null)
    try {
      const result = await api.completePayment(id, outcome)
      navigate(`/orders/${result.order_id}?payment=${result.status}`, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
      setBusy(null)
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center bg-surface-2 px-4 py-10">
      <div className="w-full max-w-sm overflow-hidden rounded-2xl bg-surface shadow-xl ring-1 ring-line">
        <div className="flex items-center justify-between border-b-2 border-accent bg-night px-5 py-3 text-night-ink">
          <span className="flex items-center gap-2 font-semibold">
            <ShieldCheck aria-hidden className="size-5 text-brand" /> Invixta Pay
          </span>
          <span className="rounded bg-white/15 px-2 py-0.5 text-xs" title="No payment provider is connected yet">
            Test mode
          </span>
        </div>
        <div className="p-6">
          {payment.loading ? (
            <div className="py-8 text-center">
              <Spinner label="Loading payment" />
            </div>
          ) : payment.error || !payment.data ? (
            <ErrorState error={payment.error ?? new Error('Payment not found')} />
          ) : payment.data.status !== 'pending' ? (
            <div className="text-center">
              <p className="font-medium">This payment is already {payment.data.status}.</p>
              <Link to={`/orders/${payment.data.order_id}`} className="mt-3 inline-block text-sm font-medium text-brand underline">
                Back to your order
              </Link>
            </div>
          ) : (
            <>
              <p className="text-sm text-muted">Order #{payment.data.order_id}</p>
              <p className="mt-1 text-4xl font-bold tabular-nums">{formatMoney(payment.data.amount)}</p>
              <p className="mt-1 text-sm text-muted">with {LABEL[payment.data.method]}</p>
              {error && (
                <p role="alert" className="mt-4 text-sm text-bad">
                  {error}
                </p>
              )}
              <div className="mt-6 grid gap-2">
                <Button onClick={() => void decide('approve')} disabled={busy !== null} className="!py-3">
                  <Lock aria-hidden className="size-4" />
                  {busy === 'approve' ? 'Paying…' : `Pay ${formatMoney(payment.data.amount)}`}
                </Button>
                <Button variant="secondary" onClick={() => void decide('decline')} disabled={busy !== null} className="!py-3">
                  {busy === 'decline' ? 'Cancelling…' : 'Cancel payment'}
                </Button>
              </div>
              <p className="mt-4 text-center text-xs text-muted">You can pay again later from your order page.</p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
