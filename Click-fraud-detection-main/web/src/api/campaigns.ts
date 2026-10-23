import { apiFetch } from './client'

export interface Campaign {
  id: number
  user_id: number
  name: string
  ad_type: string
  platform: string
  purpose: string
  status: 'Active' | 'Paused' | 'Completed'
  created_at: string | null
  cpc: number | null
  avg_conversion_value: number | null
  expected_conversion_rate: number | null
  block_threshold: number | null
  click_count: number
  fraud_count: number
  valid_count: number
  suspicious_count: number
}

export interface CampaignInput {
  name: string
  ad_type: string
  platform: string
  purpose: string
  cpc: number
  avg_conversion_value: number
  expected_conversion_rate: number
}

export interface CampaignClick {
  id: number
  campaign_id: number
  ip_address: string
  user_agent: string
  classification: 'FRAUD' | 'SUSPICIOUS' | 'VALID' | string
  fraud_reason: string | null
  score: number | null
  decision: string | null
  reason_codes: string[] | string | null
  model_version: string | null
  created_at: string | null
}

export interface CampaignStats {
  total: number
  fraud: number
  suspicious: number
  valid: number
  fraud_rate: number
}

export interface CampaignAlert { level: string; message: string }

export interface ThresholdAnalysis {
  recommended_block_threshold: number
  active_block_threshold: number
  analysis: {
    threshold: number
    estimated_wasted_spend_saved: number
    estimated_legitimate_conversions_lost: number
    estimated_conversion_value_lost: number
    sample_size: number
    labelled_fraud_count: number
    labelled_legitimate_count: number
  }
  estimate_notice: string
}

export function getCampaigns() { return apiFetch<Campaign[]>('/campaigns?limit=500') }
export function getCampaign(id: number) { return apiFetch<Campaign>(`/campaigns/${id}`) }
export function createCampaign(input: CampaignInput) {
  return apiFetch<{ message: string; campaign_id: number; api_key: string; note: string }>('/campaigns', {
    method: 'POST', body: JSON.stringify(input),
  })
}
export function setCampaignStatus(id: number, status: 'Active' | 'Paused') {
  return apiFetch<{ message: string }>(`/campaigns/${id}/status?status=${status}`, { method: 'PATCH' })
}
export function deleteCampaign(id: number) {
  return apiFetch<{ message: string }>(`/campaigns/${id}`, { method: 'DELETE' })
}
export function getCampaignStats(id: number) { return apiFetch<CampaignStats>(`/campaigns/${id}/stats`) }
export function getCampaignAlerts(id: number) { return apiFetch<CampaignAlert[]>(`/campaigns/${id}/alerts`) }
export function getCampaignClicks(id: number, limit: number, offset: number) {
  return apiFetch<CampaignClick[]>(`/campaigns/${id}/clicks?limit=${limit}&offset=${offset}`)
}
export function getThresholdAnalysis(id: number, threshold?: number) {
  const query = threshold === undefined ? '' : `?threshold=${threshold.toFixed(2)}`
  return apiFetch<ThresholdAnalysis>(`/campaigns/${id}/threshold-analysis${query}`)
}
export function updateCampaignEconomics(id: number, values: Pick<CampaignInput, 'cpc' | 'avg_conversion_value' | 'expected_conversion_rate'>) {
  return apiFetch<{ message: string }>(`/campaigns/${id}/economics`, { method: 'PATCH', body: JSON.stringify(values) })
}
export function updateCampaignThreshold(id: number, block_threshold: number) {
  return apiFetch<{ block_threshold: number }>(`/campaigns/${id}/block-threshold`, {
    method: 'PATCH', body: JSON.stringify({ block_threshold }),
  })
}
