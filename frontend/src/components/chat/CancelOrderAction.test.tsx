import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '../toast'
import { CancelOrderActions } from './CancelOrderAction'

const cancelOrder = vi.fn(async (_orderId: number) => ({}))
vi.mock('../../api/endpoints', () => ({ api: { cancelOrder: (id: number) => cancelOrder(id) } }))

describe('CancelOrderActions', () => {
  it('only cancels after the customer confirms', async () => {
    render(
      <ToastProvider>
        <CancelOrderActions
          steps={[
            { name: 'get_order_status', arguments: { order_id: '10021' }, status: 'ok' },
            { name: 'request_order_cancellation', arguments: { order_id: '10021' }, status: 'ok', summary: 'can be cancelled' },
          ]}
        />
      </ToastProvider>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Cancel order #10021' }))
    expect(cancelOrder).not.toHaveBeenCalled() // first a confirmation question
    await userEvent.click(screen.getByRole('button', { name: 'Yes, cancel it' }))
    expect(cancelOrder).toHaveBeenCalledWith(10021)
    expect(await screen.findByText('Order #10021 is cancelled.')).toBeInTheDocument()
  })

  it('shows nothing when the order could not be cancelled', () => {
    const { container } = render(
      <CancelOrderActions steps={[{ name: 'request_order_cancellation', arguments: { order_id: '10021' }, status: 'error' }]} />,
    )
    expect(container).toBeEmptyDOMElement()
  })
})
