import { Trash2 } from 'lucide-react'
import { Link } from 'react-router'
import type { CartLine } from '../../api/types'
import { useCart } from '../../cart/useCart'
import { formatMoney } from '../../lib/format'
import { printing } from '../../lib/shop'
import { ProductArt } from './ProductArt'
import { QuantityStepper } from './QuantityStepper'

/** The lines of the cart, used in the drawer and on the cart page. */
export function CartLines({ lines, onNavigate }: { lines: CartLine[]; onNavigate?: () => void }) {
  const { update, remove, busy } = useCart()
  return (
    <ul className="divide-y divide-line">
      {lines.map((line) => {
        const printed = printing(line)
        return (
          <li key={line.id} className="flex gap-3 py-4">
            <Link to={`/product/${line.product_slug}`} onClick={onNavigate} className="w-20 shrink-0 rounded-lg bg-surface-2 p-2">
              <ProductArt
                name={line.product_name}
                category={line.category}
                team={line.team}
                season={line.season}
                slug={line.product_slug}
                view={printed ? 'back' : 'front'}
                printName={line.personalization_name}
                printNumber={line.personalization_number}
              />
            </Link>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <Link to={`/product/${line.product_slug}`} onClick={onNavigate} className="font-medium leading-snug hover:underline">
                  {line.product_name}
                </Link>
                <span className="shrink-0 font-display text-lg font-bold tabular-nums">{formatMoney(line.line_total)}</span>
              </div>
              <p className="text-sm text-muted">
                Size {line.size}
                {printed && <>, printed: <span className="font-medium text-ink-2">{printed}</span></>}
              </p>
              <div className="mt-2 flex items-center justify-between">
                <QuantityStepper
                  label={`Quantity of ${line.product_name}`}
                  value={line.quantity}
                  max={Math.min(10, line.stock)}
                  disabled={busy}
                  onChange={(q) => void update(line.id, q).catch(() => {})}
                />
                <button
                  type="button"
                  onClick={() => void remove(line.id).catch(() => {})}
                  disabled={busy}
                  className="rounded-md p-2 text-muted hover:bg-surface-2 hover:text-bad"
                >
                  <Trash2 aria-hidden className="size-4" />
                  <span className="sr-only">Remove {line.product_name}</span>
                </button>
              </div>
            </div>
          </li>
        )
      })}
    </ul>
  )
}

export function FreeShippingBar({ remaining, threshold = 50 }: { remaining: string; threshold?: number }) {
  const left = Number(remaining)
  const progress = Math.min(100, ((threshold - left) / threshold) * 100)
  return (
    <div>
      <p className="text-sm text-ink-2">
        {left > 0 ? (
          <>
            Add <strong>{formatMoney(left)}</strong> more for free shipping
          </>
        ) : (
          <strong className="text-brand">You get free shipping</strong>
        )}
      </p>
      <div className="mt-1.5 h-1.5 rounded-full bg-line" aria-hidden>
        <div className="h-1.5 rounded-full bg-brand transition-all" style={{ width: `${progress}%` }} />
      </div>
    </div>
  )
}
