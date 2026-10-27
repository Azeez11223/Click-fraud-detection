import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { flexRender, getCoreRowModel, getSortedRowModel, useReactTable, type ColumnDef, type SortingState } from '@tanstack/react-table'
import { ArrowDown, ArrowUp, ArrowUpDown, CircleAlert, Plus, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { deleteCampaign, getCampaigns, setCampaignStatus, type Campaign } from '@/api/campaigns'
import { ApiError } from '@/api/client'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { EmptyState, LoadingSkeleton, QueryError } from '@/components/DataState'
import { Button } from '@/components/ui/button'
import { CampaignForm } from './CampaignForm'

type Action = { id: number; name: string; kind: 'delete' } | { id: number; name: string; kind: 'status'; status: 'Active' | 'Paused' }

export default function CampaignsPage() {
  const client = useQueryClient()
  const navigate = useNavigate()
  const query = useQuery({ queryKey: ['campaigns'], queryFn: getCampaigns, refetchOnWindowFocus: true })
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [sorting, setSorting] = useState<SortingState>([{ id: 'name', desc: false }])
  const [createOpen, setCreateOpen] = useState(false)
  const [action, setAction] = useState<Action | null>(null)
  const [actionError, setActionError] = useState('')

  const actionMutation = useMutation({
    mutationFn: async (next: Action) => next.kind === 'delete' ? deleteCampaign(next.id) : setCampaignStatus(next.id, next.status),
    onMutate: async (next) => {
      await client.cancelQueries({ queryKey: ['campaigns'] })
      const previous = client.getQueryData<Campaign[]>(['campaigns'])
      client.setQueryData<Campaign[]>(['campaigns'], (current) => next.kind === 'delete'
        ? current?.filter((campaign) => campaign.id !== next.id)
        : current?.map((campaign) => campaign.id === next.id ? { ...campaign, status: next.status } : campaign))
      return { previous }
    },
    onError: (error, _next, context) => {
      if (context?.previous) client.setQueryData(['campaigns'], context.previous)
      setActionError(error instanceof ApiError ? error.message : 'Could not update this campaign. Please retry.')
    },
    // Keep the confirmation dialog from waiting on a follow-up list request.
    // The optimistic cache is already current; refresh it in the background.
    onSettled: () => { void client.invalidateQueries({ queryKey: ['campaigns'] }) },
  })

  const rows = (query.data ?? []).filter((campaign) => {
    const matchesText = `${campaign.name} ${campaign.platform} ${campaign.ad_type}`.toLowerCase().includes(search.toLowerCase())
    return matchesText && (status === 'all' || campaign.status === status)
  })
  const table = useReactTable({ data: rows, columns: columns(), state: { sorting }, onSortingChange: setSorting, getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel() })

  async function confirmAction() {
    if (!action) return
    setActionError('')
    try {
      await actionMutation.mutateAsync(action)
      const removed = action.kind === 'delete'
      setAction(null)
      if (removed && window.location.pathname === `/campaigns/${action.id}`) navigate('/campaigns')
    } catch { /* Mutation state rolls back the optimistic change and exposes an error below. */ }
  }

  return <div className="space-y-6">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent">Workspace</p><h1 className="font-heading text-3xl font-bold">Campaigns</h1><p className="mt-2 text-sm text-muted">Manage ad campaigns and monitor click activity.</p></div>
      <Button onClick={() => setCreateOpen(true)}><Plus size={16} /> New campaign</Button></header>
    {query.isPending ? <LoadingSkeleton rows={5} /> : query.isError ? <QueryError error={query.error} retry={() => void query.refetch()} /> : query.data.length === 0
      ? <EmptyState title="Create your first campaign" detail="Set up a campaign to start tracking clicks, costs, and fraud signals." action={<Button onClick={() => setCreateOpen(true)}><Plus size={15} /> New campaign</Button>} />
      : <>
        <CampaignTotals campaigns={query.data} />
        <section className="overflow-hidden rounded-2xl border border-border bg-[#090e1b]">
          <div className="flex flex-wrap items-center gap-3 border-b border-border p-4">
            <label className="relative min-w-[220px] flex-1"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" /><span className="sr-only">Search campaigns</span><input className="campaign-input pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search campaigns" /></label>
            <label className="sr-only" htmlFor="campaign-status">Filter by status</label><select id="campaign-status" className="campaign-input w-40" value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All statuses</option><option>Active</option><option>Paused</option><option>Completed</option></select>
          </div>
          <div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-white/[0.025] text-xs uppercase tracking-wide text-muted">{table.getHeaderGroups().map((group) => <tr key={group.id}>{group.headers.map((header) => <th key={header.id} className="px-4 py-3 font-medium">{header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>)}</thead>
            <tbody className="divide-y divide-border">{table.getRowModel().rows.map((row) => <tr key={row.id} className="hover:bg-white/[0.02]">{row.getVisibleCells().map((cell) => <td key={cell.id} className="px-4 py-4 align-middle">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody>
          </table></div>
          {rows.length === 0 && <p className="p-8 text-center text-sm text-muted">No campaigns match these filters.</p>}
        </section>
      </>}
    <CampaignDialog open={createOpen} onClose={() => setCreateOpen(false)} onCreated={async (id) => { await client.invalidateQueries({ queryKey: ['campaigns'] }); setCreateOpen(false); navigate(`/campaigns/${id}`) }} />
    <ConfirmDialog open={Boolean(action)} title={actionTitle(action)} detail={actionDetail(action)} confirmLabel={action?.kind === 'delete' ? 'Delete campaign' : action?.status === 'Paused' ? 'Pause campaign' : 'Resume campaign'} busy={actionMutation.isPending} error={actionError || undefined} onCancel={() => { setAction(null); setActionError('') }} onConfirm={() => void confirmAction()} />
  </div>

  function columns(): ColumnDef<Campaign>[] {
    return [
      { accessorKey: 'name', header: ({ column }) => <SortHeader title="Campaign" sorted={column.getIsSorted()} toggle={() => column.toggleSorting(column.getIsSorted() === 'asc')} />, cell: ({ row }) => <Link to={`/campaigns/${row.original.id}`} className="font-semibold hover:text-accent">{row.original.name}</Link> },
      { accessorKey: 'platform', header: ({ column }) => <SortHeader title="Platform" sorted={column.getIsSorted()} toggle={() => column.toggleSorting(column.getIsSorted() === 'asc')} /> },
      { accessorKey: 'status', header: ({ column }) => <SortHeader title="Status" sorted={column.getIsSorted()} toggle={() => column.toggleSorting(column.getIsSorted() === 'asc')} />, cell: ({ getValue }) => <span className="rounded-full border border-border px-2.5 py-1 text-xs">{getValue<string>()}</span> },
      { accessorKey: 'click_count', header: ({ column }) => <SortHeader title="Clicks" sorted={column.getIsSorted()} toggle={() => column.toggleSorting(column.getIsSorted() === 'asc')} /> },
      { accessorKey: 'fraud_count', header: ({ column }) => <SortHeader title="Fraud" sorted={column.getIsSorted()} toggle={() => column.toggleSorting(column.getIsSorted() === 'asc')} />, cell: ({ getValue }) => <span className="inline-flex items-center gap-1.5">{getValue<number>() >= 10 && <CircleAlert size={14} className="text-danger" />}<span>{getValue<number>()}</span></span> },
      { id: 'actions', header: 'Actions', enableSorting: false, cell: ({ row }) => <div className="flex items-center gap-2"><Button size="sm" variant="outline" onClick={() => setAction({ id: row.original.id, name: row.original.name, kind: 'status', status: row.original.status === 'Active' ? 'Paused' : 'Active' })}>{row.original.status === 'Active' ? 'Pause' : 'Resume'}</Button><Button size="sm" variant="ghost" className="text-danger hover:text-danger" onClick={() => setAction({ id: row.original.id, name: row.original.name, kind: 'delete' })}>Delete</Button></div> },
    ]
  }
}

function SortHeader({ title, sorted, toggle }: { title: string; sorted: false | 'asc' | 'desc'; toggle: () => void }) {
  const Icon = sorted === 'asc' ? ArrowUp : sorted === 'desc' ? ArrowDown : ArrowUpDown
  return <button className="inline-flex items-center gap-1.5" onClick={toggle}>{title}<Icon size={13} /></button>
}

function CampaignTotals({ campaigns }: { campaigns: Campaign[] }) {
  const totals = [{ label: 'Total campaigns', value: campaigns.length }, { label: 'Active', value: campaigns.filter((c) => c.status === 'Active').length }, { label: 'Total clicks', value: campaigns.reduce((n, c) => n + c.click_count, 0) }, { label: 'Fraud clicks', value: campaigns.reduce((n, c) => n + c.fraud_count, 0) }]
  return <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">{totals.map((item) => <div key={item.label} className="rounded-xl border border-border bg-[#090e1b] p-4"><p className="text-xs text-muted">{item.label}</p><p className="mt-2 font-mono text-2xl font-semibold">{item.value.toLocaleString()}</p></div>)}</div>
}

function CampaignDialog({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (id: number) => void }) {
  const dialog = useRef<HTMLElement>(null)
  useEffect(() => {
    if (!open) return
    dialog.current?.querySelector<HTMLElement>('input,select,button')?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'Tab') {
        const controls = dialog.current?.querySelectorAll<HTMLElement>('input:not([disabled]),select:not([disabled]),button:not([disabled]),a[href]')
        if (!controls?.length) return
        const first = controls[0]; const last = controls[controls.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])
  if (!open) return null
  return <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/70 p-4"><section ref={dialog} role="dialog" aria-modal="true" aria-labelledby="new-campaign-title" className="my-auto w-full max-w-2xl rounded-2xl border border-border bg-[#0a0f1d] p-6 shadow-2xl">
    <h2 id="new-campaign-title" className="font-heading text-2xl font-bold">New campaign</h2><p className="mb-5 mt-1 text-sm text-muted">Enter the campaign settings and cost assumptions.</p><CampaignForm onCancel={onClose} onCreated={onCreated} />
  </section></div>
}

function actionTitle(action: Action | null) { return action?.kind === 'delete' ? `Delete “${action.name}”?` : action?.status === 'Paused' ? `Pause “${action?.name}”?` : `Resume “${action?.name}”?` }
function actionDetail(action: Action | null) { return action?.kind === 'delete' ? 'This permanently removes the campaign and its associated click records.' : action?.status === 'Paused' ? 'New clicks will no longer be accepted until you resume this campaign.' : 'This campaign will accept new clicks again.' }
