import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { ChatEvent } from '../api/types'
import { renderAt } from '../test/render'
import { ChatPage } from './ChatPage'

const streamChat = vi.fn()
vi.mock('../api/chatStream', () => ({ streamChat: (...args: unknown[]) => streamChat(...args) }))
vi.mock('../api/endpoints', () => ({
  api: { conversations: async () => ({ items: [], total: 0, limit: 30, offset: 0 }), conversation: vi.fn() },
}))

describe('ChatPage', () => {
  it('shows the tool the agent used, the streamed answer and its latency', async () => {
    let emit: (e: ChatEvent) => void = () => {}
    let finish: () => void = () => {}
    streamChat.mockImplementation((_body, onEvent: (e: ChatEvent) => void) => {
      emit = onEvent
      return new Promise<void>((resolve) => (finish = resolve))
    })
    renderAt(<ChatPage />, { path: '/chat', route: '/chat/:conversationId?' })

    await userEvent.type(screen.getByRole('textbox', { name: 'Message' }), 'Where is order 10012?{Enter}')
    expect(streamChat).toHaveBeenCalledWith({ conversation_id: null, message: 'Where is order 10012?' }, expect.any(Function))
    expect(screen.getByText('Where is order 10012?')).toBeInTheDocument()

    emit({ type: 'tool_start', name: 'get_order_status', arguments: { order_id: '10012' } })
    expect(await screen.findByText('Checking your order…')).toBeInTheDocument()

    emit({ type: 'tool_end', name: 'get_order_status', arguments: { order_id: '10012' }, status: 'ok', summary: 'Order #10012: shipped', duration_ms: 5 })
    emit({ type: 'text', delta: 'Your order has shipped.' })
    expect(await screen.findByText('Order database')).toBeInTheDocument()
    expect(screen.getByText('Order #10012: shipped')).toBeInTheDocument()
    expect(screen.getByText('Your order has shipped.')).toBeInTheDocument()

    emit({
      type: 'done',
      conversation_id: 5,
      message_id: 12,
      message: 'Your order has shipped.',
      sources: [{ chunk_id: 1, document_id: 2, filename: 'Shipping Policy.pdf', page_number: 1, chunk_index: 0, score: 0.81, excerpt: 'Delivery takes 1 to 3 days.' }],
      tool_calls: [{ name: 'get_order_status', arguments: { order_id: '10012' }, status: 'ok', summary: 'Order #10012: shipped', duration_ms: 5 }],
      latency_ms: 1530,
    })
    finish()
    expect(await screen.findByText('Answered in 1.5 s')).toBeInTheDocument()
    expect(screen.getByText('Shipping Policy.pdf')).toBeInTheDocument()
  })

  it('shows an error with a retry button when sending fails', async () => {
    streamChat.mockRejectedValueOnce(new Error('The AI assistant is temporarily unavailable.'))
    renderAt(<ChatPage />, { path: '/chat', route: '/chat/:conversationId?' })
    await userEvent.click(screen.getByRole('button', { name: 'What is your return policy?' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable')

    streamChat.mockResolvedValueOnce(undefined)
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    await waitFor(() => expect(streamChat).toHaveBeenLastCalledWith({ conversation_id: null, message: 'What is your return policy?' }, expect.any(Function)))
  })
})
