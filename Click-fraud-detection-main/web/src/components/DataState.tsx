import { AlertTriangle, LoaderCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return <div aria-label="Loading" className="animate-pulse space-y-3" role="status">
    {Array.from({ length: rows }, (_, index) => <div key={index} className="h-12 rounded-lg bg-white/[0.045]" />)}
  </div>
}

export function PanelSkeleton({ rows = 3 }: { rows?: number }) {
  return <div className="rounded-2xl border border-border bg-[#090e1b] p-5"><div className="mb-5 h-4 w-40 animate-pulse rounded bg-white/[0.06]" /><LoadingSkeleton rows={rows} /></div>
}

export function QueryError({ error, retry }: { error: unknown; retry: () => void }) {
  const detail = error instanceof Error ? error.message : 'The request could not be completed.'
  const unreachable = detail.toLowerCase().includes('unable to reach') || (error instanceof Error && 'status' in error && error.status === 0)
  return <div role="alert" className="flex min-h-40 flex-col items-center justify-center rounded-xl border border-danger/25 bg-danger/[0.045] p-6 text-center">
    <AlertTriangle className="mb-3 text-danger" size={21} />
    <p className="font-medium text-foreground">{unreachable ? 'API unreachable' : 'Could not load this data'}</p>
    <p className="mb-4 mt-1 max-w-xl text-sm text-muted">{detail}</p>
    <Button variant="outline" size="sm" onClick={retry}><LoaderCircle size={14} /> Retry</Button>
  </div>
}

export function EmptyState({ title, detail, action }: { title: string; detail?: string; action?: React.ReactNode }) {
  return <div className="flex min-h-40 flex-col items-center justify-center rounded-xl border border-dashed border-border px-5 py-8 text-center">
    <p className="font-medium text-foreground">{title}</p>{detail && <p className="mt-2 text-sm text-muted">{detail}</p>}{action && <div className="mt-4">{action}</div>}
  </div>
}
