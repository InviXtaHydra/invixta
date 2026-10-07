import {
  ChartColumn,
  FileText,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  Menu,
  MessageSquare,
  Package,
  UserRound,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { NavLink, Outlet } from 'react-router'
import type { Role } from '../api/types'
import { useAuth, useUser } from '../auth/useAuth'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  roles: Role[]
}

const ALL: Role[] = ['CUSTOMER', 'AGENT', 'ADMIN']
const NAV: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ALL },
  { to: '/chat', label: 'AI assistant', icon: MessageSquare, roles: ['CUSTOMER'] },
  { to: '/orders', label: 'Orders', icon: Package, roles: ALL },
  { to: '/tickets', label: 'Tickets', icon: LifeBuoy, roles: ALL },
  { to: '/admin/documents', label: 'Knowledge base', icon: FileText, roles: ['ADMIN'] },
  { to: '/admin/metrics', label: 'Metrics', icon: ChartColumn, roles: ['ADMIN'] },
  { to: '/profile', label: 'Profile', icon: UserRound, roles: ALL },
]

const ROLE_LABEL: Record<Role, string> = { CUSTOMER: 'Customer', AGENT: 'Support agent', ADMIN: 'Administrator' }

export function Logo({ inverted = false }: { inverted?: boolean }) {
  return (
    <span className={`flex items-center gap-2.5 font-semibold tracking-tight ${inverted ? 'text-brand-ink' : 'text-ink'}`}>
      <img src="/favicon.svg" alt="" className={`size-7 ${inverted ? 'rounded-lg ring-2 ring-white/40' : ''}`} />
      SupportAI
    </span>
  )
}

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const user = useUser()
  const { logout } = useAuth()
  return (
    <div className="flex h-full flex-col">
      <nav aria-label="Main" className="flex-1 space-y-0.5 px-3">
        {NAV.filter((item) => item.roles.includes(user.role)).map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive ? 'bg-brand-soft text-brand' : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <Icon aria-hidden className="size-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-line p-3">
        <div className="px-3 pb-2">
          <p className="truncate text-sm font-medium text-ink">{user.name ?? user.email}</p>
          <p className="truncate text-xs text-muted">
            {ROLE_LABEL[user.role]}
            {user.name ? `, ${user.email}` : ''}
          </p>
        </div>
        <button
          type="button"
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-ink-2 hover:bg-surface-2 hover:text-ink"
        >
          <LogOut aria-hidden className="size-4" />
          Sign out
        </button>
      </div>
    </div>
  )
}

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[15rem_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-line bg-surface lg:flex">
        <div className="px-6 py-5">
          <Logo />
        </div>
        <Navigation />
      </aside>

      {/* Mobile top bar + slide-over menu */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-surface/95 px-4 py-3 backdrop-blur lg:hidden">
        <Logo />
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          aria-expanded={menuOpen}
          aria-controls="mobile-menu"
          className="rounded-md p-2 text-ink-2 hover:bg-surface-2"
        >
          <Menu aria-hidden className="size-5" />
          <span className="sr-only">Open menu</span>
        </button>
      </header>
      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu" id="mobile-menu">
          <button type="button" className="absolute inset-0 bg-black/40" onClick={() => setMenuOpen(false)} aria-label="Close menu" />
          <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-surface shadow-xl">
            <div className="flex items-center justify-between px-5 py-4">
              <Logo />
              <button type="button" onClick={() => setMenuOpen(false)} className="rounded-md p-2 text-ink-2 hover:bg-surface-2">
                <X aria-hidden className="size-5" />
                <span className="sr-only">Close menu</span>
              </button>
            </div>
            <Navigation onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      )}

      <main id="main" className="min-w-0">
        <Outlet />
      </main>
    </div>
  )
}

/** Standard page width and padding. The chat page uses the full height instead. */
export function PageContainer({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</div>
}
