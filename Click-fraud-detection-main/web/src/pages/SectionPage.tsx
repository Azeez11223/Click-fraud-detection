import { useLocation } from 'react-router-dom'

const descriptions: Record<string, string> = {
  '/campaigns': 'Create campaigns and inspect their click activity.',
  '/ip-manager': 'Manage the IP block and allow lists for your account.',
  '/predict': 'Submit a click signal for a risk assessment.',
  '/analytics': 'Explore campaign performance and fraud signals.',
  '/history': 'Review your recent click scoring history.',
  '/about': 'Learn about AdShield and how its risk estimates work.',
}

export default function SectionPage() {
  const { pathname } = useLocation()
  const title = pathname === '/ip-manager' ? 'IP Manager' : pathname.slice(1).replace(/(^|-)\w/g, (word) => word.toUpperCase())
  return <div className="max-w-3xl">
    <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent">Workspace</p>
    <h1 className="font-heading text-3xl font-bold tracking-tight">{title}</h1>
    <p className="mt-3 text-sm leading-6 text-muted">{descriptions[pathname]}</p>
    <div className="mt-8 rounded-xl border border-dashed border-border bg-[#090e1b]/60 p-8 text-center">
      <h2 className="font-heading text-lg font-semibold">Ready to connect</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">This section is scaffolded for the React migration. Its data view will appear here as the feature is ported from Streamlit.</p>
    </div>
  </div>
}
