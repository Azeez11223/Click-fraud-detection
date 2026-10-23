import { BadgeCheck, ShieldAlert } from 'lucide-react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { DashboardStats } from '@/api/dashboard'

export function FraudDonut({ stats }: { stats: DashboardStats }) {
  const data = [{ name: 'Genuine', value: stats.legit, color: '#34d399' }, { name: 'Fraud', value: stats.fraud, color: '#f87171' }]
  return <section className="rounded-2xl border border-border bg-[#090e1b] p-5">
    <div className="mb-2"><h2 className="font-heading text-lg font-semibold">Fraud distribution</h2><p className="mt-1 text-xs text-muted">Genuine and fraudulent click counts</p></div>
    {stats.total === 0 ? <div className="flex h-64 items-center justify-center text-sm text-muted">No click data yet</div> : <div className="h-64" aria-label={`Fraud ${stats.fraud}, genuine ${stats.legit}`}>
      <ResponsiveContainer width="100%" height="100%"><PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={62} outerRadius={88} paddingAngle={4} stroke="#090e1b">
          {data.map((item) => <Cell key={item.name} fill={item.color} />)}
        </Pie>
        <Tooltip contentStyle={{ background: '#0b1020', border: '1px solid #1e293b', borderRadius: 8 }} />
      </PieChart></ResponsiveContainer>
    </div>}
    {stats.total > 0 && <div className="flex justify-center gap-5 text-xs"><span className="inline-flex items-center gap-1.5 text-success"><BadgeCheck size={14} aria-hidden="true" /> Genuine · {stats.legit.toLocaleString()}</span><span className="inline-flex items-center gap-1.5 text-danger"><ShieldAlert size={14} aria-hidden="true" /> Fraud · {stats.fraud.toLocaleString()}</span></div>}
    {stats.review > 0 && <p className="mt-1 text-center text-xs text-muted">{stats.review.toLocaleString()} review clicks are tracked separately</p>}
  </section>
}
