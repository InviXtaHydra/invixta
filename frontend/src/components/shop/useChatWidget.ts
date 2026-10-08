import { createContext, useContext } from 'react'

export interface ChatWidgetValue {
  /** Open the chat widget, optionally with a question typed in. */
  openChat: (prompt?: string) => void
}

export const ChatWidgetContext = createContext<ChatWidgetValue>({ openChat: () => {} })

export const useChatWidget = () => useContext(ChatWidgetContext)
