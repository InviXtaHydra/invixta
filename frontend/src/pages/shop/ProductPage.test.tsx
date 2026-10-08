import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import type { Product } from '../../api/types'
import { CartContext, type CartValue } from '../../cart/useCart'
import { ProductPage } from './ProductPage'

const product: Product = {
  id: 1,
  slug: 'fc-dijkstad-home-26-27',
  name: 'FC Dijkstad Home Shirt 26/27',
  category: 'home',
  season: '26/27',
  price: '69.95',
  compare_at_price: null,
  discount_percent: null,
  personalizable: true,
  team: {
    slug: 'fc-dijkstad',
    name: 'FC Dijkstad',
    short_name: 'FCD',
    league: 'Lage Landen League',
    city: 'Dijkstad',
    founded: 1899,
    primary_color: '#C8102E',
    secondary_color: '#FFFFFF',
    pattern: 'stripes',
  },
  sizes_in_stock: ['L'],
  description: 'The home shirt.',
  variants: [
    { id: 11, size: 'M', sku: 'M', stock: 0 },
    { id: 12, size: 'L', sku: 'L', stock: 2 },
  ],
  personalization_price: '15.00',
}

vi.mock('../../api/endpoints', () => ({
  api: { product: async () => product, products: async () => ({ items: [], total: 0, limit: 5, offset: 0 }) },
}))

function renderPage(add: CartValue['add']) {
  const cart: CartValue = {
    cart: null,
    loading: false,
    busy: false,
    drawerOpen: false,
    openDrawer: () => {},
    closeDrawer: () => {},
    add,
    update: async () => {},
    remove: async () => {},
    refresh: async () => {},
  }
  return render(
    <MemoryRouter initialEntries={[`/product/${product.slug}`]}>
      <CartContext.Provider value={cart}>
        <Routes>
          <Route path="/product/:slug" element={<ProductPage />} />
        </Routes>
      </CartContext.Provider>
    </MemoryRouter>,
  )
}

describe('ProductPage', () => {
  it('needs a size, shows low stock, and adds a printed shirt with the right price', async () => {
    const add = vi.fn(async () => {})
    renderPage(add)
    const button = await screen.findByRole('button', { name: /Add to cart/ })
    expect(screen.getByRole('radio', { name: 'M, sold out' })).toBeDisabled()

    await userEvent.click(button)
    expect(screen.getByRole('alert')).toHaveTextContent('Choose a size first')
    expect(add).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('radio', { name: 'L' }))
    expect(screen.getByText('Only 2 left in L')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Name'), 'de vries')
    await userEvent.type(screen.getByLabelText('Number'), '10')
    expect(screen.getByRole('button', { name: /Add to cart, €84\.95/ })).toBeInTheDocument() // + €15 printing
    expect(screen.getByRole('img', { name: /back/ })).toHaveTextContent('DE VRIES') // live preview on the back

    await userEvent.click(screen.getByRole('button', { name: /Add to cart/ }))
    expect(add).toHaveBeenCalledWith({ variant_id: 12, quantity: 1, personalization_name: 'DE VRIES', personalization_number: 10 })
  })

  it('rejects characters that cannot be printed', async () => {
    const add = vi.fn(async () => {})
    renderPage(add)
    await userEvent.click(await screen.findByRole('radio', { name: 'L' }))
    await userEvent.type(screen.getByLabelText('Name'), 'abc<1>')
    expect(screen.getByText('Letters, spaces, dots and hyphens only')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Add to cart/ }))
    expect(add).not.toHaveBeenCalled()
  })
})
