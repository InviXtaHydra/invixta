import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router'
import { api } from '../../api/endpoints'
import type { Team } from '../../api/types'
import { SkeletonRows } from '../../components/feedback'
import { Crest } from '../../components/shop/Crest'
import { Jersey } from '../../components/shop/Jersey'
import { ProductGrid } from '../../components/shop/ProductCard'
import { useApi } from '../../lib/useApi'

function Section({ title, link, linkLabel, children }: { title: string; link: string; linkLabel: string; children: React.ReactNode }) {
  return (
    <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div className="mb-6 flex items-end justify-between gap-4">
        <h2 className="font-display text-3xl font-extrabold uppercase tracking-wide sm:text-4xl">{title}</h2>
        <Link to={link} className="flex shrink-0 items-center gap-1 text-sm font-semibold text-brand hover:underline">
          {linkLabel} <ArrowRight aria-hidden className="size-4" />
        </Link>
      </div>
      {children}
    </section>
  )
}

function Hero({ teams }: { teams: Team[] }) {
  // Three clubs side by side, the middle one larger, like shirts on a rail.
  const shown = teams.length >= 3 ? [teams[1], teams[0], teams[9] ?? teams[2]] : teams
  return (
    <section className="relative overflow-hidden bg-brand text-brand-ink">
      <div aria-hidden className="absolute inset-0 opacity-[0.08] [background:repeating-linear-gradient(90deg,#fff_0_60px,transparent_60px_120px)]" />
      <div className="relative mx-auto grid max-w-7xl items-center gap-8 px-4 py-12 sm:px-6 lg:grid-cols-[1fr_1.1fr] lg:py-20">
        <div>
          <p className="font-display text-lg font-bold uppercase tracking-[0.2em] text-accent">Season 26/27</p>
          <h1 className="mt-2 font-display text-6xl font-extrabold uppercase leading-[0.9] sm:text-7xl lg:text-8xl">
            Your name.
            <br />
            Your number.
          </h1>
          <p className="mt-5 max-w-md text-lg text-brand-ink/85">
            The new shirts of every club in the Lage Landen League and the Noordzee Divisie, printed with the name and number you
            choose.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/shop?category=home" className="rounded-lg bg-accent px-6 py-3 font-display text-lg font-bold uppercase tracking-wide text-accent-ink hover:brightness-95">
              Shop home shirts
            </Link>
            <Link to="/shop?on_sale=true" className="rounded-lg border border-white/40 px-6 py-3 font-display text-lg font-bold uppercase tracking-wide hover:bg-white/10">
              On sale
            </Link>
          </div>
        </div>
        <div className="flex items-end justify-center gap-2 sm:gap-4" aria-hidden>
          {shown.map((team, i) => (
            <Jersey
              key={team.slug}
              primary={team.primary_color}
              secondary={team.secondary_color}
              pattern={team.pattern}
              crest={team.short_name}
              view={i === 1 ? 'back' : 'front'}
              name={i === 1 ? 'KOPBAL' : null}
              number={i === 1 ? 10 : null}
              label=""
              className={`drop-shadow-2xl ${i === 1 ? 'w-[42%]' : 'w-[29%] -mb-2 opacity-90'}`}
            />
          ))}
        </div>
      </div>
    </section>
  )
}

const TILES = [
  { to: '/shop?category=home', label: 'Home shirts', note: 'New season 26/27' },
  { to: '/shop?category=away', label: 'Away shirts', note: 'The colours reversed' },
  { to: '/shop?category=retro', label: 'Retro', note: 'Classics from 1974 to 2002' },
  { to: '/shop?category=kids', label: 'Kids', note: 'Sizes 116 to 164' },
]

export function HomePage() {
  const leagues = useApi(() => api.leagues(), [])
  const bestsellers = useApi(() => api.products({ sort: 'popular', limit: 8, category: 'home' }), [])
  const onSale = useApi(() => api.products({ on_sale: true, limit: 4 }), [])
  const retro = useApi(() => api.products({ category: 'retro', limit: 4 }), [])
  const teams = leagues.data?.flatMap((l) => l.teams) ?? []

  return (
    <>
      <Hero teams={teams} />

      <section className="mx-auto grid max-w-7xl grid-cols-2 gap-3 px-4 pt-10 sm:px-6 lg:grid-cols-4">
        {TILES.map((tile) => (
          <Link key={tile.to} to={tile.to} className="group rounded-xl border border-line bg-surface p-5 hover:border-brand">
            <span className="block font-display text-2xl font-extrabold uppercase tracking-wide group-hover:text-brand">{tile.label}</span>
            <span className="text-sm text-muted">{tile.note}</span>
          </Link>
        ))}
      </section>

      <Section title="Best sellers" link="/shop?sort=popular" linkLabel="All products">
        {bestsellers.data ? <ProductGrid products={bestsellers.data.items} /> : <SkeletonRows rows={2} />}
      </Section>

      {onSale.data && onSale.data.items.length > 0 && (
        <Section title="On sale" link="/shop?on_sale=true" linkLabel="All deals">
          <ProductGrid products={onSale.data.items} />
        </Section>
      )}

      {teams.length > 0 && (
        <section className="border-y border-line bg-surface py-10">
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <h2 className="mb-6 font-display text-3xl font-extrabold uppercase tracking-wide">Shop by club</h2>
            <ul className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-6">
              {teams.map((team) => (
                <li key={team.slug}>
                  <Link to={`/shop?team=${team.slug}`} className="flex flex-col items-center gap-2 rounded-xl p-3 text-center hover:bg-surface-2">
                    <Crest team={team} className="size-14" />
                    <span className="text-sm font-medium leading-tight">{team.name}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {retro.data && (
        <Section title="Retro classics" link="/shop?category=retro" linkLabel="All retro shirts">
          <ProductGrid products={retro.data.items} />
        </Section>
      )}
    </>
  )
}
