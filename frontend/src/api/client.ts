// A small fetch wrapper: adds the JWT, turns error responses into ApiError, and logs out on 401.

export const API_BASE = import.meta.env.VITE_API_URL ?? '/api'
const TOKEN_KEY = 'supportai.token'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

let unauthorizedHandler: (() => void) | null = null

/** Called by AuthProvider: what to do when the server says the token is no longer valid. */
export function onUnauthorized(handler: (() => void) | null) {
  unauthorizedHandler = handler
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage can be unavailable (private mode); the session then lasts until the tab closes.
  }
}

/** FastAPI errors are {"detail": "..."} or, for validation errors, {"detail": [{"msg": ..., "loc": [...]}]}. */
export async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const first = body.detail[0] as { msg?: string; loc?: unknown[] }
      const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]) : ''
      const msg = (first.msg ?? 'Invalid input').replace(/^Value error, /, '')
      return field && field !== 'body' ? `${field.replace(/_/g, ' ')}: ${msg}` : msg
    }
  } catch {
    // not JSON
  }
  if (response.status === 429) return 'Too many requests. Please wait a moment and try again.'
  if (response.status >= 500) return 'The server ran into a problem. Please try again.'
  return `Request failed (${response.status})`
}

export function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

interface RequestOptions {
  method?: string
  json?: unknown
  form?: FormData | URLSearchParams
  signal?: AbortSignal
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders() }
  let body: BodyInit | undefined
  if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.json)
  } else if (options.form) {
    body = options.form
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { method: options.method ?? 'GET', headers, body, signal: options.signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.")
  }

  if (response.status === 401 && getToken()) {
    setToken(null)
    unauthorizedHandler?.()
  }
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** Builds "?a=1&b=2", skipping empty values. */
export function query(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}
