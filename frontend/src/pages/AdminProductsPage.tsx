import { Search, Shirt } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api } from '../api/endpoints'
import type { AdminProduct } from '../api/types'
import { PageContainer } from '../components/AppShell'
import { EmptyState, ErrorState, SkeletonRows } from '../components/feedback'
import { Pagination } from '../components/Pagination'
import { useToast } from '../components/useToast'
import { Badge, Button, Dialog, Field, Input, PageHeader, Panel } from '../components/ui'
import { formatMoney } from '../lib/format'
import { useApi } from '../lib/useApi'

const PAGE_SIZE = 25

export function AdminProductsPage() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const offset = Number(params.get('offset') ?? 0)
  const state = useApi(() => api.adminProducts({ q: q || undefined, limit: PAGE_SIZE, offset }), [q, offset])
  const [search, setSearch] = useState(q)
  const [editing, setEditing] = useState<AdminProduct | null>(null)

  function submit(event: FormEvent) {
    event.preventDefault()
    setParams(search.trim() ? { q: search.trim() } : {}, { replace: true })
  }

  return (
    <PageContainer>
      <PageHeader
        title="Products"
        description="Prices, sales, visibility in the shop and stock per size. Changes are live in the shop straight away."
        actions={
          <form onSubmit={submit} role="search" className="relative w-64">
            <label htmlFor="product-search" className="sr-only">
              Search products
            </label>
            <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <Input id="product-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Club or product" className="pl-9" />
          </form>
        }
      />
      <Panel flush>
        {state.loading && !state.data ? (
          <SkeletonRows rows={8} />
        ) : state.error ? (
          <ErrorState error={state.error} onRetry={state.reload} />
        ) : !state.data?.items.length ? (
          <EmptyState icon={Shirt} title="No products found" />
        ) : (
          <div aria-busy={state.loading} className={state.loading ? 'opacity-60' : ''}>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <caption className="sr-only">Products</caption>
                <thead className="border-b border-line text-xs text-muted">
                  <tr>
                    <th scope="col" className="px-4 py-2.5 font-medium">Product</th>
                    <th scope="col" className="px-4 py-2.5 font-medium">Price</th>
                    <th scope="col" className="px-4 py-2.5 font-medium">Stock per size</th>
                    <th scope="col" className="px-4 py-2.5 text-right font-medium">Sold</th>
                    <th scope="col" className="px-4 py-2.5">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {state.data.items.map((product) => (
                    <tr key={product.id} className={product.is_active ? '' : 'bg-surface-2/60'}>
                      <td className="px-4 py-3">
                        <Link to={`/product/${product.slug}`} className="font-medium hover:underline">
                          {product.name}
                        </Link>
                        <span className="mt-0.5 flex gap-1.5">
                          {!product.is_active && <Badge tone="neutral">Hidden</Badge>}
                          {product.compare_at_price && <Badge tone="warn">On sale</Badge>}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 tabular-nums">
                        {formatMoney(product.price)}
                        {product.compare_at_price && <span className="ml-1.5 text-xs text-muted line-through">{formatMoney(product.compare_at_price)}</span>}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1.5">
                          {product.variants.map((v) => (
                            <StockInput key={v.id} productName={product.name} variant={v} onSaved={state.reload} />
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">{product.units_sold}</td>
                      <td className="px-4 py-3 text-right">
                        <Button variant="ghost" onClick={() => setEditing(product)}>
                          Edit
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              total={state.data.total}
              limit={PAGE_SIZE}
              offset={offset}
              onChange={(o) => setParams({ ...(q ? { q } : {}), offset: String(o) }, { replace: true })}
            />
          </div>
        )}
      </Panel>
      <EditProductDialog product={editing} onClose={() => setEditing(null)} onSaved={() => (setEditing(null), state.reload())} />
    </PageContainer>
  )
}

function StockInput({ productName, variant, onSaved }: { productName: string; variant: AdminProduct['variants'][number]; onSaved: () => void }) {
  const toast = useToast()
  const [value, setValue] = useState(String(variant.stock))
  const [saving, setSaving] = useState(false)

  async function save() {
    const stock = Number(value)
    if (value === String(variant.stock)) return
    if (!Number.isInteger(stock) || stock < 0) {
      toast('Stock must be 0 or more', 'error')
      setValue(String(variant.stock))
      return
    }
    setSaving(true)
    try {
      await api.updateStock(variant.id, stock)
      toast(`${productName}, size ${variant.size}: ${stock} in stock`)
      onSaved()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Stock could not be saved', 'error')
      setValue(String(variant.stock))
    } finally {
      setSaving(false)
    }
  }

  const low = Number(value) <= 3
  return (
    <label className={`flex items-center overflow-hidden rounded-md border text-xs ${low ? 'border-warn/50' : 'border-line-strong'}`}>
      <span className={`px-1.5 py-1 font-medium ${low ? 'bg-warn-soft text-warn' : 'bg-surface-2 text-ink-2'}`}>{variant.size}</span>
      <input
        aria-label={`Stock of ${productName} in size ${variant.size}`}
        inputMode="numeric"
        value={value}
        disabled={saving}
        onChange={(e) => setValue(e.target.value.replace(/\D/g, ''))}
        onBlur={() => void save()}
        onKeyDown={(e) => e.key === 'Enter' && (e.currentTarget as HTMLInputElement).blur()}
        className="w-12 bg-surface px-1.5 py-1 text-right tabular-nums focus:outline-none"
      />
    </label>
  )
}

function EditProductDialog({ product, onClose, onSaved }: { product: AdminProduct | null; onClose: () => void; onSaved: () => void }) {
  return (
    <Dialog open={product !== null} onClose={onClose} title={product ? `Edit ${product.name}` : 'Edit product'}>
      {product && <EditProductForm key={product.id} product={product} onClose={onClose} onSaved={onSaved} />}
    </Dialog>
  )
}

function EditProductForm({ product, onClose, onSaved }: { product: AdminProduct; onClose: () => void; onSaved: () => void }) {
  const toast = useToast()
  const [price, setPrice] = useState(product.price)
  const [compareAt, setCompareAt] = useState(product.compare_at_price ?? '')
  const [active, setActive] = useState(product.is_active)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (compareAt && Number(compareAt) <= Number(price)) return setError('The old price must be higher than the price')
    setBusy(true)
    setError(null)
    try {
      await api.updateProduct(product.id, { price, compare_at_price: compareAt || null, is_active: active })
      toast(`${product.name} saved`)
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The product could not be saved')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      {error && (
        <p role="alert" className="rounded-lg bg-bad-soft px-3 py-2 text-sm text-bad">
          {error}
        </p>
      )}
      <div className="grid grid-cols-2 gap-3">
        <Field label="Price (€)">{(p) => <Input {...p} inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />}</Field>
        <Field label="Old price (€)" hint="Filled in = on sale">
          {(p) => <Input {...p} inputMode="decimal" value={compareAt} onChange={(e) => setCompareAt(e.target.value)} placeholder="No sale" />}
        </Field>
      </div>
      <label className="flex items-center gap-2 text-sm font-medium">
        <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} className="size-4 accent-[var(--brand)]" />
        Show in the shop
      </label>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={busy}>
          {busy ? 'Saving…' : 'Save'}
        </Button>
      </div>
    </form>
  )
}
