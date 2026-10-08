import { ArrowLeft, MessageCircle, RotateCcw, Truck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { api } from '../../api/endpoints'
import type { Product } from '../../api/types'
import { useCart } from '../../cart/useCart'
import { ErrorState, Skeleton } from '../../components/feedback'
import { Price } from '../../components/shop/Price'
import { ProductArt } from '../../components/shop/ProductArt'
import { ProductGrid } from '../../components/shop/ProductCard'
import { QuantityStepper } from '../../components/shop/QuantityStepper'
import { useChatWidget } from '../../components/shop/useChatWidget'
import { Button, Field, Input } from '../../components/ui'
import { formatMoney } from '../../lib/format'
import { useApi } from '../../lib/useApi'

export function ProductPage() {
  const { slug = '' } = useParams()
  const product = useApi(() => api.product(slug), [slug])
  if (product.loading && !product.data) {
    return (
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-10 sm:px-6 lg:grid-cols-2">
        <Skeleton className="aspect-square" />
        <Skeleton className="h-96" />
      </div>
    )
  }
  if (product.error || !product.data) return <ErrorState error={product.error ?? new Error('Not found')} onRetry={product.reload} />
  // key: a new product starts with a fresh form
  return <ProductView key={product.data.slug} product={product.data} />
}

const NAME_PATTERN = /^[A-Za-zÀ-ÿ' .-]*$/

function ProductView({ product }: { product: Product }) {
  const { add, busy } = useCart()
  const { openChat } = useChatWidget()
  const firstInStock = product.variants.find((v) => v.stock > 0)
  const [variantId, setVariantId] = useState<number | null>(product.variants.length === 1 ? (firstInStock?.id ?? null) : null)
  const [quantity, setQuantity] = useState(1)
  const [printName, setPrintName] = useState('')
  const [printNumber, setPrintNumber] = useState('')
  const [view, setView] = useState<'front' | 'back'>('front')
  const [sizeError, setSizeError] = useState(false)
  const related = useApi(() => (product.team ? api.products({ team: product.team.slug, limit: 5 }) : Promise.resolve(null)), [product.team?.slug ?? ''])

  const variant = product.variants.find((v) => v.id === variantId)
  const name = printName.trim().toUpperCase()
  const number = printNumber === '' ? null : Number(printNumber)
  const nameError = name && !NAME_PATTERN.test(name) ? 'Letters, spaces, dots and hyphens only' : undefined
  const numberError = number !== null && (!Number.isInteger(number) || number < 0 || number > 99) ? 'A number from 0 to 99' : undefined
  const printed = Boolean(name) || number !== null
  const unit = Number(product.price) + (printed ? Number(product.personalization_price) : 0)
  const soldOut = !firstInStock

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!variant) return setSizeError(true)
    if (nameError || numberError) return
    await add({
      variant_id: variant.id,
      quantity,
      ...(name ? { personalization_name: name } : {}),
      ...(number !== null ? { personalization_number: number } : {}),
    }).catch(() => {})
  }

  const shownView = printed ? view : 'front'
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <Link to={product.team ? `/shop?team=${product.team.slug}` : '/shop'} className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeft aria-hidden className="size-4" /> {product.team ? product.team.name : 'All products'}
      </Link>
      <div className="grid gap-10 lg:grid-cols-2">
        <div>
          <div className="relative rounded-2xl bg-surface-2 p-8 sm:p-12">
            <ProductArt
              name={product.name}
              category={product.category}
              team={product.team}
              season={product.season}
              slug={product.slug}
              view={shownView}
              printName={name || null}
              printNumber={numberError ? null : number}
              className="mx-auto w-full max-w-md drop-shadow-xl"
            />
            {product.discount_percent && (
              <span className="absolute left-4 top-4 rounded-md bg-accent px-2.5 py-1 font-display text-lg font-bold text-accent-ink">
                −{product.discount_percent}%
              </span>
            )}
          </div>
          {product.personalizable && (
            <div className="mt-3 flex justify-center gap-2" role="group" aria-label="Show the shirt from">
              {(['front', 'back'] as const).map((side) => (
                <button
                  key={side}
                  type="button"
                  aria-pressed={shownView === side}
                  onClick={() => setView(side)}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium ${shownView === side ? 'bg-ink text-canvas' : 'bg-surface-2 text-ink-2 hover:bg-line'}`}
                >
                  {side === 'front' ? 'Front' : 'Back'}
                </button>
              ))}
            </div>
          )}
        </div>

        <form onSubmit={submit} className="flex flex-col" noValidate>
          {product.team && <p className="font-display text-lg font-bold uppercase tracking-wide text-brand">{product.team.name}</p>}
          <h1 className="font-display text-4xl font-extrabold uppercase leading-tight tracking-wide sm:text-5xl">{product.name}</h1>
          <div className="mt-3">
            <Price price={product.price} compareAt={product.compare_at_price} size="lg" />
          </div>

          <fieldset className="mt-8" aria-describedby={sizeError ? 'size-error' : undefined}>
            <legend className="mb-2 flex w-full items-baseline justify-between text-sm font-semibold">
              Size
              <button type="button" onClick={() => openChat(`Which size of the ${product.name} should I take? I'm usually a `)} className="text-xs font-medium text-brand hover:underline">
                Help with sizes
              </button>
            </legend>
            <div className="flex flex-wrap gap-2">
              {product.variants.map((v) => (
                <label key={v.id} className={`relative ${v.stock === 0 ? 'cursor-not-allowed' : 'cursor-pointer'}`}>
                  <input
                    type="radio"
                    name="size"
                    value={v.id}
                    disabled={v.stock === 0}
                    checked={variantId === v.id}
                    onChange={() => (setVariantId(v.id), setSizeError(false), setQuantity(1))}
                    className="peer sr-only"
                  />
                  <span
                    className={`grid min-w-14 place-items-center rounded-lg border px-3 py-2.5 font-medium peer-focus-visible:outline-2 peer-focus-visible:outline-brand ${
                      v.stock === 0
                        ? 'border-line text-muted line-through'
                        : variantId === v.id
                          ? 'border-brand bg-brand text-brand-ink'
                          : 'border-line-strong hover:border-ink-2'
                    }`}
                  >
                    {v.size}
                    {v.stock === 0 && <span className="sr-only">, sold out</span>}
                  </span>
                </label>
              ))}
            </div>
            {sizeError && (
              <p id="size-error" role="alert" className="mt-2 text-sm text-bad">
                Choose a size first
              </p>
            )}
            {variant && variant.stock > 0 && variant.stock <= 3 && <p className="mt-2 text-sm font-medium text-warn">Only {variant.stock} left in {variant.size}</p>}
          </fieldset>

          {product.personalizable && (
            <fieldset className="mt-6 rounded-xl border border-line bg-surface p-4">
              <legend className="px-1 text-sm font-semibold">
                Name &amp; number printing <span className="font-normal text-muted">(+{formatMoney(product.personalization_price)})</span>
              </legend>
              <div className="grid grid-cols-[1fr_6rem] gap-3">
                <Field label="Name" error={nameError} hint="Up to 12 letters">
                  {(props) => (
                    <Input
                      {...props}
                      value={printName}
                      maxLength={12}
                      onChange={(e) => (setPrintName(e.target.value), setView('back'))}
                      placeholder="DE VRIES"
                      className="uppercase"
                    />
                  )}
                </Field>
                <Field label="Number" error={numberError}>
                  {(props) => (
                    <Input
                      {...props}
                      value={printNumber}
                      inputMode="numeric"
                      maxLength={2}
                      onChange={(e) => (setPrintNumber(e.target.value.replace(/\D/g, '')), setView('back'))}
                      placeholder="10"
                    />
                  )}
                </Field>
              </div>
              <p className="mt-2 text-xs text-muted">Printed shirts are made for you, see the return rules below.</p>
            </fieldset>
          )}

          <div className="mt-6 flex items-center gap-3">
            <QuantityStepper label="Quantity" value={quantity} max={Math.min(10, variant?.stock ?? 10)} onChange={setQuantity} disabled={soldOut} />
            <Button type="submit" disabled={busy || soldOut} className="flex-1 !py-3 font-display text-lg uppercase tracking-wide">
              {soldOut ? 'Sold out' : `Add to cart, ${formatMoney(unit * quantity)}`}
            </Button>
          </div>

          <ul className="mt-6 space-y-2 text-sm text-ink-2">
            <li className="flex gap-2">
              <Truck aria-hidden className="mt-0.5 size-4 shrink-0 text-brand" /> Free shipping from €50, delivered in 1 to 3 working days in the Netherlands and Belgium
            </li>
            <li className="flex gap-2">
              <RotateCcw aria-hidden className="mt-0.5 size-4 shrink-0 text-brand" /> 30 days to return unprinted items
            </li>
            <li className="flex gap-2">
              <MessageCircle aria-hidden className="mt-0.5 size-4 shrink-0 text-brand" />
              <button type="button" onClick={() => openChat(`I have a question about the ${product.name}: `)} className="text-left hover:underline">
                A question about this product? Ask our assistant
              </button>
            </li>
          </ul>

          <div className="mt-8 border-t border-line pt-6">
            <h2 className="font-display text-xl font-bold uppercase tracking-wide">Details</h2>
            <p className="mt-2 leading-relaxed text-ink-2">{product.description}</p>
          </div>
        </form>
      </div>

      {related.data && related.data.items.filter((p) => p.slug !== product.slug).length > 0 && (
        <section className="mt-16">
          <h2 className="mb-6 font-display text-3xl font-extrabold uppercase tracking-wide">More from {product.team?.name}</h2>
          <ProductGrid products={related.data.items.filter((p) => p.slug !== product.slug).slice(0, 4)} />
        </section>
      )}
    </div>
  )
}
