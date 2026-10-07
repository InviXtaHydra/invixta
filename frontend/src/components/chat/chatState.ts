// The chat's message list and how streamed events change it. Pure functions, so they're unit tested.
import type { ChatEvent, Message, Source, ToolCall } from '../../api/types'
import type { TraceStep } from './AgentTrace'

export interface ChatItem {
  key: string
  role: 'user' | 'assistant'
  content: string
  steps: TraceStep[]
  sources: Source[]
  latencyMs?: number
  pending?: boolean
  error?: string
}

const toStep = (call: ToolCall): TraceStep => ({ ...call, status: call.status === 'ok' ? 'ok' : 'error' })

export function fromMessage(message: Message): ChatItem {
  return {
    key: `m-${message.id}`,
    role: message.role === 'user' ? 'user' : 'assistant',
    content: message.content,
    steps: (message.tool_calls ?? []).map(toStep),
    sources: message.sources ?? [],
    latencyMs: message.latency_ms ?? undefined,
  }
}

/** Applies one streamed event to the assistant message that is being written. */
export function applyEvent(item: ChatItem, event: ChatEvent): ChatItem {
  switch (event.type) {
    case 'tool_start':
      return { ...item, steps: [...item.steps, { name: event.name, arguments: event.arguments, status: 'running' }] }
    case 'tool_end': {
      const steps = [...item.steps]
      const index = steps.findLastIndex((s) => s.name === event.name && s.status === 'running')
      const finished = toStep(event)
      if (index >= 0) steps[index] = finished
      else steps.push(finished)
      return { ...item, steps }
    }
    case 'text':
      return { ...item, content: item.content + event.delta }
    case 'done':
      return {
        ...item,
        key: `m-${event.message_id}`,
        content: event.message,
        sources: event.sources,
        steps: event.tool_calls.map(toStep),
        latencyMs: event.latency_ms,
        pending: false,
      }
    case 'error':
      return { ...item, pending: false, error: event.detail }
    default:
      return item
  }
}
