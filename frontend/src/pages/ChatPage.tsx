import { Bot, History, MessageSquare, Plus, Send } from 'lucide-react'
import { useEffect, useEffectEvent, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { api } from '../api/endpoints'
import type { ConversationSummary, Page } from '../api/types'
import { useUser } from '../auth/useAuth'
import { MessageList } from '../components/chat/Messages'
import { useChatSession } from '../components/chat/useChatSession'
import { ErrorState, Spinner } from '../components/feedback'
import { Button, Dialog } from '../components/ui'
import { formatRelative } from '../lib/format'
import { useApi, type ApiState } from '../lib/useApi'

const SUGGESTIONS = [
  'Where is my most recent order?',
  'What is your return policy?',
  'My order arrived damaged. What should I do?',
  'Do you ship outside the EU?',
]

/**
 * /chat and /chat/:conversationId.
 *
 * Every conversation gets its own <ChatSession> (via `key`), so switching conversations starts with
 * fresh state. One exception: when a new conversation is created while an answer is streaming, the
 * URL changes to /chat/<new id> but the same session keeps going.
 */
export function ChatPage() {
  const params = useParams()
  const conversationId = params.conversationId ? Number(params.conversationId) : null
  const conversations = useApi(() => api.conversations({ limit: 30 }), [])
  const [createdId, setCreatedId] = useState<number | null>(null)
  const [session, setSession] = useState({ id: conversationId, key: 0 })
  const [historyOpen, setHistoryOpen] = useState(false)

  if (conversationId !== session.id) {
    // Adjusting state during render (instead of in an effect) avoids rendering the old conversation once more.
    const continuing = conversationId !== null && conversationId === createdId
    setSession({ id: conversationId, key: continuing ? session.key : session.key + 1 })
  }

  const list = <ConversationList state={conversations} activeId={conversationId} onSelect={() => setHistoryOpen(false)} />

  return (
    <div className="flex h-[calc(100dvh-3.8rem)] lg:h-dvh">
      <aside className="hidden w-72 shrink-0 flex-col border-r border-line bg-surface xl:flex">{list}</aside>
      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} title="Conversations">
        <div className="-mx-5 -mb-5 max-h-[60vh] overflow-y-auto overscroll-contain">{list}</div>
      </Dialog>
      <ChatSession
        key={session.key}
        conversationId={conversationId}
        onCreated={setCreatedId}
        onAnswered={conversations.reload}
        onShowHistory={() => setHistoryOpen(true)}
      />
    </div>
  )
}

