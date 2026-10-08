import { ShoppingBag, X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { useCart } from '../../cart/useCart'
import { formatMoney } from '../../lib/format'
import { ButtonLink } from '../ui'
import { CartLines, FreeShippingBar } from './CartLines'

/** The cart as a panel that slides in from the right after adding something. */
export function CartDrawer() {
  const { cart, drawerOpen, closeDrawer } = useCart()
  const panel = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!drawerOpen) return
    panel.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && closeDrawer()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [drawerOpen, closeDrawer])

  if (!drawerOpen) return null
  const lines = cart?.items ?? []
  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="cart-title">
      <button type="button" aria-label="Close cart" className="absolute inset-0 bg-black/40" onClick={closeDrawer} />
      <div
        ref={panel}
        tabIndex={-1}
        className="absolute inset-y-0 right-0 flex w-full max-w-md flex-col bg-surface shadow-2xl outline-none motion-safe:animate-[slide-in_200ms_ease-out]"
      >
        <header className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 id="cart-title" className="font-display text-2xl font-bold uppercase tracking-wide">
            Your cart{cart?.item_count ? ` (${cart.item_count})` : ''}
          </h2>
          <button type="button" onClick={closeDrawer} className="rounded-md p-2 text-muted hover:bg-surface-2 hover:text-ink">
            <X aria-hidden className="size-5" />
            <span className="sr-only">Close cart</span>
          </button>
        </header>
        {lines.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
            <ShoppingBag aria-hidden className="mb-3 size-8 text-muted" />
            <p className="font-medium">Your cart is empty</p>
            <ButtonLink to="/shop" onClick={closeDrawer} className="mt-4">
              Browse the shirts
            </ButtonLink>
          </div>
        ) : (
          <>
            <div className="px-5 pt-4">
              <FreeShippingBar remaining={cart!.free_shipping_remaining} />
            </div>
            <div className="flex-1 overflow-y-auto px-5">
              <CartLines lines={lines} onNavigate={closeDrawer} />
            </div>
            <footer className="space-y-3 border-t border-line px-5 py-4">
              <div className="flex justify-between text-sm">
                <span className="text-muted">Subtotal</span>
                <span className="font-display text-xl font-bold tabular-nums">{formatMoney(cart!.subtotal)}</span>
              </div>
              <ButtonLink to="/checkout" onClick={closeDrawer} className="w-full !py-3 text-base">
                Checkout
              </ButtonLink>
              <ButtonLink to="/cart" onClick={closeDrawer} variant="ghost" className="w-full">
                View cart
              </ButtonLink>
            </footer>
          </>
        )}
      </div>
    </div>
  )
}
