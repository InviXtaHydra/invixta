import { createContext, useContext } from 'react'
import type { Cart } from '../api/types'

export interface AddToCart {
  variant_id: number
  quantity: number
  personalization_name?: string
  personalization_number?: number
}

export interface CartValue {
  cart: Cart | null
  loading: boolean
  /** true while an add/update/remove is in flight */
  busy: boolean
  drawerOpen: boolean
  openDrawer: () => void
  closeDrawer: () => void
  add: (item: AddToCart) => Promise<void>
  update: (lineId: number, quantity: number) => Promise<void>
  remove: (lineId: number) => Promise<void>
  refresh: () => Promise<void>
}

export const CartContext = createContext<CartValue | null>(null)

export function useCart(): CartValue {
  const value = useContext(CartContext)
  if (!value) throw new Error('useCart must be used inside <CartProvider>')
  return value
}
