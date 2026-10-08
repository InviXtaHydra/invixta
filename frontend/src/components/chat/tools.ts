import { BookOpen, CircleSlash, Database, LifeBuoy, Package, Shirt, Ticket, Wrench, type LucideIcon } from 'lucide-react'

interface ToolInfo {
  running: string // shown while the tool runs
  done: string // shown after it ran
  icon: LucideIcon
}

/** How each agent tool is described in the chat, so it's clear what the AI actually did. */
export const TOOL_INFO: Record<string, ToolInfo> = {
  get_order_status: { running: 'Checking your order…', done: 'Checked your order', icon: Database },
  get_customer_orders: { running: 'Looking up your orders…', done: 'Looked up your orders', icon: Package },
  search_knowledge_base: { running: 'Searching our help articles…', done: 'Searched our help articles', icon: BookOpen },
  create_support_ticket: { running: 'Creating a support ticket…', done: 'Support ticket', icon: LifeBuoy },
  get_support_tickets: { running: 'Checking your tickets…', done: 'Checked your tickets', icon: Ticket },
  search_products: { running: 'Checking the shop…', done: 'Checked the shop', icon: Shirt },
  request_order_cancellation: { running: 'Checking if your order can be cancelled…', done: 'Cancellation', icon: CircleSlash },
}

export function toolInfo(name: string): ToolInfo {
  return TOOL_INFO[name] ?? { running: `Running ${name}…`, done: name, icon: Wrench }
}