function ChatSession({
  conversationId,
  onCreated,
  onAnswered,
  onShowHistory,
}: {
  conversationId: number | null
  onCreated: (id: number) => void
  onAnswered: () => void
  onShowHistory: () => void
}) {
  const user = useUser()
  const navigate = useNavigate()
  const location = useLocation()
  const [initialId] = useState(conversationId) // the conversation this session was opened for
  const session = useChatSession(initialId, {
    onCreated: (id) => {
      onCreated(id)
      navigate(`/chat/${id}`, { replace: true })
    },
    onAnswered,
  })
  const { items, loadingHistory, historyError, busy, announcement } = session
  const [draft, setDraft] = useState('')
  const sentInitialPrompt = useRef(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [items])

  async function send(text: string) {
    setDraft('')
    await session.send(text)
    inputRef.current?.focus()
  }

  // A question typed on the dashboard (or an order page) arrives as navigation state: send it once.
  const initialPrompt = (location.state as { prompt?: string } | null)?.prompt
  const sendInitialPrompt = useEffectEvent((prompt: string) => {
    navigate(location.pathname, { replace: true, state: null })
    void send(prompt)
  })
  useEffect(() => {
    if (!initialPrompt || sentInitialPrompt.current) return
    sentInitialPrompt.current = true
    sendInitialPrompt(initialPrompt)
  }, [initialPrompt])

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    void send(draft)
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      void send(draft)
    }
  }

  const firstName = user.name?.split(' ')[0]

  return (
    <section className="flex min-w-0 flex-1 flex-col" aria-label="Chat with the AI assistant">
      <header className="flex items-center justify-between gap-3 border-b border-line bg-surface px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand text-brand-ink">
            <Bot aria-hidden className="size-4" />
          </span>
          <div className="min-w-0">
            <h1 className="font-semibold leading-tight">AI assistant</h1>
            <p className="truncate text-xs text-muted">Looks up your orders and tickets, and answers from our policy documents</p>
          </div>
        </div>
        <div className="flex shrink-0 gap-1 xl:hidden">
          <Button variant="ghost" onClick={onShowHistory} aria-label="Show conversations">
            <History aria-hidden className="size-4" />
          </Button>
          <Button variant="ghost" onClick={() => navigate('/chat')} aria-label="New conversation">
            <Plus aria-hidden className="size-4" />
          </Button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto overscroll-contain">
        <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
          {loadingHistory ? (
            <div className="py-16 text-center">
              <Spinner label="Loading conversation" />
            </div>
          ) : historyError ? (
            <ErrorState error={historyError} />
          ) : items.length === 0 ? (
            <div className="py-10">
              <h2 className="text-xl font-semibold tracking-tight">{firstName ? `Hi ${firstName}, how can I help?` : 'How can I help?'}</h2>
              <p className="mt-1 text-sm text-muted">
                Ask about an order, a return or a problem. The assistant checks your account and our documents before it answers.
              </p>
              <div className="mt-6 grid gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    disabled={busy}
                    onClick={() => void send(suggestion)}
                    className="rounded-lg border border-line bg-surface px-4 py-3 text-left text-sm text-ink-2 hover:border-line-strong hover:text-ink"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <MessageList items={items} onRetry={session.retry} />
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <form onSubmit={onSubmit} className="border-t border-line bg-surface px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <label htmlFor="chat-input" className="sr-only">
            Message
          </label>
          <textarea
            id="chat-input"
            ref={inputRef}
            rows={1}
            maxLength={4000}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask about an order, a return, a delivery…"
            className="max-h-40 min-h-11 flex-1 resize-none rounded-xl border border-line-strong bg-surface px-4 py-2.5 text-sm [field-sizing:content] placeholder:text-muted/80 focus:border-brand focus:outline-none"
          />
          <Button type="submit" className="size-11 shrink-0 !p-0" disabled={busy || !draft.trim()} aria-label="Send message">
            <Send aria-hidden className="size-4" />
          </Button>
        </div>
        <p className="mx-auto mt-1.5 max-w-3xl text-xs text-muted">Enter to send, Shift + Enter for a new line. Answers can contain mistakes.</p>
      </form>
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
    </section>
  )
}

function ConversationList({ state, activeId, onSelect }: { state: ApiState<Page<ConversationSummary>>; activeId: number | null; onSelect: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="p-3">
        <Link
          to="/chat"
          onClick={onSelect}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-line-strong bg-surface px-3.5 py-2 text-sm font-medium hover:bg-surface-2"
        >
          <Plus aria-hidden className="size-4" /> New conversation
        </Link>
      </div>
      <nav aria-label="Conversations" className="flex-1 overflow-y-auto overscroll-contain px-3 pb-3">
        {state.loading && !state.data ? (
          <div className="p-3">
            <Spinner label="Loading conversations" />
          </div>
        ) : state.error ? (
          <p className="p-3 text-sm text-bad">{state.error.message}</p>
        ) : !state.data?.items.length ? (
          <p className="flex items-center gap-2 p-3 text-sm text-muted">
            <MessageSquare aria-hidden className="size-4" /> No conversations yet
          </p>
        ) : (
          <ul className="space-y-0.5">
            {state.data.items.map((conversation) => (
              <li key={conversation.id}>
                <Link
                  to={`/chat/${conversation.id}`}
                  onClick={onSelect}
                  aria-current={conversation.id === activeId ? 'page' : undefined}
                  className={`block rounded-lg px-3 py-2 text-sm ${
                    conversation.id === activeId ? 'bg-brand-soft text-brand' : 'text-ink-2 hover:bg-surface-2'
                  }`}
                >
                  <span className="block truncate font-medium">{conversation.title ?? `Conversation #${conversation.id}`}</span>
                  <span className="text-xs text-muted">
                    {formatRelative(conversation.updated_at)}, {conversation.message_count} messages
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </nav>
    </div>
  )
}
