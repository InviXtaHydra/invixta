import { BookOpen, Database, LifeBuoy, Package, Ticket, Wrench, type LucideIcon } from 'lucide-react'

interface ToolInfo {
  running: string // shown while the tool runs
  done: string // shown after it ran
  icon: LucideIcon
}

/** How each agent tool is described in the chat, so it's clear what the AI actually did. */
export const TOOL_INFO: Record<string, ToolInfo> = {
  get_order_status: { running: 'Checking your order…', done: 'Order database', icon: Database },
  get_customer_orders: { running: 'Looking up your orders…', done: 'Order history', icon: Package },
  search_knowledge_base: { running: 'Searching the knowledge base…', done: 'Knowledge base', icon: BookOpen },
  create_support_ticket: { running: 'Creating a support ticket…', done: 'Support ticket', icon: LifeBuoy },
  get_support_tickets: { running: 'Checking your tickets…', done: 'Your tickets', icon: Ticket },
}

export function toolInfo(name: string): ToolInfo {
  return TOOL_INFO[name] ?? { running: `Running ${name}…`, done: name, icon: Wrench }
}
