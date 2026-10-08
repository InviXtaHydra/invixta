import { useEffect, useRef, useState } from 'react'
import { streamChat } from '../../api/chatStream'
import { api } from '../../api/endpoints'
import { applyEvent, fromMessage, type ChatItem } from './chatState'

let keyCounter = 0
const newKey = () => `local-${++keyCounter}`

export interface ChatSession {
  conversationId: number | null
  items: ChatItem[]
  loadingHistory: boolean
  historyError: Error | undefined
  busy: boolean
  announcement: string // for a screen-reader live region
  send: (text: string) => Promise<void>
  retry: (failedKey: string) => void
}

/**
 * One chat conversation: loads its history, sends messages over the streaming endpoint and applies
 * the streamed events. Used by the full chat page and by the chat widget in the shop.
 */
export function useChatSession(
  initialId: number | null,
  { onCreated, onAnswered }: { onCreated?: (id: number) => void; onAnswered?: () => void } = {},
): ChatSession {
  const [conversationId, setConversationId] = useState(initialId)
  const [items, setItems] = useState<ChatItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(initialId !== null)
  const [historyError, setHistoryError] = useState<Error>()
  const [busy, setBusy] = useState(false)
  const [announcement, setAnnouncement] = useState('')
  const active = useRef(true) // false once the component using this session is gone

  useEffect(() => {
    active.current = true
    return () => {
      active.current = false
    }
  }, [])

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

  async function send(text: string) {
    const message = text.trim()
    if (!message || busy) return
    const assistantKey = newKey()
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
            setConversationId(event.conversation_id)
            onCreated?.(event.conversation_id)
          }
          return
        }
        update((item) => applyEvent(item, event))
        if (event.type === 'done') {
          setAnnouncement('Answer received.')
          onAnswered?.()
        }
        if (event.type === 'error') setAnnouncement(`The assistant ran into a problem: ${event.detail}`)
      })
    } catch (error) {
      update((item) => ({ ...item, pending: false, error: error instanceof Error ? error.message : 'Something went wrong' }))
      setAnnouncement('The message could not be sent.')
    } finally {
      setBusy(false)
    }
  }

  function retry(failedKey: string) {
    // A failed answer wasn't saved: remove it and its question, then send the question again.
    const index = items.findIndex((item) => item.key === failedKey)
    const question = items[index - 1]
    if (!question || question.role !== 'user') return
    setItems((all) => all.filter((_, i) => i !== index && i !== index - 1))
    void send(question.content)
  }

  return { conversationId, items, loadingHistory, historyError, busy, announcement, send, retry }
}
