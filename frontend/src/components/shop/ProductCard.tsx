import { Link } from 'react-router'
import type { ProductSummary } from '../../api/types'
import { Price } from './Price'
import { ProductArt } from './ProductArt'

export function ProductCard({ product }: { product: ProductSummary }) {
  const soldOut = product.sizes_in_stock.length === 0
  return (
    <article className="group relative flex flex-col">
      <div className="relative overflow-hidden rounded-xl bg-surface-2 p-6 transition-colors group-hover:bg-brand-soft/60">
        <ProductArt
          name={product.name}
          category={product.category}
          team={product.team}
          season={product.season}
          slug={product.slug}
          className="mx-auto w-full max-w-56 drop-shadow-sm transition-transform duration-300 group-hover:-translate-y-1"
        />
        {product.discount_percent && (
          <span className="absolute left-3 top-3 rounded-md bg-accent px-2 py-0.5 font-display text-sm font-bold text-accent-ink">
            −{product.discount_percent}%
          </span>
        )}
        {soldOut && (
          <span className="absolute right-3 top-3 rounded-md bg-ink/80 px-2 py-0.5 text-xs font-medium text-canvas">Sold out</span>
        )}
      </div>
      <div className="mt-3 flex flex-1 flex-col">
        {product.team && <p className="text-xs font-medium text-muted">{product.team.name}</p>}
        <h3 className="mt-0.5 font-medium leading-snug text-ink">
          <Link to={`/product/${product.slug}`} className="after:absolute after:inset-0">
            {product.name}
          </Link>
        </h3>
        <div className="mt-1.5 flex items-center justify-between gap-2">
          <Price price={product.price} compareAt={product.compare_at_price} />
          {product.personalizable && <span className="text-xs text-muted">Name &amp; number</span>}
        </div>
      </div>
    </article>
  )
}

export function ProductGrid({ products }: { products: ProductSummary[] }) {
  return (
    <ul className="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 lg:grid-cols-4">
      {products.map((p) => (
        <li key={p.id} className="flex">
          <ProductCard product={p} />
        </li>
      ))}
    </ul>
  )
}
