import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import type { Role } from '../api/types'
import { FullPageSpinner } from '../components/feedback'
import { useAuth } from './useAuth'

/** Renders the page only for signed-in users (and, optionally, only for some roles). */
export function RequireAuth({ children, roles }: { children: ReactNode; roles?: Role[] }) {
  const { user, checking } = useAuth()
  const location = useLocation()
  if (checking) return <FullPageSpinner />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  if (roles && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}
