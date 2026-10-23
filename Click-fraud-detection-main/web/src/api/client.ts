const API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(/\/$/, '')
const TOKEN_KEY = 'adshield_access_token'
let firstRequestPending = true

function coldStartEvent(state: 'waking' | 'ready' | 'unreachable') {
  window.dispatchEvent(new CustomEvent('adshield:cold-start', { detail: state }))
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function storeToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearSession(): void {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem('adshield_user')
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  settings: { redirectOnUnauthorized?: boolean } = {},
): Promise<T> {
  const isFirstRequest = firstRequestPending
  firstRequestPending = false
  const wakeTimer = isFirstRequest ? window.setTimeout(() => coldStartEvent('waking'), 3000) : undefined
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const token = getStoredToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    if (wakeTimer !== undefined) window.clearTimeout(wakeTimer)
    if (isFirstRequest) coldStartEvent('unreachable')
    throw new ApiError('Unable to reach the API. Check that the backend is running.', 0)
  }
  if (wakeTimer !== undefined) window.clearTimeout(wakeTimer)
  if (isFirstRequest) coldStartEvent('ready')

  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body: unknown = await response.json()
      if (body && typeof body === 'object') {
        const record = body as { detail?: unknown; error?: { message?: unknown } }
        const candidate = record.error?.message ?? record.detail
        if (typeof candidate === 'string') message = candidate
      }
    } catch {
      // Keep the status-based message for non-JSON error responses.
    }
    if (response.status === 401) {
      clearSession()
      if (settings.redirectOnUnauthorized !== false && window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    throw new ApiError(message, response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const apiBase = API_BASE
