import { Shirt, SlidersHorizontal, X } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { api, type ProductQuery } from '../../api/endpoints'
import type { ProductCategory } from '../../api/types'
import { EmptyState, ErrorState, Skeleton } from '../../components/feedback'
import { Pagination } from '../../components/Pagination'
import { Crest } from '../../components/shop/Crest'
import { ProductGrid } from '../../components/shop/ProductCard'
import { Button, Select } from '../../components/ui'
import { useApi } from '../../lib/useApi'

const PAGE_SIZE = 24
const CATEGORIES: { value: ProductCategory; label: string }[] = [
  { value: 'home', label: 'Home shirts' },
  { value: 'away', label: 'Away shirts' },
  { value: 'retro', label: 'Retro' },
  { value: 'training', label: 'Training' },
  { value: 'kids', label: 'Kids' },
  { value: 'accessory', label: 'Accessories' },
]
const SIZES = ['S', 'M', 'L', 'XL', 'XXL', '116', '128', '140', '152', '164']
const PRICES = [
  { value: '', label: 'Any price' },
  { value: '0-30', label: 'Up to €30' },
  { value: '30-50', label: '€30 to €50' },
  { value: '50-1000', label: '€50 and more' },
]
const SORTS = [
  { value: 'popular', label: 'Most popular' },
  { value: 'new', label: 'Newest' },
  { value: 'price_asc', label: 'Price: low to high' },
  { value: 'price_desc', label: 'Price: high to low' },
]

