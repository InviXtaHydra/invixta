import { Button } from './ui'

export function Pagination({ total, limit, offset, onChange }: { total: number; limit: number; offset: number; onChange: (offset: number) => void }) {
  if (total <= limit) return null
  const from = offset + 1
  const to = Math.min(offset + limit, total)
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
      <p className="text-muted">
        {from}–{to} of {total}
      </p>
      <div className="flex gap-2">
        <Button variant="secondary" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
          Previous
        </Button>
        <Button variant="secondary" disabled={to >= total} onClick={() => onChange(offset + limit)}>
          Next
        </Button>
      </div>
    </nav>
  )
}
