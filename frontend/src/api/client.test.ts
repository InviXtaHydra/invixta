import { describe, expect, it } from 'vitest'
import { errorMessage, query } from './client'

const json = (body: unknown, status: number) => new Response(JSON.stringify(body), { status })

describe('errorMessage', () => {
  it('uses the detail string of FastAPI errors', async () => {
    expect(await errorMessage(json({ detail: 'Incorrect email or password' }, 401))).toBe('Incorrect email or password')
  })
  it('turns a validation error list into a readable sentence', async () => {
    const body = { detail: [{ loc: ['body', 'subject'], msg: 'String should have at least 3 characters' }] }
    expect(await errorMessage(json(body, 422))).toBe('subject: String should have at least 3 characters')
  })
  it('has a fallback for responses without JSON', async () => {
    expect(await errorMessage(new Response('Bad gateway', { status: 502 }))).toBe('The server ran into a problem. Please try again.')
    expect(await errorMessage(new Response('', { status: 429 }))).toMatch(/Too many requests/)
  })
})

describe('query', () => {
  it('skips empty values', () => {
    expect(query({ status: '', limit: 10, offset: 0, x: undefined })).toBe('?limit=10&offset=0')
    expect(query({})).toBe('')
  })
})
