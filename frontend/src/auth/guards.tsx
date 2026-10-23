import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { FullPageSpinner } from '@/components/FullPageSpinner'

import { useAuth } from './useAuth'

/**
 * Ces gardes améliorent l'expérience ; elles ne protègent rien.
 * L'autorisation réelle est faite par l'API sur chaque requête.
 */
export function RequireAuth() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return <FullPageSpinner />
  if (!isAuthenticated) {
    // `state.from` permet de revenir où l'utilisateur voulait aller.
    return <Navigate to="/connexion" replace state={{ from: location }} />
  }
  return <Outlet />
}

export function RequireAdmin() {
  const { isAdmin, isLoading } = useAuth()

  if (isLoading) return <FullPageSpinner />
  if (!isAdmin) return <Navigate to="/mes-convocations" replace />
  return <Outlet />
}

export function RequireReferee() {
  const { isAdmin, isLoading } = useAuth()

  if (isLoading) return <FullPageSpinner />
  if (isAdmin) return <Navigate to="/admin" replace />
  return <Outlet />
}
