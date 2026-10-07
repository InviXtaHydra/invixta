import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import { LoginPage } from './AuthPages'

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<p>Dashboard page</p>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('LoginPage', () => {
  it('signs in with the OAuth2 form and stores the token', async () => {
    const fetchMock = vi.fn(async (url: string) =>
      url.endsWith('/auth/login')
        ? new Response(JSON.stringify({ access_token: 'jwt-token' }), { status: 200 })
        : new Response(JSON.stringify({ id: 1, email: 'emma@example.com', role: 'CUSTOMER', created_at: '', customer_id: 1, name: 'Emma' }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderLogin()

    await userEvent.type(screen.getByLabelText('Email'), 'emma@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'Password123!')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Dashboard page')).toBeInTheDocument()
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/auth/login')
    expect(String(init.body)).toBe('username=emma%40example.com&password=Password123%21')
    expect(localStorage.getItem('supportai.token')).toBe('jwt-token')
  })

  it('shows the server error for wrong credentials', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'Incorrect email or password' }), { status: 401 })))
    renderLogin()
    await userEvent.type(screen.getByLabelText('Email'), 'emma@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password')
    expect(localStorage.getItem('supportai.token')).toBeNull()
  })
})
