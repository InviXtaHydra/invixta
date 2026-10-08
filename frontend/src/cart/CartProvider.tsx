import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getCartToken, getToken, setCartToken } from '../api/client'
import { api } from '../api/endpoints'
import type { Cart } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { useToast } from '../components/useToast'
import { CartContext, type AddToCart } from './useCart'

/** The current cart. Signed in with a guest cart in storage: its items move to the account cart first. */
async function loadCart(): Promise<Cart> {
  const guestToken = getCartToken()
  if (getToken() && guestToken) {
    const merged = await api.claimCart(guestToken)
    setCartToken(null)
    return merged
  }
  return api.cart()
}

/**
 * The cart for the whole app. Guests get a cart token from the server (kept in localStorage); when the
 * user signs in, the guest cart is merged into their account cart (POST /cart/claim).
 */
export function CartProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const toast = useToast()
  const [cart, setCart] = useState<Cart | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const apply = useCallback((next: Cart) => {
    if (next.token) setCartToken(next.token) // a new guest cart
    setCart(next)
  }, [])

  const refresh = useCallback(async () => {
    try {
      apply(await loadCart())
    } catch {
      setCart(null)
    }
  }, [apply])

  // Load the cart, and again when the user signs in or out.
  const userId = user?.id ?? null
  useEffect(() => {
    let current = true
    loadCart()
      .then((next) => current && apply(next))
      .catch(() => current && setCart(null))
      .finally(() => current && setLoading(false))
    return () => {
      current = false
    }
  }, [apply, userId])

  const run = useCallback(
    async (action: () => Promise<Cart>, success?: string) => {
      setBusy(true)
      try {
        apply(await action())
        if (success) toast(success)
      } catch (err) {
        toast(err instanceof Error ? err.message : 'The cart could not be updated', 'error')
        throw err
      } finally {
        setBusy(false)
      }
    },
    [apply, toast],
  )

  const value = useMemo(
    () => ({
      cart,
      loading,
      busy,
      drawerOpen,
      openDrawer: () => setDrawerOpen(true),
      closeDrawer: () => setDrawerOpen(false),
      add: async (item: AddToCart) => {
        await run(() => api.addToCart(item))
        setDrawerOpen(true)
      },
      update: (lineId: number, quantity: number) => run(() => api.updateCartItem(lineId, quantity)),
      remove: (lineId: number) => run(() => api.removeCartItem(lineId), 'Removed from your cart'),
      refresh,
    }),
    [cart, loading, busy, drawerOpen, run, refresh],
  )
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}
