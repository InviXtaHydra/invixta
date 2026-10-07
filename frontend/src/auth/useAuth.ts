import { createContext, useContext } from 'react'
import type { User } from '../api/types'

export interface AuthValue {
  user: User | null
  /** true while the stored token is being checked on page load */
  checking: boolean
  login: (email: string, password: string) => Promise<User>
  register: (name: string, email: string, password: string) => Promise<User>
  logout: () => void
}

export const AuthContext = createContext<AuthValue | null>(null)

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>')
  return value
}

export function useUser(): User {
  const { user } = useAuth()
  if (!user) throw new Error('useUser needs a signed-in user (use it inside <RequireAuth>)')
  return user
}

export const isStaff = (user: User) => user.role === 'ADMIN' || user.role === 'AGENT'
