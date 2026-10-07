// One function per backend endpoint used by the app.
import { query, request } from './client'
import type {
  Conversation,
  ConversationSummary,
  DocumentDetail,
  DocumentInfo,
  Metrics,
  Order,
  OrderStatus,
  OrderSummary,
  Page,
  Ticket,
  TicketPriority,
  TicketStatus,
  User,
} from './types'

export const api = {
  login(email: string, password: string) {
    const form = new URLSearchParams({ username: email, password })
    return request<{ access_token: string }>('/auth/login', { method: 'POST', form })
  },
  register(body: { name: string; email: string; password: string }) {
    return request<User>('/auth/register', { method: 'POST', json: body })
  },
  me() {
    return request<User>('/users/me')
  },
  changePassword(body: { current_password: string; new_password: string }) {
    return request<void>('/users/me/password', { method: 'POST', json: body })
  },

  orders(params: { status?: OrderStatus | ''; limit?: number; offset?: number } = {}) {
    return request<Page<OrderSummary>>(`/orders${query(params)}`)
  },
  order(id: number) {
    return request<Order>(`/orders/${id}`)
  },

  tickets(params: { status?: TicketStatus | ''; limit?: number; offset?: number } = {}) {
    return request<Page<Ticket>>(`/tickets${query(params)}`)
  },
  ticket(id: number) {
    return request<Ticket>(`/tickets/${id}`)
  },
  createTicket(body: { subject: string; description: string; priority: TicketPriority; customer_id?: number }) {
    return request<Ticket>('/tickets', { method: 'POST', json: body })
  },
  updateTicket(id: number, body: { status?: TicketStatus; priority?: TicketPriority }) {
    return request<Ticket>(`/tickets/${id}`, { method: 'PATCH', json: body })
  },

  conversations(params: { limit?: number; offset?: number } = {}) {
    return request<Page<ConversationSummary>>(`/conversations${query(params)}`)
  },
  conversation(id: number) {
    return request<Conversation>(`/conversations/${id}`)
  },

  documents() {
    return request<DocumentInfo[]>('/documents')
  },
  document(id: number) {
    return request<DocumentDetail>(`/documents/${id}`)
  },
  uploadDocument(file: File) {
    const form = new FormData()
    form.append('file', file)
    return request<DocumentInfo>('/documents', { method: 'POST', form })
  },
  deleteDocument(id: number) {
    return request<void>(`/documents/${id}`, { method: 'DELETE' })
  },

  metrics(days = 14) {
    return request<Metrics>(`/admin/metrics${query({ days })}`)
  },
}
