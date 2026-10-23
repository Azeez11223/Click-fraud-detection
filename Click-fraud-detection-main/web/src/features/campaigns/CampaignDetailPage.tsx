import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowLeft, BadgeCheck, Cable, CircleDollarSign, Settings2, ShieldAlert, TableProperties } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCampaign } from '@/api/campaigns'
import { LoadingSkeleton, QueryError } from '@/components/DataState'
import { Button } from '@/components/ui/button'
import { ClicksTab } from './detail/ClicksTab'
import { EconomicsTab } from './detail/EconomicsTab'
import { OverviewTab } from './detail/OverviewTab'
import { SettingsTab } from './detail/SettingsTab'

export type CampaignTab = 'overview' | 'clicks' | 'economics' | 'settings'
const tabs: { id: CampaignTab; label: string; icon: typeof BadgeCheck }[] = [
  { id: 'overview', label: 'Overview', icon: BadgeCheck },
  { id: 'clicks', label: 'Clicks', icon: TableProperties },
  { id: 'economics', label: 'Economics & Threshold', icon: CircleDollarSign },
  { id: 'settings', label: 'Settings', icon: Settings2 },
]

export default function CampaignDetailPage() {
  const { campaignId } = useParams()
  const id = Number(campaignId)
  const [tab, setTab] = useState<CampaignTab>('overview')
  const campaignQuery = useQuery({ queryKey: ['campaign', id], queryFn: () => getCampaign(id), enabled: Number.isInteger(id) && id > 0, refetchOnWindowFocus: true })

  if (!Number.isInteger(id) || id <= 0) return <QueryError error={new Error('Campaign not found.')} retry={() => undefined} />
  if (campaignQuery.isPending) return <LoadingSkeleton rows={7} />
  if (campaignQuery.isError) return <QueryError error={campaignQuery.error} retry={() => void campaignQuery.refetch()} />
  const campaign = campaignQuery.data

  return <div className="space-y-6">
    <Link to="/campaigns" className="inline-flex items-center gap-2 text-sm text-muted hover:text-foreground"><ArrowLeft size={15} /> Back to campaigns</Link>
    <header className="flex flex-wrap items-start justify-between gap-4"><div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-accent">{campaign.platform} · {campaign.ad_type} · {campaign.purpose}</p>
      <h1 className="font-heading text-3xl font-bold">{campaign.name}</h1>
    </div><div className="flex flex-wrap items-center gap-2"><Link to={`/campaigns/${id}/live`} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border px-3 text-sm hover:bg-white/5"><Activity size={15}/>Live monitor</Link><Link to={`/campaigns/${id}/integrations`} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border px-3 text-sm hover:bg-white/5"><Cable size={15}/>Integrations</Link><span className="rounded-full border border-border px-3 py-1.5 text-xs font-medium">{campaign.status}</span></div></header>
    <div role="tablist" aria-label="Campaign details" className="flex gap-1 overflow-x-auto border-b border-border">
      {tabs.map(({ id: tabId, label, icon: Icon }) => <Button key={tabId} role="tab" aria-selected={tab === tabId} variant="ghost" className={`shrink-0 rounded-b-none ${tab === tabId ? 'border-b-2 border-accent text-accent' : 'text-muted'}`} onClick={() => setTab(tabId)}><Icon size={15} />{label}</Button>)}
    </div>
    {tab === 'overview' && <OverviewTab id={id} />}
    {tab === 'clicks' && <ClicksTab id={id} />}
    {tab === 'economics' && <EconomicsTab campaign={campaign} />}
    {tab === 'settings' && <SettingsTab campaign={campaign} />}
    <p className="border-t border-border pt-4 text-xs leading-5 text-muted"><ShieldAlert className="mr-1 inline text-warning" size={13} />Classification labels and threshold what-if results are estimates, not verified outcomes.</p>
  </div>
}
