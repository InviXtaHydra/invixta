import { CircleAlert, ShieldCheck } from 'lucide-react'
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
 * TestPay: a stand-in for a payment provider's page (iDEAL, Bancontact, …). In a real shop the
 * customer would log in to their bank here; in Kopbal you simply choose the outcome.
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
    <div className="grid min-h-dvh place-items-center bg-[#eef1f5] px-4 py-10 text-[#1b2430]">
      <div className="w-full max-w-sm overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-black/5">
        <div className="flex items-center justify-between bg-[#1b2430] px-5 py-3 text-white">
          <span className="flex items-center gap-2 font-semibold">
            <ShieldCheck aria-hidden className="size-5 text-[#7dd3fc]" /> TestPay
          </span>
          <span className="rounded bg-white/15 px-2 py-0.5 text-xs">Simulation</span>
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
              <Link to={`/orders/${payment.data.order_id}`} className="mt-3 inline-block text-sm font-medium text-[#0f5132] underline">
                Back to your order
              </Link>
            </div>
          ) : (
            <>
              <p className="text-sm text-[#5b6675]">Pay to</p>
              <p className="font-semibold">Kopbal (order #{payment.data.order_id})</p>
              <p className="mt-4 text-sm text-[#5b6675]">Amount</p>
              <p className="text-4xl font-bold tabular-nums">{formatMoney(payment.data.amount)}</p>
              <p className="mt-1 text-sm text-[#5b6675]">with {LABEL[payment.data.method]}</p>

              <div className="mt-5 flex gap-2 rounded-lg bg-[#fff8e1] p-3 text-xs text-[#6b5300]">
                <CircleAlert aria-hidden className="size-4 shrink-0" />
                This is a simulated payment page. No bank is involved and no money moves: choose what the bank would answer.
              </div>
              {error && (
                <p role="alert" className="mt-3 text-sm text-[#b42318]">
                  {error}
                </p>
              )}
              <div className="mt-5 grid gap-2">
                <Button onClick={() => void decide('approve')} disabled={busy !== null} className="!bg-[#0f5132] !py-3 !text-white">
                  {busy === 'approve' ? 'Approving…' : 'Approve payment'}
                </Button>
                <Button variant="secondary" onClick={() => void decide('decline')} disabled={busy !== null} className="!py-3">
                  {busy === 'decline' ? 'Declining…' : 'Decline payment'}
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
