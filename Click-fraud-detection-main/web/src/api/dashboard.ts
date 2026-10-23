import { apiFetch } from './client'

export interface DashboardStats {
  total: number
  fraud: number
  review: number
  legit: number
  fraud_rate: number
}

export interface ClickRecord {
  id: number
  ip_address: string
  result: string
  confidence: number
  decision: string | null
  reason_codes: string[]
  model_version: string | null
  created_at: string
}

export interface DashboardAlert {
  level: string
  message: string
  campaign_id: number
  campaign_name: string
}

export function getDashboardStats() { return apiFetch<DashboardStats>('/stats') }
export function getRecentClicks() { return apiFetch<ClickRecord[]>('/clicks?limit=200') }
export function getRecentClicksLimit(limit: number) { return apiFetch<ClickRecord[]>(`/clicks?limit=${Math.min(500, Math.max(1, limit))}`) }
export function getDashboardAlerts() { return apiFetch<DashboardAlert[]>('/alerts') }
