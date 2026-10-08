import { Lock } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { api } from '../../api/endpoints'
import type { PaymentMethod, ShippingMethod } from '../../api/types'
import { useUser } from '../../auth/useAuth'
import { useCart } from '../../cart/useCart'
import { SkeletonRows } from '../../components/feedback'
import { Button, Field, Input, Select } from '../../components/ui'
import { formatMoney } from '../../lib/format'
import { printing } from '../../lib/shop'
import { useApi } from '../../lib/useApi'

const PAYMENT_LABEL: Record<PaymentMethod, string> = { ideal: 'iDEAL', bancontact: 'Bancontact', card: 'Credit card', paypal: 'PayPal' }

export function CheckoutPage() {
  const user = useUser()
  const navigate = useNavigate()
  const { cart, loading, refresh } = useCart()
  const info = useApi(() => api.shopInfo(), [])
  const [form, setForm] = useState({ name: user.name ?? '', street: '', postcode: '', city: '', country: 'NL' })
  const [method, setMethod] = useState<ShippingMethod>('standard')
  const [payment, setPayment] = useState<PaymentMethod>('ideal')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [placedPayment, setPlacedPayment] = useState<number | null>(null)
  const express = info.data?.shipping.find((s) => s.method === 'express')
  const expressAllowed = express?.countries.includes(form.country) ?? false
  const shippingMethod: ShippingMethod = method === 'express' && !expressAllowed ? 'standard' : method
  const quote = useApi(() => api.quote(form.country, shippingMethod), [form.country, shippingMethod, cart?.subtotal ?? ''])

  if (placedPayment) return <Navigate to={`/pay/${placedPayment}`} replace /> // the cart is empty now: don't send them to /cart
  if (user.role !== 'CUSTOMER') return <Navigate to="/dashboard" replace />
  if (loading || info.loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <SkeletonRows rows={6} />
      </div>
    )
  }
  if (!cart?.items.length) return <Navigate to="/cart" replace />

  const missing = !form.name.trim() || form.street.trim().length < 3 || form.postcode.trim().length < 3 || form.city.trim().length < 2
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [key]: e.target.value })

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (missing) return setError('Fill in your name and full address')
    setBusy(true)
    setError(null)
    try {
      const result = await api.checkout({ ...form, shipping_method: shippingMethod, payment_method: payment })
      setPlacedPayment(result.payment.id)
      navigate(`/pay/${result.payment.id}`)
      void refresh() // the server emptied the cart
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The order could not be placed')
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <h1 className="mb-6 font-display text-4xl font-extrabold uppercase tracking-wide">Checkout</h1>
      <form onSubmit={submit} noValidate className="grid gap-8 lg:grid-cols-[1fr_22rem]">
        <div className="space-y-8">
          {error && (
            <p role="alert" className="rounded-lg bg-bad-soft px-4 py-3 text-sm text-bad">
              {error}
            </p>
          )}
          <section aria-labelledby="address-title" className="rounded-xl border border-line bg-surface p-5">
            <h2 id="address-title" className="mb-4 font-display text-xl font-bold uppercase tracking-wide">
              Delivery address
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Field label="Full name">{(p) => <Input {...p} autoComplete="name" value={form.name} onChange={set('name')} />}</Field>
              </div>
              <div className="sm:col-span-2">
                <Field label="Street and house number">
                  {(p) => <Input {...p} autoComplete="street-address" value={form.street} onChange={set('street')} />}
                </Field>
              </div>
              <Field label="Postcode">{(p) => <Input {...p} autoComplete="postal-code" value={form.postcode} onChange={set('postcode')} />}</Field>
              <Field label="City">{(p) => <Input {...p} autoComplete="address-level2" value={form.city} onChange={set('city')} />}</Field>
              <div className="sm:col-span-2">
                <Field label="Country" hint="We deliver within the EU">
                  {(p) => (
                    <Select {...p} autoComplete="country" value={form.country} onChange={set('country')}>
                      {Object.entries(info.data?.countries ?? {}).map(([code, name]) => (
                        <option key={code} value={code}>
                          {name}
                        </option>
                      ))}
                    </Select>
                  )}
                </Field>
              </div>
            </div>
          </section>

          <fieldset className="rounded-xl border border-line bg-surface p-5">
            <legend className="px-1 font-display text-xl font-bold uppercase tracking-wide">Delivery</legend>
            <div className="mt-2 grid gap-2">
              <Choice name="shipping" checked={shippingMethod === 'standard'} onChange={() => setMethod('standard')} title="Standard" note="1 to 3 working days in the Benelux, 3 to 7 elsewhere in the EU" />
              <Choice
                name="shipping"
                checked={shippingMethod === 'express'}
                disabled={!expressAllowed}
                onChange={() => setMethod('express')}
                title="Express"
                note={expressAllowed ? `Next working day, ${formatMoney(Number(express?.cost ?? 0) - Number(info.data?.shipping[0].cost ?? 0))} extra` : 'Only in the Netherlands and Belgium'}
              />
            </div>
          </fieldset>

          <fieldset className="rounded-xl border border-line bg-surface p-5">
            <legend className="px-1 font-display text-xl font-bold uppercase tracking-wide">Payment</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {(info.data?.payment_methods ?? []).map((m) => (
                <Choice key={m} name="payment" checked={payment === m} onChange={() => setPayment(m)} title={PAYMENT_LABEL[m]} />
              ))}
            </div>
            <p className="mt-3 text-xs text-muted">
              Kopbal is a fictional shop: you'll pay on a simulated payment page and no money moves.
            </p>
          </fieldset>
        </div>

        <aside className="h-fit space-y-4 rounded-xl border border-line bg-surface p-5 lg:sticky lg:top-24">
          <h2 className="font-display text-xl font-bold uppercase tracking-wide">Your order</h2>
          <ul className="space-y-2 text-sm">
            {cart.items.map((line) => (
              <li key={line.id} className="flex justify-between gap-3">
                <span className="min-w-0">
                  {line.quantity} × {line.product_name}
                  <span className="block text-xs text-muted">
                    Size {line.size}
                    {printing(line) ? `, ${printing(line)}` : ''}
                  </span>
                </span>
                <span className="shrink-0 tabular-nums">{formatMoney(line.line_total)}</span>
              </li>
            ))}
          </ul>
          <dl className="space-y-1.5 border-t border-line pt-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted">Subtotal</dt>
              <dd className="tabular-nums">{formatMoney(cart.subtotal)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Shipping</dt>
              <dd className="tabular-nums">{quote.data ? (Number(quote.data.shipping_cost) === 0 ? 'Free' : formatMoney(quote.data.shipping_cost)) : '…'}</dd>
            </div>
            <div className="flex justify-between border-t border-line pt-2 text-base font-semibold">
              <dt>Total</dt>
              <dd className="font-display text-2xl font-bold tabular-nums">{quote.data ? formatMoney(quote.data.total) : '…'}</dd>
            </div>
          </dl>
          <Button type="submit" disabled={busy} className="w-full !py-3 font-display text-lg uppercase tracking-wide">
            <Lock aria-hidden className="size-4" /> {busy ? 'Placing your order…' : 'Place order and pay'}
          </Button>
        </aside>
      </form>
    </div>
  )
}

function Choice({ name, checked, onChange, title, note, disabled }: { name: string; checked: boolean; onChange: () => void; title: string; note?: string; disabled?: boolean }) {
  return (
    <label className={`flex items-start gap-3 rounded-lg border p-3 ${disabled ? 'cursor-not-allowed opacity-55' : 'cursor-pointer'} ${checked ? 'border-brand bg-brand-soft/50' : 'border-line-strong'}`}>
      <input type="radio" name={name} checked={checked} disabled={disabled} onChange={onChange} className="mt-1 size-4 accent-[var(--brand)]" />
      <span>
        <span className="block font-medium">{title}</span>
        {note && <span className="text-sm text-muted">{note}</span>}
      </span>
    </label>
  )
}
