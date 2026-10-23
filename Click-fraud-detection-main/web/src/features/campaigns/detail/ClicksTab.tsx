import { useQuery } from '@tanstack/react-query'
import { BadgeCheck, ChevronLeft, ChevronRight, CircleHelp, ShieldAlert } from 'lucide-react'
import { useState } from 'react'
import { getCampaignClicks } from '@/api/campaigns'
import { EmptyState, LoadingSkeleton, QueryError } from '@/components/DataState'
import { Button } from '@/components/ui/button'

const PAGE_SIZE = 25

export function ClicksTab({ id }: { id: number }) {
  const [page, setPage] = useState(0)
  const clicks = useQuery({ queryKey: ['campaign-clicks', id, page], queryFn: () => getCampaignClicks(id, PAGE_SIZE, page * PAGE_SIZE), refetchOnWindowFocus: true })
  if (clicks.isPending) return <div className="rounded-2xl border border-border bg-[#090e1b] p-5"><LoadingSkeleton rows={7} /></div>
  if (clicks.isError) return <QueryError error={clicks.error} retry={() => void clicks.refetch()} />
  if (clicks.data.length === 0 && page === 0) return <EmptyState title="No clicks recorded yet" detail="Click records will appear here when this campaign receives traffic." />
  return <section className="overflow-hidden rounded-2xl border border-border bg-[#090e1b]">
    <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-white/[0.025] text-xs uppercase tracking-wide text-muted"><tr>
      <th className="px-4 py-3 font-medium">Time</th><th className="px-4 py-3 font-medium">IP address</th><th className="px-4 py-3 font-medium">Classification</th><th className="px-4 py-3 font-medium">Risk score</th><th className="px-4 py-3 font-medium">Decision</th><th className="px-4 py-3 font-medium">Reason codes</th><th className="px-4 py-3 font-medium">Model</th>
    </tr></thead><tbody className="divide-y divide-border">{clicks.data.map((click) => {
      const codes = parseReasonCodes(click.reason_codes)
      const fraud = click.classification === 'FRAUD'
      const legit = click.classification === 'VALID'
      const Icon = fraud ? ShieldAlert : legit ? BadgeCheck : CircleHelp
      const label = fraud ? 'Fraud' : legit ? 'Genuine' : 'Suspicious'
      return <tr key={click.id}>
        <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-muted">{formatTimestamp(click.created_at)}</td>
        <td className="px-4 py-3 font-mono text-xs">{click.ip_address}</td>
        <td className="px-4 py-3"><span className={`inline-flex items-center gap-1.5 ${fraud ? 'text-danger' : legit ? 'text-success' : 'text-warning'}`}><Icon size={14} aria-hidden="true" />{label}</span></td>
        <td className="px-4 py-3 font-mono text-xs">{click.score == null ? '—' : click.score.toFixed(3)}</td>
        <td className="px-4 py-3 text-xs">{click.decision ?? '—'}</td>
        <td className="px-4 py-3">{codes.length ? <div className="flex max-w-64 flex-wrap gap-1">{codes.map((code) => <span key={code} className="rounded-md border border-border bg-white/[0.03] px-1.5 py-0.5 font-mono text-[10px] text-muted">{code}</span>)}</div> : <span className="text-muted">—</span>}</td>
        <td className="px-4 py-3 text-xs text-muted">{click.model_version ?? '—'}</td>
      </tr>
    })}</tbody></table></div>
    <div className="flex items-center justify-between border-t border-border px-4 py-3 text-xs text-muted"><span>Page {page + 1} · {clicks.data.length} records</span><div className="flex gap-2"><Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((current) => current - 1)}><ChevronLeft size={14} /> Previous</Button><Button variant="outline" size="sm" disabled={clicks.data.length < PAGE_SIZE} onClick={() => setPage((current) => current + 1)}>Next <ChevronRight size={14} /></Button></div></div>
  </section>
}

function parseReasonCodes(value: string[] | string | null): string[] {
  if (Array.isArray(value)) return value
  if (!value) return []
  try { const parsed: unknown = JSON.parse(value); return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : [] }
  catch { return [] }
}

function formatTimestamp(value: string | null): string {
  if (!value) return '—'
  const normalized = /^\d{4}-\d\d-\d\d \d\d/.test(value) ? `${value.replace(' ', 'T')}Z` : value
  const date = new Date(normalized)
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString()
}
