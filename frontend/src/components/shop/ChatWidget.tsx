import { Bot, Maximize2, MessageCircle, Plus, Send, X } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router'
import { useAuth } from '../../auth/useAuth'
import { MessageList } from '../chat/Messages'
import { useChatSession } from '../chat/useChatSession'
import { Spinner } from '../feedback'
import { ButtonLink } from '../ui'
import { ChatWidgetContext } from './useChatWidget'

const STORAGE_KEY = 'invixta.chat'
const SUGGESTIONS = ['Where is my order?', 'Which size should I take?', 'Can I return a printed shirt?']

function storedConversation(): number | null {
  try {
    const value = Number(localStorage.getItem(STORAGE_KEY))
    return Number.isFinite(value) && value > 0 ? value : null
  } catch {
    return null
  }
}

function remember(id: number | null) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, String(id))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // only a convenience
  }
}

/** Provides openChat() to the shop pages and renders the floating support chat. */
export function ChatWidgetProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  // The draft lives here, so a page can put a question in the input ("Which size should I take?").
  const [draft, setDraft] = useState('')
  const value = {
    openChat: (text?: string) => {
      if (text) setDraft(text)
      setOpen(true)
    },
  }
  return (
    <ChatWidgetContext.Provider value={value}>
      {children}
      <ChatWidget open={open} onOpenChange={setOpen} draft={draft} onDraftChange={setDraft} />
    </ChatWidgetContext.Provider>
  )
}

function ChatWidget({
  open,
  onOpenChange,
  draft,
  onDraftChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  draft: string
  onDraftChange: (text: string) => void
}) {
  const { user } = useAuth()
  const [sessionKey, setSessionKey] = useState(0) // a new key starts a new conversation
  if (user && user.role !== 'CUSTOMER') return null // the assistant is for customers

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => onOpenChange(true)}
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full border border-white/10 bg-night px-4 py-3 font-medium text-night-ink shadow-lg hover:bg-night-2"
        >
          <MessageCircle aria-hidden className="size-5 text-accent" />
          <span className="hidden sm:inline">Questions? Ask us</span>
          <span className="sr-only sm:hidden">Open the support chat</span>
        </button>
      )}
      {open && (
        <section
          aria-label="Support chat"
          className="fixed inset-x-0 bottom-0 z-50 flex h-[min(38rem,85dvh)] flex-col overflow-hidden rounded-t-2xl border border-line bg-canvas shadow-2xl sm:inset-x-auto sm:bottom-5 sm:right-5 sm:w-[24rem] sm:rounded-2xl"
        >
          <header className="flex items-center gap-3 border-b-2 border-accent bg-night px-4 py-3 text-night-ink">
            <Bot aria-hidden className="size-5" />
            <div className="min-w-0 flex-1">
              <h2 className="font-display text-lg font-bold uppercase leading-none tracking-wide">Invixta Support</h2>
              <p className="text-xs text-white/70">Orders, sizes, delivery and returns</p>
            </div>
            {user && (
              <button
                type="button"
                onClick={() => (remember(null), setSessionKey((k) => k + 1))}
                className="rounded-md p-1.5 hover:bg-white/15"
                title="New conversation"
              >
                <Plus aria-hidden className="size-4" />
                <span className="sr-only">New conversation</span>
              </button>
            )}
            <button type="button" onClick={() => onOpenChange(false)} className="rounded-md p-1.5 hover:bg-white/15">
              <X aria-hidden className="size-4" />
              <span className="sr-only">Close the chat</span>
            </button>
          </header>
          {user ? (
            <WidgetSession key={sessionKey} draft={draft} onDraftChange={onDraftChange} />
          ) : (
            <GuestNotice />
          )}
        </section>
      )}
    </>
  )
}

function GuestNotice() {
  const location = useLocation()
  return (
    <div className="flex flex-1 flex-col items-center justify-center p-6 text-center">
      <Bot aria-hidden className="mb-3 size-8 text-brand" />
      <p className="font-medium">Sign in to chat with our assistant</p>
      <p className="mt-1 text-sm text-muted">It looks up your orders, so it needs to know who you are.</p>
      <ButtonLink to="/login" state={{ from: location.pathname + location.search }} className="mt-4">
        Sign in
      </ButtonLink>
    </div>
  )
}

function WidgetSession({ draft, onDraftChange: setDraft }: { draft: string; onDraftChange: (text: string) => void }) {
  const [initialId] = useState(storedConversation)
  const session = useChatSession(initialId, { onCreated: remember })
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [session.items])

  async function submit(event: FormEvent) {
    event.preventDefault()
    const text = draft
    setDraft('')
    await session.send(text)
    inputRef.current?.focus()
  }

  return (
    <>
      <div className="flex-1 overflow-y-auto overscroll-contain px-4 py-4">
        {session.loadingHistory ? (
          <div className="py-10 text-center">
            <Spinner label="Loading conversation" />
          </div>
        ) : session.items.length === 0 ? (
          <div>
            <p className="text-sm text-ink-2">Hi! Ask me about an order, sizes, delivery or returns.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  disabled={session.busy}
                  onClick={() => void session.send(s)}
                  className="rounded-full border border-line-strong bg-surface px-3 py-1.5 text-xs text-ink-2 hover:border-brand hover:text-ink"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <MessageList items={session.items} onRetry={session.retry} />
        )}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={submit} className="flex items-center gap-2 border-t border-line bg-surface p-3">
        <label htmlFor="widget-input" className="sr-only">
          Message
        </label>
        <input
          id="widget-input"
          ref={inputRef}
          autoFocus
          value={draft}
          maxLength={4000}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type your question…"
          className="min-w-0 flex-1 rounded-full border border-line-strong bg-surface px-4 py-2 text-sm focus:border-brand focus:outline-none"
        />
        <button
          type="submit"
          disabled={session.busy || !draft.trim()}
          className="grid size-9 shrink-0 place-items-center rounded-full bg-brand text-brand-ink disabled:opacity-50"
        >
          <Send aria-hidden className="size-4" />
          <span className="sr-only">Send message</span>
        </button>
        {session.conversationId && (
          <Link to={`/chat/${session.conversationId}`} className="grid size-9 shrink-0 place-items-center rounded-full text-muted hover:bg-surface-2" title="Open the full chat">
            <Maximize2 aria-hidden className="size-4" />
            <span className="sr-only">Open the full chat</span>
          </Link>
        )}
      </form>
      <p aria-live="polite" className="sr-only">
        {session.announcement}
      </p>
    </>
  )
}
