// Reads the Server-Sent Events of POST /chat/stream.
//
// The browser's EventSource only supports GET without custom headers, so we use fetch() and parse
// the stream ourselves: events are separated by a blank line and each has a "data: {json}" line.
import { API_BASE, ApiError, authHeaders, errorMessage } from './client'
import type { ChatEvent } from './types'

export function parseEvents(buffer: string): { events: ChatEvent[]; rest: string } {
  const blocks = buffer.split('\n\n')
  const rest = blocks.pop() ?? '' // the last block may be incomplete
  const events: ChatEvent[] = []
  for (const block of blocks) {
    const data = block
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n')
    if (data) events.push(JSON.parse(data) as ChatEvent)
  }
  return { events, rest }
}

export async function streamChat(
  body: { conversation_id: number | null; message: string },
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', ...authHeaders() },
      body: JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.")
  }
  if (!response.ok || !response.body) throw new ApiError(response.status, await errorMessage(response))

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parsed = parseEvents(buffer)
    buffer = parsed.rest
    parsed.events.forEach(onEvent)
  }
  buffer += decoder.decode()
  parseEvents(`${buffer}\n\n`).events.forEach(onEvent)
}
