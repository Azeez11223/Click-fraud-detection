import { ArrowUpRight, ShieldCheck, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function DashboardPage() {
  return <div className="space-y-8">
    <div><p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent">Overview</p>
      <h1 className="font-heading text-3xl font-bold tracking-tight sm:text-4xl">Your campaigns, protected.</h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">AdShield helps you spot suspicious clicks, understand risk signals, and keep campaign activity in view.</p>
    </div>
    <section className="grid gap-4 md:grid-cols-2">
      <Link to="/campaigns" className="group rounded-2xl border border-border bg-[#090e1b] p-6 transition hover:border-accent/50">
        <div className="mb-7 flex items-start justify-between"><span className="grid h-11 w-11 place-items-center rounded-xl bg-accent/10 text-accent"><ShieldCheck size={22} /></span><ArrowUpRight size={18} className="text-muted transition group-hover:text-accent" /></div>
        <h2 className="font-heading text-xl font-semibold">Campaigns</h2><p className="mt-2 text-sm leading-6 text-muted">Create and monitor your campaign activity.</p>
      </Link>
      <Link to="/predict" className="group rounded-2xl border border-border bg-[#090e1b] p-6 transition hover:border-accent/50">
        <div className="mb-7 flex items-start justify-between"><span className="grid h-11 w-11 place-items-center rounded-xl bg-success/10 text-success"><Sparkles size={22} /></span><ArrowUpRight size={18} className="text-muted transition group-hover:text-accent" /></div>
        <h2 className="font-heading text-xl font-semibold">Score a click</h2><p className="mt-2 text-sm leading-6 text-muted">Review a click signal with AdShield’s risk model.</p>
      </Link>
    </section>
    <p className="border-t border-border pt-5 text-xs leading-5 text-muted">AdShield is an assistive prototype. Risk classifications are estimates and do not replace ad platform enforcement.</p>
  </div>
}
