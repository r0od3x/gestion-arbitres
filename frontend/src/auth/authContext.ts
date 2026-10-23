import { createContext } from 'react'

import type { CurrentUser } from '@/api/types'

export interface AuthState {
  user: CurrentUser | null
  /** Vrai pendant la restauration de session au démarrage. */
  isLoading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  login: (email: string, password: string) => Promise<CurrentUser>
  /**
   * Adopte une session obtenue autrement qu'avec un mot de passe (acceptation
   * d'invitation, par exemple). Passe toujours par ici : poser le jeton
   * directement sur le client HTTP laisserait l'état React sur l'utilisateur
   * précédent, et les gardes de route décideraient d'après lui.
   */
  adoptSession: (accessToken: string) => Promise<CurrentUser>
  logout: () => Promise<void>
}

/** Séparé du provider pour garder le rafraîchissement à chaud fonctionnel. */
export const AuthContext = createContext<AuthState | null>(null)
