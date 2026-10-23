import { BellRing, Siren } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { DashboardAlert } from '@/api/dashboard'

export function AlertsStrip({ alerts }: { alerts: DashboardAlert[] }) {
  const shown = alerts.slice(0, 3)
  return <section aria-label="Campaign alerts" className="space-y-2">
    {shown.length === 0 ? <div className="flex items-center gap-2 rounded-xl border border-border bg-[#090e1b] px-4 py-3 text-sm text-muted"><BellRing size={16} /> No active campaign alerts</div> : shown.map((alert, index) => {
      const critical = alert.level === 'critical'
      const Icon = critical ? Siren : BellRing
      return <Link key={`${alert.campaign_id}-${alert.level}-${index}`} to={`/campaigns/${alert.campaign_id}`} className={`flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border px-4 py-3 text-sm ${critical ? 'border-danger/25 bg-danger/[0.06]' : 'border-warning/25 bg-warning/[0.05]'}`}>
        <Icon aria-hidden="true" size={16} className={critical ? 'text-danger' : 'text-warning'} /><span className="font-semibold">{alert.campaign_name}</span><span className="text-muted">{alert.message}</span><span className="ml-auto text-xs text-accent">Open campaign →</span>
      </Link>
    })}
  </section>
}
