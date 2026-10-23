import { apiFetch } from '@/api/client'

export type PlatformStats={platform:string;total:number;fraud:number;suspicious:number;valid:number;total_spend:number;wasted_spend:number}
export type HourlyRow={hour:string;platform:string;classification:string;cnt:number}
export type PlatformEvent={id:number;campaign_id:number;source?:string;platform:string;event_type?:string;ip_address:string;country:string;device:string;browser?:string;classification:string;fraud_reason?:string;cost_usd?:number;created_at:string}
export type EventInput={platform:string;event_type:string;ip_address:string;country:string;device:string;browser:string;cost_usd:number}
export const getPlatformStats=(id:number)=>apiFetch<PlatformStats[]>(`/campaigns/${id}/platform-stats`)
export const getHourlyBreakdown=(id:number,hours=24)=>apiFetch<HourlyRow[]>(`/campaigns/${id}/hourly-breakdown?hours=${hours}`)
export const getLiveFeed=(id:number)=>apiFetch<PlatformEvent[]>(`/campaigns/${id}/realtime-feed?limit=50`)
export const getPlatformEvents=(id:number)=>apiFetch<PlatformEvent[]>(`/campaigns/${id}/platform-events?limit=100`)
export const submitPlatformEvent=(id:number,input:EventInput)=>apiFetch<PlatformEvent & {reason?:string}>(`/campaigns/${id}/platform-event`,{method:'POST',body:JSON.stringify(input)})
