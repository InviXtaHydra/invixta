import { Minus, Plus } from 'lucide-react'

export function QuantityStepper({
  value,
  max,
  onChange,
  disabled,
  label,
}: {
  value: number
  max: number
  onChange: (value: number) => void
  disabled?: boolean
  label: string
}) {
  return (
    <div role="group" aria-label={label} className="inline-flex items-center rounded-lg border border-line-strong">
      <button
        type="button"
        onClick={() => onChange(value - 1)}
        disabled={disabled || value <= 1}
        className="grid size-9 place-items-center text-ink-2 hover:bg-surface-2 disabled:opacity-40"
        aria-label="Decrease quantity"
      >
        <Minus aria-hidden className="size-3.5" />
      </button>
      <span aria-live="polite" className="w-8 text-center text-sm tabular-nums">
        {value}
      </span>
      <button
        type="button"
        onClick={() => onChange(value + 1)}
        disabled={disabled || value >= max}
        className="grid size-9 place-items-center text-ink-2 hover:bg-surface-2 disabled:opacity-40"
        aria-label="Increase quantity"
      >
        <Plus aria-hidden className="size-3.5" />
      </button>
    </div>
  )
}
