import { useState } from 'react'
import { Activity, BarChart3, ChevronLeft, ChevronRight, CircleHelp, Clock3, LayoutDashboard, LogOut, Menu, MousePointerClick, Shield, ShieldCheck, X } from 'lucide-react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { RouteErrorBoundary } from './RouteErrorBoundary'

const items = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Campaigns', to: '/campaigns', icon: Activity },
  { label: 'IP Manager', to: '/ip-manager', icon: Shield },
  { label: 'Predict', to: '/predict', icon: MousePointerClick },
  { label: 'Analytics', to: '/analytics', icon: BarChart3 },
  { label: 'History', to: '/history', icon: Clock3 },
  { label: 'About', to: '/about', icon: CircleHelp },
]
const titles: Record<string, string> = Object.fromEntries(items.map(({ label, to }) => [to, label]))

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [userMenu, setUserMenu] = useState(false)
  const { user, logout } = useAuth()
  const location = useLocation()
  const title = location.pathname.endsWith('/live') ? 'Realtime monitor' : location.pathname.endsWith('/integrations') ? 'Platform integrations' : location.pathname.startsWith('/campaigns/') ? 'Campaign details' : titles[location.pathname] ?? 'Dashboard'

  return <div className="min-h-screen bg-background text-foreground">
    {mobileOpen && <button aria-label="Close navigation" className="fixed inset-0 z-30 bg-black/60 lg:hidden" onClick={() => setMobileOpen(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-border bg-sidebar transition-all ${collapsed ? 'w-[76px]' : 'w-[248px]'} ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
      <div className="flex h-[76px] items-center justify-between border-b border-border px-5">
        <Link to="/dashboard" className="flex items-center gap-3 overflow-hidden">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-accent/10 text-accent"><ShieldCheck size={20} /></span>
          {!collapsed && <span className="font-heading text-lg font-bold">AdShield</span>}
        </Link>
        <button className="text-muted lg:hidden" aria-label="Close menu" onClick={() => setMobileOpen(false)}><X size={18} /></button>
      </div>
      <nav aria-label="Main navigation" className="flex-1 space-y-1 px-3 py-6">
        {items.map(({ label, to, icon: Icon }) => <NavLink key={to} to={to} title={collapsed ? label : undefined} onClick={() => setMobileOpen(false)} className={({ isActive }) => `flex h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium transition ${isActive ? 'bg-accent/10 text-accent' : 'text-muted hover:bg-white/5 hover:text-foreground'}`}>
          <Icon size={18} className="shrink-0" />{!collapsed && <span>{label}</span>}
        </NavLink>)}
      </nav>
      <div className="hidden border-t border-border p-3 lg:block">
        <button className="flex h-10 w-full items-center justify-center rounded-lg text-muted hover:bg-white/5 hover:text-foreground" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? <ChevronRight size={18} /> : <><ChevronLeft size={18} /><span className="ml-2 text-xs">Collapse sidebar</span></>}
        </button>
      </div>
    </aside>
    <div className={`min-h-screen transition-[padding] ${collapsed ? 'lg:pl-[76px]' : 'lg:pl-[248px]'}`}>
      <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-border bg-background/90 px-5 backdrop-blur sm:px-8">
        <div className="flex items-center gap-3"><button aria-label="Open navigation" className="text-muted lg:hidden" onClick={() => setMobileOpen(true)}><Menu size={21} /></button>
          <div className="text-sm"><span className="text-muted">AdShield</span><span className="px-2 text-slate-700">/</span><span className="font-medium">{title}</span></div>
        </div>
        <div className="relative">
          <button className="flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-white/5" aria-expanded={userMenu} onClick={() => setUserMenu(!userMenu)}>
            <span className="grid h-8 w-8 place-items-center rounded-full bg-accent/10 text-xs font-semibold text-accent">{user?.name.slice(0, 1).toUpperCase()}</span>
            <span className="hidden max-w-40 text-left sm:block"><span className="block truncate text-sm font-medium">{user?.name}</span><span className="block truncate text-xs text-muted">{user?.email}</span></span>
          </button>
          {userMenu && <div className="absolute right-0 top-12 w-48 rounded-xl border border-border bg-[#0b1020] p-1 shadow-xl"><button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted hover:bg-white/5 hover:text-foreground" onClick={() => { logout(); setUserMenu(false) }}><LogOut size={16} /> Sign out</button></div>}
        </div>
      </header>
      <main className="mx-auto max-w-[1440px] p-5 sm:p-8"><RouteErrorBoundary><Outlet /></RouteErrorBoundary></main>
    </div>
  </div>
}
