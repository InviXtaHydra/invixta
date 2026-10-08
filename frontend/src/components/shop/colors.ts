// Small colour helpers for drawing shirts: pick readable text colours and shades.

function rgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16)) as [number, number, number]
}

/** WCAG relative luminance (0 = black, 1 = white). */
export function luminance(hex: string): number {
  const [r, g, b] = rgb(hex).map((v) => {
    const c = v / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

/** The candidate with the best contrast against the background (for names and numbers on a shirt). */
export function readableOn(background: string, candidates: string[]): string {
  return [...candidates].sort((a, b) => contrast(b, background) - contrast(a, background))[0]
}

/** Mix a colour with black (amount > 0) or white (amount < 0). */
export function shade(hex: string, amount: number): string {
  const target = amount > 0 ? 0 : 255
  const t = Math.abs(amount)
  return `#${rgb(hex)
    .map((v) => Math.round(v + (target - v) * t).toString(16).padStart(2, '0'))
    .join('')}`
}

/** The candidate that is readable on all of the backgrounds (e.g. both stripe colours of a shirt). */
export function readableOnAll(backgrounds: string[], candidates: string[]): string {
  const worst = (c: string) => Math.min(...backgrounds.map((b) => contrast(c, b)))
  return [...candidates].sort((a, b) => worst(b) - worst(a))[0]
}
