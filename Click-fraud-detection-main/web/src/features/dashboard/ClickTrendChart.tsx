import { MousePointer2, ShieldAlert } from 'lucide-react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ClickRecord } from '@/api/dashboard'

interface TrendPoint { hour: number; label: string; clicks: number; fraud: number }

function groupClickTrend(clicks: ClickRecord[]): TrendPoint[] {
  const grouped = new Map<number, TrendPoint>()
  clicks.forEach((click) => {
    const value = click.created_at.includes('T') ? click.created_at : `${click.created_at.replace(' ', 'T')}Z`
    const date = new Date(value)
    if (Number.isNaN(date.valueOf())) return
    date.setMinutes(0, 0, 0)
    const hour = date.valueOf()
    const point = grouped.get(hour) ?? { hour, label: date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric' }), clicks: 0, fraud: 0 }
    point.clicks += 1
    if (click.decision === 'BLOCK' || click.result.toLowerCase() === 'fraud') point.fraud += 1
    grouped.set(hour, point)
  })
  return [...grouped.values()].sort((a, b) => a.hour - b.hour)
}

export function ClickTrendChart({ clicks }: { clicks: ClickRecord[] }) {
  const data = groupClickTrend(clicks)
  return <section className="rounded-2xl border border-border bg-[#090e1b] p-5">
    <div className="mb-2"><h2 className="font-heading text-lg font-semibold">Click activity</h2><p className="mt-1 text-xs text-muted">Recent click scores by hour</p></div>
    {data.length === 0 ? <div className="flex h-64 items-center justify-center text-sm text-muted">No click activity yet. Submit predictions to see trends.</div> : <div className="h-64" aria-label="Click activity trend">
      <ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 12, right: 12, left: -18, bottom: 0 }}>
        <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={20} />
        <YAxis allowDecimals={false} tick={{ fill: '#94a3b8', fontSize: 10 }} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={{ background: '#0b1020', border: '1px solid #1e293b', borderRadius: 8 }} />
        <Line type="monotone" dataKey="clicks" name="All clicks" stroke="#60a5fa" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="fraud" name="Fraud" stroke="#f87171" strokeWidth={2} dot={false} />
      </LineChart></ResponsiveContainer>
    </div>}
    {data.length > 0 && <div className="mt-2 flex justify-center gap-5 text-xs"><span className="inline-flex items-center gap-1.5 text-accent"><MousePointer2 size={13} aria-hidden="true" /> All clicks</span><span className="inline-flex items-center gap-1.5 text-danger"><ShieldAlert size={13} aria-hidden="true" /> Fraud</span></div>}
  </section>
}
