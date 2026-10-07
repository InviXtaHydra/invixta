import { describe, expect, it, vi } from 'vitest'
import { parseEvents, streamChat } from './chatStream'
import type { ChatEvent } from './types'

describe('parseEvents', () => {
  it('parses complete events and keeps an incomplete one for later', () => {
    const { events, rest } = parseEvents('data: {"type":"start","conversation_id":4}\n\ndata: {"type":"text","delta":"Hel')
    expect(events).toEqual([{ type: 'start', conversation_id: 4 }])
    expect(rest).toBe('data: {"type":"text","delta":"Hel')
  })
})

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder()
  const body = new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

describe('streamChat', () => {
  it('delivers events in order, even when they arrive split across network chunks', async () => {
    const chunks = [
      'data: {"type":"start","conversation_id":7}\n\ndata: {"type":"tool_st',
      'art","name":"get_order_status","arguments":{"order_id":"10012"}}\n\n',
      'data: {"type":"text","delta":"Shipped"}\n\n',
    ]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse(chunks)))
    const received: ChatEvent[] = []
    await streamChat({ conversation_id: null, message: 'Where is 10012?' }, (e) => received.push(e))
    expect(received.map((e) => e.type)).toEqual(['start', 'tool_start', 'text'])
    vi.unstubAllGlobals()
  })

  it('turns an HTTP error into an ApiError with the server message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Conversation 9 not found' }), { status: 404 })))
    await expect(streamChat({ conversation_id: 9, message: 'Hi' }, () => {})).rejects.toMatchObject({ status: 404, message: 'Conversation 9 not found' })
    vi.unstubAllGlobals()
  })
})
