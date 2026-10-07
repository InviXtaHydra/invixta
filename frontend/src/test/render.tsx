import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import type { User } from '../api/types'
import { AuthContext } from '../auth/useAuth'
import { ToastProvider } from '../components/toast'

export const emma: User = {
  id: 3,
  email: 'emma.devries@example.com',
  role: 'CUSTOMER',
  created_at: '2026-07-01T10:00:00Z',
  customer_id: 1,
  name: 'Emma de Vries',
}

/** Renders `element` at `path` with a router, toasts and (optionally) a signed-in user. */
export function renderAt(element: ReactElement, { path = '/', route = '/', user = emma as User | null } = {}) {
  const auth = { user, checking: false, login: async () => emma, register: async () => emma, logout: () => {} }
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthContext.Provider value={auth}>
        <ToastProvider>
          <Routes>
            <Route path={route} element={element} />
            <Route path="*" element={<p>Navigated away</p>} />
          </Routes>
        </ToastProvider>
      </AuthContext.Provider>
    </MemoryRouter>,
  )
}
