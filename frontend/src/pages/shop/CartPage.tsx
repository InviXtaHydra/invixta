import { ShoppingBag } from 'lucide-react'
import { useCart } from '../../cart/useCart'
import { EmptyState, SkeletonRows } from '../../components/feedback'
import { CartLines, FreeShippingBar } from '../../components/shop/CartLines'
import { ButtonLink } from '../../components/ui'
import { formatMoney } from '../../lib/format'

export function CartPage() {
  const { cart, loading } = useCart()
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <h1 className="mb-6 font-display text-4xl font-extrabold uppercase tracking-wide">Your cart</h1>
      {loading ? (
        <SkeletonRows rows={3} />
      ) : !cart?.items.length ? (
        <EmptyState icon={ShoppingBag} title="Your cart is empty" action={<ButtonLink to="/shop">Browse the shirts</ButtonLink>}>
          Pick a club, choose your size and add your name.
        </EmptyState>
      ) : (
        <div className="grid gap-8 lg:grid-cols-[1fr_20rem]">
          <section aria-label="Items" className="rounded-xl border border-line bg-surface px-4">
            <CartLines lines={cart.items} />
          </section>
          <aside className="h-fit space-y-4 rounded-xl border border-line bg-surface p-5">
            <FreeShippingBar remaining={cart.free_shipping_remaining} />
            <dl className="space-y-1.5 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted">Subtotal ({cart.item_count} items)</dt>
                <dd className="tabular-nums">{formatMoney(cart.subtotal)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">Shipping to the Netherlands</dt>
                <dd className="tabular-nums">{Number(cart.shipping_estimate) === 0 ? 'Free' : formatMoney(cart.shipping_estimate)}</dd>
              </div>
            </dl>
            <ButtonLink to="/checkout" className="w-full !py-3 font-display text-lg uppercase tracking-wide">
              Checkout
            </ButtonLink>
            <p className="text-xs text-muted">The final shipping cost depends on your country and delivery method.</p>
          </aside>
        </div>
      )}
    </div>
  )
}
