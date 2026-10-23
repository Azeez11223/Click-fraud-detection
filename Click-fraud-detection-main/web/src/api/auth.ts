import { apiFetch } from './client'

export interface SessionUser {
  id: number
  name: string
  email: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  user: SessionUser
}

export interface SignupInput {
  name: string
  email: string
  password: string
}

export function login(email: string, password: string) {
  return apiFetch<LoginResult>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  }, { redirectOnUnauthorized: false })
}

export function signup(input: SignupInput) {
  return apiFetch<{ message: string; user_id: number }>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify(input),
  }, { redirectOnUnauthorized: false })
}

export function currentUser() {
  return apiFetch<SessionUser>('/auth/me')
}

export function healthCheck() {
  return apiFetch<{ status: string }>('/healthz')
}
