import { ArrowDownRight, ArrowUpRight, BadgeCheck, MousePointer2, ShieldAlert, ShieldCheck } from 'lucide-react'
import type { DashboardStats } from '@/api/dashboard'

export type RiskLevel = 'low' | 'medium' | 'high'

function getRiskLevel(rate: number): RiskLevel {
  return rate < 20 ? 'low' : rate < 50 ? 'medium' : 'high'
}

export function KpiRiskBadge({ rate }: { rate: number }) {
  const level = getRiskLevel(rate)
  const Icon = level === 'low' ? BadgeCheck : level === 'medium' ? ArrowUpRight : ShieldAlert
  return <span aria-label={`${level} risk`} className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold capitalize risk-${level}`}><Icon size={14} aria-hidden="true" />{level} risk</span>
}

export function KpiCards({ stats }: { stats: DashboardStats }) {
  const items = [
    { label: 'Total clicks analyzed', value: stats.total, detail: 'All time', icon: MousePointer2, color: 'text-accent' },
    { label: 'Fraudulent clicks', value: stats.fraud, detail: stats.total ? `${stats.fraud_rate.toFixed(1)}% of total` : 'No clicks yet', icon: ShieldAlert, color: 'text-danger' },
    { label: 'Genuine clicks', value: stats.legit, detail: stats.total ? `${Math.max(0, 100 - stats.fraud_rate).toFixed(1)}% of total` : 'No clicks yet', icon: BadgeCheck, color: 'text-success' },
  ]
  return <section aria-label="Click metrics" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    {items.map(({ label, value, detail, icon: Icon, color }) => <article key={label} className="rounded-2xl border border-border bg-[#090e1b] p-5">
      <div className="flex items-center justify-between"><span className="text-xs font-medium text-muted">{label}</span><Icon className={color} size={18} aria-hidden="true" /></div>
      <p className="mt-4 font-mono text-3xl font-semibold tracking-tight">{value.toLocaleString()}</p><p className="mt-1 text-xs text-muted">{detail}</p>
    </article>)}
    <article className="rounded-2xl border border-border bg-[#090e1b] p-5">
      <div className="flex items-center justify-between"><span className="text-xs font-medium text-muted">Fraud rate</span><ShieldCheck className="text-warning" size={18} aria-hidden="true" /></div>
      <div className="mt-4 flex items-center gap-3"><p className="font-mono text-3xl font-semibold tracking-tight">{stats.fraud_rate.toFixed(1)}%</p><KpiRiskBadge rate={stats.fraud_rate} /></div>
      <p className="mt-1 text-xs text-muted">{stats.fraud_rate >= 20 ? <ArrowUpRight className="mr-1 inline text-warning" size={13} /> : <ArrowDownRight className="mr-1 inline text-success" size={13} />}Share of analyzed clicks</p>
    </article>
  </section>
}
