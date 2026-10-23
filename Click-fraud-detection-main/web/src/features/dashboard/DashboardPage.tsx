import { useQueries, useQueryClient } from '@tanstack/react-query'
import { ArrowUpRight, BadgeCheck, RefreshCw, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getDashboardAlerts, getDashboardStats, getRecentClicks } from '@/api/dashboard'
import { getCampaigns } from '@/api/campaigns'
import { Button } from '@/components/ui/button'
import { EmptyState, PanelSkeleton, QueryError } from '@/components/DataState'
import { AlertsStrip } from './AlertsStrip'
import { CampaignSummary } from './CampaignSummary'
import { ClickTrendChart } from './ClickTrendChart'
import { FraudDonut } from './FraudDonut'
import { KpiCards } from './KpiCards'

export default function DashboardPage() {
  const queryClient = useQueryClient()
  const [stats, clicks, alerts, campaigns] = useQueries({ queries: [
    { queryKey: ['dashboard-stats'], queryFn: getDashboardStats, refetchOnWindowFocus: true },
    { queryKey: ['dashboard-clicks'], queryFn: getRecentClicks, refetchOnWindowFocus: true },
    { queryKey: ['dashboard-alerts'], queryFn: getDashboardAlerts, refetchOnWindowFocus: true },
    { queryKey: ['campaigns'], queryFn: getCampaigns, refetchOnWindowFocus: true },
  ] })

  return <div className="space-y-7">
    <div className="flex flex-wrap items-end justify-between gap-4"><div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent">Overview</p>
      <h1 className="font-heading text-3xl font-bold tracking-tight">Operations dashboard</h1>
      <p className="mt-2 text-sm text-muted">Real-time overview of click fraud detection activity.</p></div>
      <Button variant="outline" onClick={() => void queryClient.invalidateQueries()}><RefreshCw size={15} /> Refresh data</Button>
    </div>
    {alerts.isPending ? <PanelSkeleton rows={1} /> : alerts.isError ? <QueryError error={alerts.error} retry={() => void alerts.refetch()} /> : <AlertsStrip alerts={alerts.data} />}
    {stats.isPending ? <MetricSkeleton /> : stats.isError ? <QueryError error={stats.error} retry={() => void stats.refetch()} /> : <KpiCards stats={stats.data} />}
    {campaigns.isPending ? <PanelSkeleton rows={2} /> : campaigns.isError ? <QueryError error={campaigns.error} retry={() => void campaigns.refetch()} />
      : campaigns.data.length === 0 ? <EmptyState title="Create your first campaign" detail="Add a campaign to start monitoring its click activity." action={<Button asChild><Link to="/campaigns">Create campaign</Link></Button>} />
        : <CampaignSummary campaigns={campaigns.data.slice(0, 4)} />}
    <div className="grid gap-5 xl:grid-cols-[minmax(280px,0.8fr)_minmax(0,1.6fr)]">
      {stats.isPending ? <PanelSkeleton rows={4} /> : stats.isError ? <QueryError error={stats.error} retry={() => void stats.refetch()} /> : <FraudDonut stats={stats.data} />}
      {clicks.isPending ? <PanelSkeleton rows={4} /> : clicks.isError ? <QueryError error={clicks.error} retry={() => void clicks.refetch()} /> : <ClickTrendChart clicks={clicks.data} />}
    </div>
    {clicks.isSuccess && clicks.data.length > 0 && <section className="rounded-2xl border border-border bg-[#090e1b] p-5">
      <div className="mb-4 flex items-center justify-between"><div><h2 className="font-heading text-lg font-semibold">Recent activity</h2><p className="mt-1 text-xs text-muted">Latest click scores from your account</p></div><Link className="inline-flex items-center gap-1 text-xs text-accent hover:underline" to="/history">View history <ArrowUpRight size={13} /></Link></div>
      <div className="divide-y divide-border">{clicks.data.slice(0, 6).map((click) => {
        const fraud = click.decision === 'BLOCK' || click.result.toLowerCase() === 'fraud'
        const Icon = fraud ? ShieldAlert : BadgeCheck
        return <div key={click.id} className="flex items-center justify-between gap-4 py-3 text-sm"><div className="flex min-w-0 items-center gap-3"><Icon size={16} className={fraud ? 'shrink-0 text-danger' : 'shrink-0 text-success'} /><span className="font-mono text-xs text-muted">{click.ip_address}</span><span className={fraud ? 'text-danger' : 'text-success'}>{fraud ? 'Fraud' : 'Genuine'}</span></div><span className="shrink-0 font-mono text-xs text-muted">{new Date(click.created_at).toLocaleTimeString()}</span></div>
      })}</div>
    </section>}
  </div>
}

function MetricSkeleton() {
  return <div aria-label="Loading dashboard metrics" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[0, 1, 2, 3].map((item) => <PanelSkeleton key={item} rows={1} />)}</div>
}
