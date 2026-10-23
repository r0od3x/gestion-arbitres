/**
 * Client HTTP de l'API.
 *
 * Le jeton d'accès vit en mémoire (jamais en localStorage : il serait lisible
 * par n'importe quel script). Le jeton de rafraîchissement est un cookie
 * httpOnly posé par le serveur, d'où `credentials: 'include'`.
 */

import type { ApiErrorBody, TokenResponse } from './types'

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

let accessToken: string | null = null
/** Rafraîchissement en cours, partagé pour éviter les appels concurrents. */
let refreshInFlight: Promise<string | null> | null = null
let onSessionExpired: (() => void) | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

/** Appelé quand le rafraîchissement échoue : l'application doit déconnecter. */
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
    readonly code?: string,
  ) {
    super(detail)
    this.name = 'ApiError'
  }

  get isAuthError(): boolean {
    return this.status === 401
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  let detail = response.statusText || 'Erreur inconnue'
  let code: string | undefined
  try {
    const body = (await response.json()) as ApiErrorBody
    if (body?.detail) detail = body.detail
    code = body?.code
  } catch {
    // Réponse sans corps JSON : on garde le statut HTTP.
  }
  return new ApiError(response.status, detail, code)
}

function buildHeaders(init: RequestInit, hasBody: boolean): Headers {
  const headers = new Headers(init.headers)
  if (hasBody && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  return headers
}

async function rawFetch(path: string, init: RequestInit): Promise<Response> {
  return fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: buildHeaders(init, init.body !== undefined),
  })
}

/** Échange le cookie de rafraîchissement contre un nouveau jeton d'accès. */
async function refreshAccessToken(): Promise<string | null> {
  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      })
      if (!response.ok) return null
      const body = (await response.json()) as TokenResponse
      accessToken = body.access_token
      return accessToken
    } catch {
      return null
    } finally {
      refreshInFlight = null
    }
  })()
  return refreshInFlight
}

/**
 * Exécute une requête authentifiée. Sur 401, tente UN rafraîchissement puis rejoue.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response = await rawFetch(path, init)

  const isAuthRoute = path.startsWith('/auth/login') || path.startsWith('/auth/refresh')
  if (response.status === 401 && !isAuthRoute) {
    const renewed = await refreshAccessToken()
    if (renewed) {
      response = await rawFetch(path, init)
    } else {
      accessToken = null
      onSessionExpired?.()
    }
  }

  if (!response.ok) throw await toApiError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string): Promise<T> => apiFetch<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    apiFetch<T>(path, {
      method: 'POST',
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    }),
  patch: <T>(path: string, body: unknown): Promise<T> =>
    apiFetch<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown): Promise<T> =>
    apiFetch<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string): Promise<T> => apiFetch<T>(path, { method: 'DELETE' }),
}