export function ShopPage() {
  const [params, setParams] = useSearchParams()
  const [filtersOpen, setFiltersOpen] = useState(false)
  const get = (key: string) => params.get(key) ?? ''
  const [minPrice, maxPrice] = get('price') ? get('price').split('-').map(Number) : [undefined, undefined]
  const offset = Number(get('offset') || 0)
  const filters: ProductQuery = {
    category: get('category') as ProductCategory | '',
    team: get('team') || undefined,
    league: get('league') || undefined,
    size: get('size') || undefined,
    q: get('q') || undefined,
    min_price: minPrice,
    max_price: maxPrice,
    on_sale: get('on_sale') === 'true',
    sort: (get('sort') || 'popular') as ProductQuery['sort'],
    limit: PAGE_SIZE,
    offset,
  }
  const key = params.toString()
  const products = useApi(() => api.products(filters), [key])
  const leagues = useApi(() => api.leagues(), [])
  const team = leagues.data?.flatMap((l) => l.teams).find((t) => t.slug === filters.team)

  function set(next: Record<string, string>) {
    const merged = new URLSearchParams(params)
    for (const [k, v] of Object.entries(next)) {
      if (v) merged.set(k, v)
      else merged.delete(k)
    }
    if (!('offset' in next)) merged.delete('offset')
    setParams(merged, { replace: true })
  }

  const active = ['category', 'team', 'league', 'size', 'price', 'on_sale', 'q'].filter((k) => get(k))
  const title = team?.name ?? CATEGORIES.find((c) => c.value === filters.category)?.label ?? (filters.q ? `Results for "${filters.q}"` : 'All products')

  const filterPanel = (
    <div className="space-y-6">
      <FilterGroup label="Category">
        <RadioList name="category" value={get('category')} onChange={(v) => set({ category: v })} options={[{ value: '', label: 'Everything' }, ...CATEGORIES]} />
      </FilterGroup>
      <FilterGroup label="Club">
        <Select aria-label="Club" value={get('team')} onChange={(e) => set({ team: e.target.value })}>
          <option value="">All clubs</option>
          {leagues.data?.map((league) => (
            <optgroup key={league.name} label={league.name}>
              {league.teams.map((t) => (
                <option key={t.slug} value={t.slug}>
                  {t.name}
                </option>
              ))}
            </optgroup>
          ))}
        </Select>
      </FilterGroup>
      <FilterGroup label="League">
        <RadioList
          name="league"
          value={get('league')}
          onChange={(v) => set({ league: v })}
          options={[{ value: '', label: 'Both leagues' }, ...(leagues.data ?? []).map((l) => ({ value: l.name, label: l.name }))]}
        />
      </FilterGroup>
      <FilterGroup label="Size in stock">
        <div className="flex flex-wrap gap-1.5">
          {SIZES.map((size) => (
            <button
              key={size}
              type="button"
              aria-pressed={get('size') === size}
              onClick={() => set({ size: get('size') === size ? '' : size })}
              className={`min-w-11 rounded-md border px-2 py-1.5 text-sm ${
                get('size') === size ? 'border-brand bg-brand text-brand-ink' : 'border-line-strong hover:border-ink-2'
              }`}
            >
              {size}
            </button>
          ))}
        </div>
      </FilterGroup>
      <FilterGroup label="Price">
        <RadioList name="price" value={get('price')} onChange={(v) => set({ price: v })} options={PRICES} />
      </FilterGroup>
      <label className="flex items-center gap-2 text-sm font-medium">
        <input type="checkbox" checked={get('on_sale') === 'true'} onChange={(e) => set({ on_sale: e.target.checked ? 'true' : '' })} className="size-4 accent-[var(--brand)]" />
        Only items on sale
      </label>
    </div>
  )

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-4">
          {team && <Crest team={team} className="size-16" />}
          <div>
            <h1 className="font-display text-4xl font-extrabold uppercase tracking-wide sm:text-5xl">{title}</h1>
            <p className="text-sm text-muted">
              {team ? `${team.league}, ${team.city}, founded in ${team.founded}. ` : ''}
              {products.data ? `${products.data.total} products` : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" className="lg:hidden" onClick={() => setFiltersOpen(true)}>
            <SlidersHorizontal aria-hidden className="size-4" /> Filters{active.length ? ` (${active.length})` : ''}
          </Button>
          <label htmlFor="sort" className="sr-only">
            Sort
          </label>
          <Select id="sort" value={filters.sort} onChange={(e) => set({ sort: e.target.value })} className="w-48">
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </Select>
        </div>
      </header>

      {active.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          {active.map((k) => (
            <button key={k} type="button" onClick={() => set({ [k]: '' })} className="flex items-center gap-1 rounded-full bg-surface-2 px-3 py-1 text-sm hover:bg-line">
              {k === 'on_sale'
                ? 'On sale'
                : k === 'team'
                  ? (team?.name ?? get(k))
                  : k === 'price'
                    ? PRICES.find((p) => p.value === get(k))?.label
                    : k === 'category'
                      ? CATEGORIES.find((c) => c.value === get(k))?.label
                      : get(k)}
              <X aria-hidden className="size-3.5" />
              <span className="sr-only">Remove filter</span>
            </button>
          ))}
          <button type="button" onClick={() => setParams({}, { replace: true })} className="px-2 text-sm font-medium text-brand hover:underline">
            Clear all
          </button>
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-[14rem_1fr]">
        <aside aria-label="Filters" className="hidden lg:block">
          {filterPanel}
        </aside>
        <div>
          {products.loading && !products.data ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {Array.from({ length: 8 }, (_, i) => (
                <Skeleton key={i} className="aspect-[4/5]" />
              ))}
            </div>
          ) : products.error ? (
            <ErrorState error={products.error} onRetry={products.reload} />
          ) : !products.data?.items.length ? (
            <EmptyState icon={Shirt} title="Nothing matches these filters" action={<Button onClick={() => setParams({}, { replace: true })}>Clear the filters</Button>}>
              Try another size or club, or ask our assistant.
            </EmptyState>
          ) : (
            <div aria-busy={products.loading} className={products.loading ? 'opacity-60' : ''}>
              <ProductGrid products={products.data.items} />
              <div className="mt-8">
                <Pagination total={products.data.total} limit={PAGE_SIZE} offset={offset} onChange={(o) => set({ offset: String(o) })} />
              </div>
            </div>
          )}
        </div>
      </div>

      {filtersOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Filters">
          <button type="button" aria-label="Close filters" className="absolute inset-0 bg-black/40" onClick={() => setFiltersOpen(false)} />
          <div className="absolute inset-y-0 right-0 w-80 max-w-[90vw] overflow-y-auto overscroll-contain bg-surface p-5 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-display text-2xl font-bold uppercase">Filters</h2>
              <button type="button" onClick={() => setFiltersOpen(false)} className="rounded-md p-2 hover:bg-surface-2">
                <X aria-hidden className="size-5" />
                <span className="sr-only">Close filters</span>
              </button>
            </div>
            {filterPanel}
            <Button className="mt-6 w-full" onClick={() => setFiltersOpen(false)}>
              Show {products.data?.total ?? ''} products
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <fieldset>
      <legend className="mb-2 font-display text-sm font-bold uppercase tracking-wide text-muted">{label}</legend>
      {children}
    </fieldset>
  )
}

function RadioList({ name, value, options, onChange }: { name: string; value: string; options: { value: string; label: string }[]; onChange: (v: string) => void }) {
  return (
    <div className="space-y-1">
      {options.map((o) => (
        <label key={o.value} className="flex cursor-pointer items-center gap-2 text-sm">
          <input type="radio" name={name} value={o.value} checked={value === o.value} onChange={() => onChange(o.value)} className="size-4 accent-[var(--brand)]" />
          {o.label}
        </label>
      ))}
    </div>
  )
}
