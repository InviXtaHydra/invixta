import { useState } from 'react'
import { api } from '../../api/endpoints'
import { Button } from '../ui'
import { useToast } from '../useToast'
import type { TraceStep } from './AgentTrace'

/**
 * Human in the loop: the assistant can only *offer* to cancel an order (request_order_cancellation).
 * The customer confirms here; this button calls the same endpoint as the Cancel button on the order page.
 */
export function CancelOrderActions({ steps }: { steps: TraceStep[] }) {
  const offers = steps.filter((s) => s.name === 'request_order_cancellation' && s.status === 'ok' && s.arguments.order_id)
  if (offers.length === 0) return null
  return (
    <div className="mt-3 space-y-2">
      {offers.map((offer) => (
        <CancelButton key={String(offer.arguments.order_id)} orderId={Number(String(offer.arguments.order_id).replace(/\D/g, ''))} />
      ))}
    </div>
  )
}

function CancelButton({ orderId }: { orderId: number }) {
  const toast = useToast()
  const [state, setState] = useState<'idle' | 'confirm' | 'busy' | 'done'>('idle')

  async function cancel() {
    setState('busy')
    try {
      await api.cancelOrder(orderId)
      setState('done')
      toast(`Order #${orderId} cancelled`)
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The order could not be cancelled', 'error')
      setState('idle')
    }
  }

  if (state === 'done') return <p className="rounded-lg bg-ok-soft px-3 py-2 text-sm text-ok">Order #{orderId} is cancelled.</p>
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-bad/30 bg-bad-soft/50 p-3">
      {state === 'idle' ? (
        <Button variant="danger" onClick={() => setState('confirm')}>
          Cancel order #{orderId}
        </Button>
      ) : (
        <>
          <span className="text-sm text-ink">Cancel order #{orderId}? This can't be undone.</span>
          <Button variant="danger" onClick={() => void cancel()} disabled={state === 'busy'}>
            Yes, cancel it
          </Button>
          <Button variant="secondary" onClick={() => setState('idle')} disabled={state === 'busy'}>
            Keep it
          </Button>
        </>
      )}
    </div>
  )
}
