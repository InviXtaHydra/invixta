import { describe, expect, it } from 'vitest'
import { applyEvent, type ChatItem } from './chatState'

const empty: ChatItem = { key: 'a', role: 'assistant', content: '', steps: [], sources: [], pending: true }

describe('applyEvent', () => {
  it('builds the trace and text from streamed events, then takes the final message', () => {
    let item = applyEvent(empty, { type: 'tool_start', name: 'get_order_status', arguments: { order_id: '10012' } })
    expect(item.steps).toEqual([{ name: 'get_order_status', arguments: { order_id: '10012' }, status: 'running' }])

    item = applyEvent(item, {
      type: 'tool_end',
      name: 'get_order_status',
      arguments: { order_id: '10012' },
      status: 'ok',
      summary: 'Order #10012: shipped',
      duration_ms: 6,
    })
    expect(item.steps[0]).toMatchObject({ status: 'ok', summary: 'Order #10012: shipped' })

    item = applyEvent(applyEvent(item, { type: 'text', delta: 'Your order ' }), { type: 'text', delta: 'has shipped.' })
    expect(item.content).toBe('Your order has shipped.')

    item = applyEvent(item, {
      type: 'done',
      conversation_id: 3,
      message_id: 41,
      message: 'Your order has shipped.',
      sources: [],
      tool_calls: [{ name: 'get_order_status', arguments: {}, status: 'ok', summary: 'Order #10012: shipped', duration_ms: 6 }],
      latency_ms: 812,
    })
    expect(item).toMatchObject({ key: 'm-41', pending: false, latencyMs: 812 })
  })

  it('marks a failed tool call and a stream error', () => {
    let item = applyEvent(empty, { type: 'tool_start', name: 'get_order_status', arguments: {} })
    item = applyEvent(item, { type: 'tool_end', name: 'get_order_status', arguments: {}, status: 'error', summary: 'Order 99 not found', duration_ms: 2 })
    expect(item.steps[0].status).toBe('error')
    item = applyEvent(item, { type: 'error', detail: 'The AI assistant is busy' })
    expect(item).toMatchObject({ pending: false, error: 'The AI assistant is busy' })
  })
})
