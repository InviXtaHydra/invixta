import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import type { Cart } from '../../api/types'
import { AuthContext } from '../../auth/useAuth'
import { CartContext, type CartValue } from '../../cart/useCart'
import { emma } from '../../test/render'
import { CheckoutPage } from './CheckoutPage'

const checkout = vi.fn()
vi.mock('../../api/endpoints', () => ({
  api: {
    shopInfo: async () => ({
      countries: { NL: 'Netherlands', DE: 'Germany' },
      free_shipping_from: '50.00',
      personalization_price: '15.00',
      shipping: [
        { method: 'standard', cost: '4.95', countries: ['NL', 'DE'] },
        { method: 'express', cost: '12.45', countries: ['NL'] },
      ],
      payment_methods: ['ideal', 'bancontact'],
    }),
    quote: async () => ({ subtotal: '84.95', shipping_cost: '0', total: '84.95' }),
    checkout: (...args: unknown[]) => checkout(...args),
  },
}))

const cartWithShirt: Cart = {
  token: null,
  items: [
    {
      id: 1, variant_id: 12, product_slug: 'fc-dijkstad-home-26-27', product_name: 'FC Dijkstad Home Shirt 26/27', category: 'home',
      season: '26/27', team: null, size: 'L', quantity: 1, unit_price: '84.95', line_total: '84.95', personalization_name: 'DE VRIES',
      personalization_number: 10, stock: 2,
    },
  ],
  item_count: 1,
  subtotal: '84.95',
  shipping_estimate: '0',
  free_shipping_remaining: '0',
}

function renderCheckout(cart: Cart, refresh: () => Promise<void>) {
  const value: CartValue = {
    cart, loading: false, busy: false, drawerOpen: false, openDrawer: () => {}, closeDrawer: () => {},
    add: async () => {}, update: async () => {}, remove: async () => {}, refresh,
  }
  const auth = { user: emma, checking: false, login: async () => emma, register: async () => emma, logout: () => {} }
  return render(
    <MemoryRouter initialEntries={['/checkout']}>
      <AuthContext.Provider value={auth}>
        <CartContext.Provider value={value}>
          <Routes>
            <Route path="/checkout" element={<CheckoutPage />} />
            <Route path="/pay/:id" element={<p>Payment page</p>} />
            <Route path="/cart" element={<p>Cart page</p>} />
          </Routes>
        </CartContext.Provider>
      </AuthContext.Provider>
    </MemoryRouter>,
  )
}

describe('CheckoutPage', () => {
  it('places the order and goes to the payment page, also when the cart is emptied right after', async () => {
    checkout.mockResolvedValue({ order: { id: 10023 }, payment: { id: 31 } })
    // Regression: refreshing the (now empty) cart used to redirect to /cart instead of the payment page.
    const refresh = vi.fn(async () => {})
    renderCheckout(cartWithShirt, refresh)

    expect(await screen.findByText('Size L, DE VRIES 10')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Street and house number'), 'Lindelaan 12')
    await userEvent.type(screen.getByLabelText('Postcode'), '3511 AB')
    await userEvent.type(screen.getByLabelText('City'), 'Utrecht')
    await userEvent.click(screen.getByRole('radio', { name: /Bancontact/ }))
    await userEvent.click(screen.getByRole('button', { name: /Place order/ }))

    expect(await screen.findByText('Payment page')).toBeInTheDocument()
    expect(checkout).toHaveBeenCalledWith({
      name: 'Emma de Vries', street: 'Lindelaan 12', postcode: '3511 AB', city: 'Utrecht', country: 'NL',
      shipping_method: 'standard', payment_method: 'bancontact',
    })
    expect(refresh).toHaveBeenCalled()
  })

  it('needs a full address and only offers express where it exists', async () => {
    renderCheckout(cartWithShirt, async () => {})
    await userEvent.click(await screen.findByRole('button', { name: /Place order/ }))
    expect(screen.getByRole('alert')).toHaveTextContent('Fill in your name and full address')
    await userEvent.selectOptions(screen.getByLabelText(/Country/), 'DE')
    expect(screen.getByRole('radio', { name: /Express/ })).toBeDisabled()
  })
})
