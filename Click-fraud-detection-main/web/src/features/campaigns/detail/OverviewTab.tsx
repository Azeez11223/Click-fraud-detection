import { useQuery } from '@tanstack/react-query'
import { BadgeCheck, CircleAlert, MousePointer2, ShieldAlert } from 'lucide-react'
import { getCampaignAlerts, getCampaignStats } from '@/api/campaigns'
import { PanelSkeleton, QueryError } from '@/components/DataState'

export function OverviewTab({ id }: { id: number }) {
  const stats = useQuery({ queryKey: ['campaign-stats', id], queryFn: () => getCampaignStats(id), refetchOnWindowFocus: true })
  const alerts = useQuery({ queryKey: ['campaign-alerts', id], queryFn: () => getCampaignAlerts(id), refetchOnWindowFocus: true })
  return <div className="space-y-5">
    {alerts.isPending ? <PanelSkeleton rows={1} /> : alerts.isError ? <QueryError error={alerts.error} retry={() => void alerts.refetch()} /> : alerts.data.length === 0
      ? <div className="flex items-center gap-2 rounded-xl border border-border bg-[#090e1b] p-4 text-sm text-muted"><BadgeCheck size={17} className="text-success" /> No active alerts for this campaign.</div>
      : alerts.data.map((alert, index) => <div key={`${alert.level}-${index}`} className={`flex items-center gap-3 rounded-xl border p-4 text-sm ${alert.level === 'critical' ? 'border-danger/25 bg-danger/[0.06]' : 'border-warning/25 bg-warning/[0.05]'}`}><CircleAlert size={17} className={alert.level === 'critical' ? 'text-danger' : 'text-warning'} /><span>{alert.message}</span></div>)}
    {stats.isPending ? <StatsSkeleton /> : stats.isError ? <QueryError error={stats.error} retry={() => void stats.refetch()} /> : <section aria-label="Campaign click statistics" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Stat label="Total clicks" value={stats.data.total} icon={MousePointer2} />
      <Stat label="Valid clicks" value={stats.data.valid} icon={BadgeCheck} />
      <Stat label="Suspicious" value={stats.data.suspicious} icon={CircleAlert} />
      <Stat label="Fraud clicks" value={stats.data.fraud} icon={ShieldAlert} />
      <Stat label="Fraud rate" value={`${stats.data.fraud_rate.toFixed(1)}%`} icon={ShieldAlert} />
    </section>}
  </div>
}

function Stat({ label, value, icon: Icon }: { label: string; value: number | string; icon: typeof BadgeCheck }) {
  return <article className="rounded-xl border border-border bg-[#090e1b] p-4"><div className="flex justify-between text-xs text-muted">{label}<Icon size={15} aria-hidden="true" /></div><p className="mt-4 font-mono text-2xl font-semibold">{typeof value === 'number' ? value.toLocaleString() : value}</p></article>
}

function StatsSkeleton() { return <div aria-label="Loading campaign statistics" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{[0, 1, 2, 3, 4].map((i) => <PanelSkeleton key={i} rows={1} />)}</div> }
