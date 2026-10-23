import { createContext } from 'react'

import type { CurrentUser } from '@/api/types'

export interface AuthState {
  user: CurrentUser | null
  /** Vrai pendant la restauration de session au démarrage. */
  isLoading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  login: (email: string, password: string) => Promise<CurrentUser>
  logout: () => Promise<void>
}

/** Séparé du provider pour garder le rafraîchissement à chaud fonctionnel. */
export const AuthContext = createContext<AuthState | null>(null)
