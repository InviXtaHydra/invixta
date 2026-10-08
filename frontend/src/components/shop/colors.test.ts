import { describe, expect, it } from 'vitest'
import { contrast, readableOn, readableOnAll, shade } from './colors'

describe('shirt colours', () => {
  it('measures contrast like WCAG', () => {
    expect(contrast('#000000', '#ffffff')).toBeCloseTo(21, 0)
    expect(contrast('#ffffff', '#ffffff')).toBeCloseTo(1, 5)
  })

  it('prints white on a dark shirt and black on a light one', () => {
    expect(readableOn('#13294B', ['#ffffff', '#111111'])).toBe('#ffffff')
    expect(readableOn('#FFD100', ['#ffffff', '#111111'])).toBe('#111111')
  })

  it('on red-white stripes picks a colour readable on both stripes', () => {
    // White would vanish on the white stripes; black works on red and on white.
    expect(readableOnAll(['#C8102E', '#FFFFFF'], ['#ffffff', '#111111', '#C8102E'])).toBe('#111111')
  })

  it('darkens and lightens', () => {
    expect(shade('#808080', 0.5)).toBe('#404040')
    expect(shade('#000000', -1)).toBe('#ffffff')
  })
})
