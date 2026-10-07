import { Bot, History, MessageSquare, Plus, RotateCcw, Send } from 'lucide-react'
import { useEffect, useEffectEvent, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { streamChat } from '../api/chatStream'
import { api } from '../api/endpoints'
import type { ConversationSummary, Page } from '../api/types'
import { useUser } from '../auth/useAuth'
import { AgentTrace } from '../components/chat/AgentTrace'
import { applyEvent, fromMessage, type ChatItem } from '../components/chat/chatState'
import { MessageText } from '../components/chat/MessageText'
import { Sources } from '../components/chat/Sources'
import { ErrorState, Spinner } from '../components/feedback'
import { Button, Dialog } from '../components/ui'
import { formatMs, formatRelative } from '../lib/format'
import { useApi, type ApiState } from '../lib/useApi'

const SUGGESTIONS = [
  'Where is my most recent order?',
  'What is your return policy?',
  'My order arrived damaged. What should I do?',
  'Do you ship outside the EU?',
]

let keyCounter = 0
const newKey = () => `local-${++keyCounter}`

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
        <div className="-mx-5 -mb-5 max-h-[60vh] overflow-y-auto">{list}</div>
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
  const [items, setItems] = useState<ChatItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(initialId !== null)
  const [historyError, setHistoryError] = useState<Error>()
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState('')
  const [announcement, setAnnouncement] = useState('')
  const active = useRef(true) // false once the user moved to another conversation
  const sentInitialPrompt = useRef(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    active.current = true
    return () => {
      active.current = false
    }
  }, [])

  // Load the existing messages of this conversation.
  useEffect(() => {
    if (initialId === null) return
    let current = true
    api
      .conversation(initialId)
      .then((conversation) => current && setItems(conversation.messages.filter((m) => m.role !== 'system').map(fromMessage)))
      .catch((error: Error) => current && setHistoryError(error))
      .finally(() => current && setLoadingHistory(false))
    return () => {
      current = false
    }
  }, [initialId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [items])

  async function send(text: string) {
    const message = text.trim()
    if (!message || busy) return
    const assistantKey = newKey()
    setDraft('')
    setBusy(true)
    setAnnouncement('The assistant is answering…')
    setItems((all) => [
      ...all,
      { key: newKey(), role: 'user', content: message, steps: [], sources: [] },
      { key: assistantKey, role: 'assistant', content: '', steps: [], sources: [], pending: true },
    ])
    const update = (change: (item: ChatItem) => ChatItem) =>
      setItems((all) => all.map((item) => (item.key === assistantKey ? change(item) : item)))

    try {
      await streamChat({ conversation_id: conversationId, message }, (event) => {
        if (!active.current) return
        if (event.type === 'start') {
          if (conversationId === null) {
            onCreated(event.conversation_id)
            navigate(`/chat/${event.conversation_id}`, { replace: true })
          }
          return
        }
        update((item) => applyEvent(item, event))
        if (event.type === 'done') {
          setAnnouncement('Answer received.')
          onAnswered()
        }
        if (event.type === 'error') setAnnouncement(`The assistant ran into a problem: ${event.detail}`)
      })
    } catch (error) {
      update((item) => ({ ...item, pending: false, error: error instanceof Error ? error.message : 'Something went wrong' }))
      setAnnouncement('The message could not be sent.')
    } finally {
      setBusy(false)
      inputRef.current?.focus()
    }
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

  function retry(failedKey: string) {
    // A failed answer wasn't saved: remove it and its question, then send the question again.
    const index = items.findIndex((item) => item.key === failedKey)
    const question = items[index - 1]
    if (!question || question.role !== 'user') return
    setItems((all) => all.filter((_, i) => i !== index && i !== index - 1))
    void send(question.content)
  }

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

      <div className="flex-1 overflow-y-auto">
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
            <ol className="space-y-6">
              {items.map((item) => (
                <li key={item.key}>{item.role === 'user' ? <UserBubble item={item} /> : <AssistantMessage item={item} onRetry={retry} />}</li>
              ))}
            </ol>
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
      <nav aria-label="Conversations" className="flex-1 overflow-y-auto px-3 pb-3">
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
