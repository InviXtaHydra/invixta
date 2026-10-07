import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MessageText } from './MessageText'

describe('MessageText', () => {
  it('renders paragraphs, lists, bold text and citations', () => {
    const { container } = render(<MessageText text={'You can return items within **30 days** [S1].\n\n- Unused\n- In the original box'} />)
    expect(screen.getByText('30 days').tagName).toBe('STRONG')
    expect(screen.getByText('S1').tagName).toBe('SUP')
    expect(container.querySelectorAll('li')).toHaveLength(2)
  })

  it('never renders HTML from the model', () => {
    const { container } = render(<MessageText text={'<img src=x onerror="alert(1)"> hello'} />)
    expect(container.querySelector('img')).toBeNull()
    expect(container.textContent).toContain('<img src=x onerror="alert(1)"> hello')
  })
})
