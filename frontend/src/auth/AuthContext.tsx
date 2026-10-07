import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getToken, onUnauthorized, setToken } from '../api/client'
import { api } from '../api/endpoints'
import type { User } from '../api/types'
import { AuthContext } from './useAuth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(() => getToken() !== null)

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    onUnauthorized(logout) // an expired token logs the user out everywhere
    return () => onUnauthorized(null)
  }, [logout])

  useEffect(() => {
    if (!getToken()) return
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setChecking(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await api.login(email, password)
    setToken(access_token)
    const me = await api.me()
    setUser(me)
    return me
  }, [])

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      await api.register({ name, email, password })
      return login(email, password)
    },
    [login],
  )

  const value = useMemo(() => ({ user, checking, login, register, logout }), [user, checking, login, register, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
