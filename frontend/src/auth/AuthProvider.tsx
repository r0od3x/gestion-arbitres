import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { api, setAccessToken, setSessionExpiredHandler } from '@/api/client'
import type { CurrentUser, TokenResponse } from '@/api/types'

import { AuthContext, type AuthState } from './authContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const queryClient = useQueryClient()

  const clearSession = useCallback(() => {
    setAccessToken(null)
    setUser(null)
    queryClient.clear()
  }, [queryClient])

  // Au démarrage : le cookie de rafraîchissement permet de reprendre la session
  // sans redemander le mot de passe (le jeton d'accès, lui, est perdu au reload).
  useEffect(() => {
    let cancelled = false

    async function restore() {
      try {
        const tokens = await api.post<TokenResponse>('/auth/refresh')
        setAccessToken(tokens.access_token)
        const me = await api.get<CurrentUser>('/auth/me')
        if (!cancelled) setUser(me)
      } catch {
        if (!cancelled) clearSession()
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void restore()
    return () => {
      cancelled = true
    }
  }, [clearSession])

  // Le client HTTP signale une session définitivement expirée.
  useEffect(() => {
    setSessionExpiredHandler(clearSession)
    return () => setSessionExpiredHandler(null)
  }, [clearSession])

  const login = useCallback(async (email: string, password: string): Promise<CurrentUser> => {
    const tokens = await api.post<TokenResponse>('/auth/login', { email, password })
    setAccessToken(tokens.access_token)
    const me = await api.get<CurrentUser>('/auth/me')
    setUser(me)
    return me
  }, [])

  const adoptSession = useCallback(
    async (accessToken: string): Promise<CurrentUser> => {
      // Le cache peut contenir les données de la session précédente.
      queryClient.clear()
      setAccessToken(accessToken)
      const me = await api.get<CurrentUser>('/auth/me')
      setUser(me)
      setIsLoading(false)
      return me
    },
    [queryClient],
  )

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } finally {
      clearSession()
    }
  }, [clearSession])

  const value = useMemo<AuthState>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      isAdmin: user?.role === 'admin',
      login,
      adoptSession,
      logout,
    }),
    [user, isLoading, login, adoptSession, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
