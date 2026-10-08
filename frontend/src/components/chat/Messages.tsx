import { Bot, RotateCcw } from 'lucide-react'
import { formatMs } from '../../lib/format'
import { Spinner } from '../feedback'
import { Button } from '../ui'
import { AgentTrace } from './AgentTrace'
import type { ChatItem } from './chatState'
import { MessageText } from './MessageText'
import { Sources } from './Sources'

export function MessageList({ items, onRetry }: { items: ChatItem[]; onRetry: (key: string) => void }) {
  return (
    <ol className="space-y-6">
      {items.map((item) => (
        <li key={item.key}>{item.role === 'user' ? <UserBubble item={item} /> : <AssistantMessage item={item} onRetry={onRetry} />}</li>
      ))}
    </ol>
  )
}

function UserBubble({ item }: { item: ChatItem }) {
  return (
    <div className="flex justify-end">
      <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand px-4 py-2.5 text-sm text-brand-ink">{item.content}</p>
    </div>
  )
}

function AssistantMessage({ item, onRetry }: { item: ChatItem; onRetry: (key: string) => void }) {
  const thinking = item.pending && !item.content && item.steps.every((s) => s.status !== 'running')
  return (
    <article className="flex gap-3" aria-busy={item.pending}>
      <span className="mt-1 grid size-7 shrink-0 place-items-center rounded-full bg-brand-soft text-brand">
        <Bot aria-hidden className="size-3.5" />
      </span>
      <div className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-line bg-surface px-4 py-3 text-sm">
        <h3 className="sr-only">Assistant</h3>
        <AgentTrace steps={item.steps} />
        {thinking && (
          <p className="flex items-center gap-2 text-muted">
            <Spinner /> Thinking…
          </p>
        )}
        {item.content && <MessageText text={item.content} />}
        {item.error && (
          <div role="alert" className="mt-2 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-bad-soft px-3 py-2 text-bad">
            <span>{item.error}</span>
            <Button variant="secondary" className="!py-1" onClick={() => onRetry(item.key)}>
              <RotateCcw aria-hidden className="size-3.5" /> Try again
            </Button>
          </div>
        )}
        <Sources sources={item.sources} />
        {item.latencyMs !== undefined && !item.pending && <p className="mt-2 text-right text-xs text-muted">Answered in {formatMs(item.latencyMs)}</p>}
      </div>
    </article>
  )
}
