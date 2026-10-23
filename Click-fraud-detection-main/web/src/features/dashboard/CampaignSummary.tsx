import { AlertTriangle, ArrowUpRight, Megaphone } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Campaign } from '@/api/campaigns'

export function CampaignSummary({ campaigns }: { campaigns: Campaign[] }) {
  return <section>
    <div className="mb-3 flex items-center justify-between"><div><h2 className="font-heading text-lg font-semibold">Your campaigns</h2><p className="mt-1 text-xs text-muted">Quick overview of recent activity</p></div><Link className="inline-flex items-center gap-1 text-xs text-accent hover:underline" to="/campaigns">All campaigns <ArrowUpRight size={13} /></Link></div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {campaigns.map((campaign) => <Link to={`/campaigns/${campaign.id}`} key={campaign.id} className="rounded-2xl border border-border bg-[#090e1b] p-4 transition hover:border-accent/40">
        <div className="flex items-start justify-between gap-2"><div className="flex min-w-0 items-center gap-2"><Megaphone size={16} className="shrink-0 text-accent" /><h3 className="truncate text-sm font-semibold">{campaign.name}</h3></div><span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted">{campaign.status}</span></div>
        <div className="mt-5 flex items-end justify-between"><div><p className="font-mono text-2xl font-semibold">{campaign.click_count.toLocaleString()}</p><p className="mt-1 text-xs text-muted">clicks · {campaign.fraud_count} fraud</p></div>{campaign.fraud_count >= 10 && <span className="inline-flex items-center gap-1 rounded-full bg-danger/10 px-2 py-1 text-[10px] font-semibold text-danger"><AlertTriangle size={12} /> Fraud alert</span>}</div>
      </Link>)}
    </div>
  </section>
}
