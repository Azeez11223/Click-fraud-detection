import { apiBase, getStoredToken } from '@/api/client'
import { apiFetch } from '@/api/client'

export type IpEntry = { id: number; ip_address: string; list_type: string; note: string | null; source: string | null; created_at: string | null }
export type IpDataset = { id: number; filename: string; list_type: string; row_count: number; created_at: string | null }
export const listIps = (type: string) => apiFetch<IpEntry[]>(`/ip-lists?list_type=${type}&limit=500`)
export const ipCounts = () => apiFetch<{ blocked: number; whitelisted: number; total: number }>('/ip-lists/counts')
export const addIp = (ip_address: string, list_type: string, note: string) => apiFetch('/ip-lists', { method: 'POST', body: JSON.stringify({ ip_address, list_type, note }) })
export const removeIp = (ip: string) => apiFetch(`/ip-lists/${encodeURIComponent(ip)}`, { method: 'DELETE' })
export const listDatasets = () => apiFetch<IpDataset[]>('/ip-datasets')
export const deleteDataset = (id: number) => apiFetch(`/ip-datasets/${id}`, { method: 'DELETE' })
export function uploadDataset(file: File, listType: string, onProgress: (value: number) => void): Promise<{ total_ips: number; inserted_to_list: number; skipped: number; invalid: number }> {
  return new Promise((resolve, reject) => {
    const form = new FormData(); form.append('file', file); form.append('list_type', listType)
    const request = new XMLHttpRequest(); request.open('POST', `${apiBase}/ip-datasets/upload`)
    const token = getStoredToken(); if (token) request.setRequestHeader('Authorization', `Bearer ${token}`)
    request.upload.onprogress = (event) => { if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100)) }
    request.onerror = () => reject(new Error('Unable to reach the API.'))
    request.onload = () => { let body: {error?:{message?:string};detail?:string;total_ips?:number;inserted_to_list?:number;skipped?:number;invalid?:number}; try { body = JSON.parse(request.responseText) } catch { body = {} }; if (request.status >= 200 && request.status < 300) resolve({total_ips:body.total_ips??0,inserted_to_list:body.inserted_to_list??0,skipped:body.skipped??0,invalid:body.invalid??0}); else reject(new Error(body.error?.message ?? body.detail ?? 'Upload failed.')) }
    request.send(form)
  })
}

export function isValidIp(value: string): boolean {
  const ip = value.trim()
  if (ip.includes(':')) {
    if (!/^[0-9a-f:]+$/i.test(ip) || ip.includes(':::') || ip.split('::').length > 2) return false
    if ((ip.startsWith(':') && !ip.startsWith('::')) || (ip.endsWith(':') && !ip.endsWith('::'))) return false
    const halves = ip.split('::'); const groups = ip.split(':').filter(Boolean)
    return groups.length <= 8 && (halves.length === 2 ? groups.length < 8 : groups.length === 8) && groups.every((part) => part.length <= 4)
  }
  const parts = ip.split('.')
  return parts.length === 4 && parts.every((part) => /^\d{1,3}$/.test(part) && Number(part) <= 255)
}

