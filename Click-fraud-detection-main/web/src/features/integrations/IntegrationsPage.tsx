import { useQuery } from '@tanstack/react-query'
import { BarChart3, Cable, LayoutDashboard, Radio, Send } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCampaign } from '@/api/campaigns'
import { LoadingSkeleton, QueryError } from '@/components/DataState'
import { Button } from '@/components/ui/button'
import { OverviewSection } from './OverviewSection'
import { ConnectionsSection } from './ConnectionsSection'
import { AnalyticsSection } from './AnalyticsSection'
import { SimulatorSection } from './SimulatorSection'

type Tab='overview'|'connections'|'analytics'|'simulator'
const tabs:{key:Tab;label:string;icon:typeof Radio}[]=[{key:'overview',label:'Overview',icon:LayoutDashboard},{key:'connections',label:'Connections',icon:Cable},{key:'analytics',label:'Analytics',icon:BarChart3},{key:'simulator',label:'Simulator',icon:Send}]
export default function IntegrationsPage(){const id=Number(useParams().campaignId);const [tab,setTab]=useState<Tab>('overview');const campaign=useQuery({queryKey:['campaign',id],queryFn:()=>getCampaign(id),enabled:id>0,refetchOnWindowFocus:true});if(!id)return <QueryError error={new Error('Invalid campaign.')} retry={()=>undefined}/>;if(campaign.isPending)return <LoadingSkeleton rows={5}/>;if(campaign.isError)return <QueryError error={campaign.error} retry={()=>void campaign.refetch()}/>;return <div className="space-y-6"><header><Link to={`/campaigns/${id}`} className="text-xs text-accent hover:underline">{campaign.data.name}</Link><h1 className="mt-1 font-heading text-3xl font-bold">Platform Integrations</h1><p className="mt-2 text-sm text-muted">Google Ads and Facebook Ads event monitoring. Events are manually supplied or simulated; there are no direct ad-platform connections.</p></header><nav aria-label="Integration sections" className="flex flex-wrap gap-2">{tabs.map(({key,label,icon:Icon})=><Button key={key} variant={tab===key?'default':'outline'} aria-pressed={tab===key} onClick={()=>setTab(key)}><Icon size={15}/>{label}</Button>)}</nav>{tab==='overview'&&<OverviewSection campaignId={id}/ >}{tab==='connections'&&<ConnectionsSection/>}{tab==='analytics'&&<AnalyticsSection campaignId={id}/ >}{tab==='simulator'&&<SimulatorSection campaignId={id}/>}</div>}
