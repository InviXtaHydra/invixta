// TypeScript versions of the backend's Pydantic response models (backend/app/schemas).

export type Role = 'CUSTOMER' | 'AGENT' | 'ADMIN'
export type OrderStatus = 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled'
export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'
export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent'

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface User {
  id: number
  email: string
  role: Role
  created_at: string
  customer_id: number | null
  name: string | null
}

export interface OrderItem {
  product_id: number
  product_name: string
  quantity: number
  unit_price: string
  line_total: string
}

export interface OrderSummary {
  id: number
  customer_id: number
  status: OrderStatus
  total_amount: string
  tracking_number: string | null
  carrier: string | null
  estimated_delivery: string | null
  created_at: string
  updated_at: string
  item_count: number
}

export interface Order extends OrderSummary {
  items: OrderItem[]
}

export interface Ticket {
  id: number
  customer_id: number
  subject: string
  description: string
  status: TicketStatus
  priority: TicketPriority
  created_at: string
  updated_at: string
}

export interface Source {
  chunk_id: number
  document_id: number
  filename: string
  page_number: number | null
  chunk_index: number
  score: number
  excerpt: string
}

export interface ToolCall {
  name: string
  arguments: Record<string, unknown>
  status: 'ok' | 'error' | string
  summary: string
  duration_ms: number
}

export interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  tool_calls: ToolCall[] | null
  sources: Source[] | null
  latency_ms: number | null
}

export interface ConversationSummary {
  id: number
  customer_id: number
  created_at: string
  updated_at: string
  message_count: number
  title: string | null
}

export interface Conversation {
  id: number
  customer_id: number
  created_at: string
  updated_at: string
  messages: Message[]
}

export interface ChatResponse {
  conversation_id: number
  message_id: number
  message: string
  sources: Source[]
  tool_calls: ToolCall[]
  latency_ms: number
}

export type ChatEvent =
  | { type: 'start'; conversation_id: number }
  | { type: 'tool_start'; name: string; arguments: Record<string, unknown> }
  | ({ type: 'tool_end' } & ToolCall)
  | { type: 'text'; delta: string }
  | ({ type: 'done' } & ChatResponse)
  | { type: 'error'; detail: string }

export interface DocumentInfo {
  id: number
  filename: string
  uploaded_at: string
  page_count: number
  size_bytes: number
  chunk_count: number
}

export interface DocumentChunk {
  id: number
  chunk_index: number
  page_number: number | null
  content: string
  created_at: string
}

export interface DocumentDetail extends DocumentInfo {
  chunks: DocumentChunk[]
}

export interface Metrics {
  total_conversations: number
  chat_turns: number
  avg_latency_ms: number | null
  p95_latency_ms: number | null
  tool_calls: number
  tool_usage: { name: string; calls: number; errors: number }[]
  rag_searches: number
  tickets_total: number
  tickets_by_status: Record<TicketStatus, number>
  unresolved_questions: number
  recent_unresolved: { conversation_id: number; question: string | null; answered_at: string }[]
  chat_turns_per_day: { day: string; chat_turns: number }[]
}
