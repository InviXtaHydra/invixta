import { ChevronDown, Menu, Search, ShoppingBag, UserRound, X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router'
import { api } from '../../api/endpoints'
import { useAuth } from '../../auth/useAuth'
import { useCart } from '../../cart/useCart'
import { useApi } from '../../lib/useApi'
import { CartDrawer } from './CartDrawer'
import { ChatWidgetProvider } from './ChatWidget'
import { Crest } from './Crest'
import { CURRENT_YEAR } from '../../lib/format'

const CATEGORIES = [
  { to: '/shop?category=home', label: 'Home shirts' },
  { to: '/shop?category=away', label: 'Away shirts' },
  { to: '/shop?category=retro', label: 'Retro' },
  { to: '/shop?category=training', label: 'Training' },
  { to: '/shop?category=kids', label: 'Kids' },
  { to: '/shop?category=accessory', label: 'Accessories' },
]

export function Wordmark({ inverted = false }: { inverted?: boolean }) {
  return (
    <Link to="/" className={`flex items-center gap-2 ${inverted ? 'text-night-ink' : 'text-ink'}`}>
      <img src="/favicon.svg" alt="" className="size-8" />
      <span className="font-display text-2xl font-extrabold uppercase tracking-wide">Invixta</span>
    </Link>
  )
}

function SearchBox({ onDone }: { onDone?: () => void }) {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  function submit(event: FormEvent) {
    event.preventDefault()
    navigate(q.trim() ? `/shop?q=${encodeURIComponent(q.trim())}` : '/shop')
    onDone?.()
  }
  return (
    <form onSubmit={submit} role="search" className="relative">
      <label htmlFor="shop-search" className="sr-only">
        Search shirts and clubs
      </label>
      <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
      <input
        id="shop-search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search shirts or clubs"
        className="w-full rounded-full border border-white/15 bg-night-2 py-2 pl-9 pr-4 text-sm text-night-ink placeholder:text-white/50 focus:border-brand focus:outline-none"
      />
    </form>
  )
}

function ClubsMenu() {
  const leagues = useApi(() => api.leagues(), [])
  const [open, setOpen] = useState(false)
  return (
    <div className="relative" onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onMouseEnter={() => setOpen(true)}
        className="flex items-center gap-1 rounded-md px-3 py-2 text-sm font-semibold uppercase tracking-wide text-white/75 hover:text-white"
      >
        Clubs <ChevronDown aria-hidden className="size-3.5" />
      </button>
      {open && leagues.data && (
        <div className="absolute left-0 top-full z-40 w-[34rem] rounded-xl border border-line bg-surface p-5 shadow-xl">
          <div className="grid grid-cols-2 gap-6">
            {leagues.data.map((league) => (
              <div key={league.name}>
                <p className="mb-2 font-display text-sm font-bold uppercase tracking-wide text-muted">{league.name}</p>
                <ul className="space-y-1">
                  {league.teams.map((team) => (
                    <li key={team.slug}>
                      <Link
                        to={`/shop?team=${team.slug}`}
                        onClick={() => setOpen(false)}
                        className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-surface-2"
                      >
                        <Crest team={team} className="size-6" />
                        {team.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function ShopLayout() {
  const { user } = useAuth()
  const { cart, openDrawer } = useCart()
  const [menuOpen, setMenuOpen] = useState(false)
  const count = cart?.item_count ?? 0

  return (
    <ChatWidgetProvider>
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <div className="bg-accent px-4 py-1.5 text-center text-xs font-medium text-accent-ink">
        Free shipping from €50 in the EU, 30 days to return, name &amp; number printing on every shirt
      </div>
      <header className="sticky top-0 z-30 border-b border-white/10 bg-night text-night-ink">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 sm:px-6">
          <button type="button" className="rounded-md p-2 text-white/80 hover:bg-white/10 lg:hidden" onClick={() => setMenuOpen(true)}>
            <Menu aria-hidden className="size-5" />
            <span className="sr-only">Open menu</span>
          </button>
          <Wordmark inverted />
          <nav aria-label="Shop" className="ml-4 hidden items-center lg:flex">
            <ClubsMenu />
            {CATEGORIES.map((c) => (
              <NavLink
                key={c.to}
                to={c.to}
                className={({ isActive }) =>
                  `rounded-md px-3 py-2 text-sm font-semibold uppercase tracking-wide hover:text-white ${isActive ? 'text-white' : 'text-white/75'}`
                }
              >
                {c.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto hidden w-64 md:block">
            <SearchBox />
          </div>
          <div className="ml-auto flex items-center gap-1 md:ml-2">
            <Link
              to={user ? '/dashboard' : '/login'}
              className="flex items-center gap-2 rounded-md p-2 text-sm font-medium text-white/80 hover:bg-white/10 hover:text-white"
            >
              <UserRound aria-hidden className="size-5" />
              <span className="hidden sm:inline">{user ? (user.name?.split(' ')[0] ?? 'Account') : 'Sign in'}</span>
            </Link>
            <button type="button" onClick={openDrawer} className="relative rounded-md p-2 text-white/80 hover:bg-white/10 hover:text-white">
              <ShoppingBag aria-hidden className="size-5" />
              <span className="sr-only">Cart, {count} items</span>
              {count > 0 && (
                <span aria-hidden className="absolute -right-0.5 -top-0.5 grid min-w-5 place-items-center rounded-full bg-accent px-1 text-[11px] font-bold text-accent-ink">
                  {count}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button type="button" className="absolute inset-0 bg-black/40" onClick={() => setMenuOpen(false)} aria-label="Close menu" />
          <div className="absolute inset-y-0 left-0 flex w-80 max-w-[85vw] flex-col gap-4 overflow-y-auto overscroll-contain bg-surface p-5 shadow-xl">
            <div className="flex items-center justify-between">
              <Wordmark />
              <button type="button" onClick={() => setMenuOpen(false)} className="rounded-md p-2 hover:bg-surface-2">
                <X aria-hidden className="size-5" />
                <span className="sr-only">Close menu</span>
              </button>
            </div>
            <SearchBox onDone={() => setMenuOpen(false)} />
            <nav aria-label="Shop" className="flex flex-col">
              <Link to="/shop" onClick={() => setMenuOpen(false)} className="py-2 font-display text-xl font-bold uppercase">
                All products
              </Link>
              {CATEGORIES.map((c) => (
                <Link key={c.to} to={c.to} onClick={() => setMenuOpen(false)} className="py-2 font-display text-xl font-bold uppercase">
                  {c.label}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      )}

      <main id="main" className="flex-1">
        <Outlet />
      </main>

      <footer className="mt-16 border-t-4 border-accent bg-night text-night-ink">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:grid-cols-3 sm:px-6">
          <div>
            <Wordmark inverted />
            <p className="mt-3 max-w-xs text-sm text-white/70">
              Football shirts of the Lage Landen League and the Noordzee Divisie, printed with your name.
            </p>
          </div>
          <div className="text-sm">
            <p className="mb-2 font-display text-base font-bold uppercase tracking-wide">Help</p>
            <ul className="space-y-1.5 text-white/80">
              <li>
                <Link to="/dashboard" className="hover:underline">
                  Your orders
                </Link>
              </li>
              <li>
                <Link to="/chat" className="hover:underline">
                  Ask the assistant: delivery, returns, sizes
                </Link>
              </li>
              <li>
                <Link to="/tickets" className="hover:underline">
                  Contact support
                </Link>
              </li>
            </ul>
          </div>
          <div className="text-sm text-white/70 sm:text-right">
            <p>Secure payment with iDEAL, Bancontact, card or PayPal</p>
            <p className="mt-1">Prices include VAT</p>
            <p className="mt-4 text-xs text-white/50">© {CURRENT_YEAR} Invixta</p>
          </div>
        </div>
      </footer>
      <CartDrawer />
    </div>
    </ChatWidgetProvider>
  )
}
