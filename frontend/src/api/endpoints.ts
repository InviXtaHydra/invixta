// One function per backend endpoint used by the app.
import { getCartToken, query, request } from './client'
import type {
  Cart,
  Conversation,
  ConversationSummary,
  DocumentDetail,
  DocumentInfo,
  Metrics,
  Order,
  OrderStatus,
  OrderSummary,
  Page,
  Payment,
  PaymentMethod,
  Product,
  ProductCategory,
  ProductSummary,
  League,
  ShippingMethod,
  ShopInfo,
  Ticket,
  TicketPriority,
  TicketStatus,
  User,
} from './types'

export interface ProductQuery {
  category?: ProductCategory | ''
  team?: string
  league?: string
  size?: string
  q?: string
  min_price?: number
  max_price?: number
  on_sale?: boolean
  sort?: 'popular' | 'new' | 'price_asc' | 'price_desc'
  limit?: number
  offset?: number
}

export interface CheckoutBody {
  name: string
  street: string
  postcode: string
  city: string
  country: string
  shipping_method: ShippingMethod
  payment_method: PaymentMethod
}

const cartHeaders = (): Record<string, string> => {
  const token = getCartToken()
  return token ? { 'X-Cart-Token': token } : {}
}

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

  // --- shop ---
  products(params: ProductQuery = {}) {
    const { on_sale, ...rest } = params
    return request<Page<ProductSummary>>(`/catalog/products${query({ ...rest, on_sale: on_sale ? 'true' : undefined })}`)
  },
  product(slug: string) {
    return request<Product>(`/catalog/products/${encodeURIComponent(slug)}`)
  },
  leagues() {
    return request<League[]>('/catalog/leagues')
  },
  shopInfo() {
    return request<ShopInfo>('/shop/info')
  },
  cart() {
    return request<Cart>('/cart', { headers: cartHeaders() })
  },
  addToCart(body: { variant_id: number; quantity: number; personalization_name?: string; personalization_number?: number }) {
    return request<Cart>('/cart/items', { method: 'POST', json: body, headers: cartHeaders() })
  },
  updateCartItem(id: number, quantity: number) {
    return request<Cart>(`/cart/items/${id}`, { method: 'PATCH', json: { quantity }, headers: cartHeaders() })
  },
  removeCartItem(id: number) {
    return request<Cart>(`/cart/items/${id}`, { method: 'DELETE', headers: cartHeaders() })
  },
  quote(country: string, shipping_method: ShippingMethod) {
    return request<{ subtotal: string; shipping_cost: string; total: string }>(`/cart/quote${query({ country, shipping_method })}`, {
      headers: cartHeaders(),
    })
  },
  claimCart(token: string) {
    return request<Cart>('/cart/claim', { method: 'POST', headers: { 'X-Cart-Token': token } })
  },
  checkout(body: CheckoutBody) {
    return request<{ order: Order; payment: Payment }>('/checkout', { method: 'POST', json: body })
  },
  payment(id: number) {
    return request<Payment>(`/payments/${id}`)
  },
  completePayment(id: number, outcome: 'approve' | 'decline') {
    return request<Payment>(`/payments/${id}/complete`, { method: 'POST', json: { outcome } })
  },
  retryPayment(orderId: number, payment_method?: PaymentMethod) {
    return request<Payment>(`/orders/${orderId}/payments`, { method: 'POST', json: { payment_method } })
  },
  cancelOrder(orderId: number) {
    return request<Order>(`/orders/${orderId}/cancel`, { method: 'POST' })
  },

  metrics(days = 14) {
    return request<Metrics>(`/admin/metrics${query({ days })}`)
  },
}
