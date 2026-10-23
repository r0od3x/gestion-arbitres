import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { setAccessToken } from '@/api/client'
import { AuthProvider } from '@/auth/AuthProvider'
import { LoginPage } from '@/pages/LoginPage'

/** `fetch` accepte une chaîne, une URL ou un Request : les trois donnent une URL. */
function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input
  if (input instanceof URL) return input.href
  return input.url
}

function requestBody(init: RequestInit | undefined): string {
  return typeof init?.body === 'string' ? init.body : ''
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/** Rejette la restauration de session au démarrage, puis délègue au gestionnaire. */
function mockApi(handler: (url: string, init?: RequestInit) => Response) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = requestUrl(input)
    if (url.endsWith('/auth/refresh')) {
      return Promise.resolve(jsonResponse({ detail: 'Non authentifié' }, 401))
    }
    return Promise.resolve(handler(url, init))
  })
}

function renderLogin() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/connexion']}>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
  return render(<LoginPage />, { wrapper })
}

beforeEach(() => {
  setAccessToken(null)
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('page de connexion', () => {
  it('affiche le formulaire une fois la session restaurée', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => jsonResponse({}, 404)),
    )
    renderLogin()

    expect(await screen.findByLabelText('Adresse e-mail')).toBeInTheDocument()
    expect(screen.getByLabelText('Mot de passe')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Se connecter' })).toBeInTheDocument()
  })

  it('valide les champs avant tout appel réseau', async () => {
    const fetchMock = mockApi(() => jsonResponse({}, 404))
    vi.stubGlobal('fetch', fetchMock)
    renderLogin()

    await screen.findByLabelText('Adresse e-mail')
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByText('Saisissez votre adresse e-mail.')).toBeInTheDocument()
    expect(screen.getByText('Saisissez votre mot de passe.')).toBeInTheDocument()

    const loginCalls = fetchMock.mock.calls.filter(([url]) =>
      requestUrl(url).endsWith('/auth/login'),
    )
    expect(loginCalls).toHaveLength(0)
  })

  it('refuse une adresse e-mail mal formée', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => jsonResponse({}, 404)),
    )
    renderLogin()

    await userEvent.type(await screen.findByLabelText('Adresse e-mail'), 'pas-un-email')
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'MotDePasse!2026')
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByText('Adresse e-mail invalide.')).toBeInTheDocument()
  })

  it('envoie les identifiants et stocke le jeton en mémoire', async () => {
    const fetchMock = mockApi((url) => {
      if (url.endsWith('/auth/login')) {
        return jsonResponse({
          access_token: 'jeton-123',
          token_type: 'bearer',
          expires_in: 900,
        })
      }
      if (url.endsWith('/auth/me')) {
        return jsonResponse({
          id: '00000000-0000-0000-0000-000000000001',
          email: 'admin@test.ma',
          role: 'admin',
          is_active: true,
          created_at: '2026-01-01T00:00:00Z',
          last_login_at: null,
          referee_profile: null,
        })
      }
      return jsonResponse({}, 404)
    })
    vi.stubGlobal('fetch', fetchMock)
    renderLogin()

    await userEvent.type(await screen.findByLabelText('Adresse e-mail'), 'admin@test.ma')
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'AdminTest!2026')
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }))

    await waitFor(() => {
      const loginCall = fetchMock.mock.calls.find(([url]) =>
        requestUrl(url).endsWith('/auth/login'),
      )
      expect(loginCall).toBeDefined()
      expect(JSON.parse(requestBody(loginCall?.[1]))).toEqual({
        email: 'admin@test.ma',
        password: 'AdminTest!2026',
      })
      // Le cookie de rafraîchissement doit pouvoir circuler.
      expect(loginCall?.[1]?.credentials).toBe('include')
    })
  })

  it('affiche un message dédié quand les identifiants sont refusés', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi((url) =>
        url.endsWith('/auth/login')
          ? jsonResponse(
              { detail: 'E-mail ou mot de passe incorrect.', code: 'authentication_failed' },
              401,
            )
          : jsonResponse({}, 404),
      ),
    )
    renderLogin()

    await userEvent.type(await screen.findByLabelText('Adresse e-mail'), 'admin@test.ma')
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'mauvais')
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'E-mail ou mot de passe incorrect.',
    )
  })

  it('distingue une panne serveur d’une erreur d’identifiants', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi((url) =>
        url.endsWith('/auth/login')
          ? jsonResponse({ detail: 'boum' }, 500)
          : jsonResponse({}, 404),
      ),
    )
    renderLogin()

    await userEvent.type(await screen.findByLabelText('Adresse e-mail'), 'admin@test.ma')
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'AdminTest!2026')
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Connexion impossible. Réessayez dans un instant.',
    )
  })
})
