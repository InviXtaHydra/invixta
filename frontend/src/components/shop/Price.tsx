import { formatMoney } from '../../lib/format'

export function Price({ price, compareAt, size = 'md' }: { price: string; compareAt?: string | null; size?: 'md' | 'lg' }) {
  const big = size === 'lg'
  return (
    <span className="flex items-baseline gap-2">
      <span className={`font-display font-bold tabular-nums ${big ? 'text-3xl' : 'text-lg'} ${compareAt ? 'text-bad' : 'text-ink'}`}>
        {formatMoney(price)}
      </span>
      {compareAt && (
        <span className={`tabular-nums text-muted line-through ${big ? 'text-base' : 'text-sm'}`}>
          <span className="sr-only">was </span>
          {formatMoney(compareAt)}
        </span>
      )}
    </span>
  )
}
