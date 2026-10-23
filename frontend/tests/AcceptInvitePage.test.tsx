import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { setAccessToken } from '@/api/client'
import { AuthProvider } from '@/auth/AuthProvider'
import { AcceptInvitePage } from '@/pages/AcceptInvitePage'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input
  if (input instanceof URL) return input.href
  return input.url
}

function requestBody(init: RequestInit | undefined): string {
  return typeof init?.body === 'string' ? init.body : '{}'
}

const ADMIN = {
  id: 'u-admin',
  email: 'admin@example.com',
  role: 'admin',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  last_login_at: null,
  referee_profile: null,
}

const REFEREE = {
  id: 'u-ref',
  email: 'imane@test.ma',
  role: 'referee',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  last_login_at: null,
  referee_profile: { id: 'r1', first_name: 'Imane', last_name: 'Cherkaoui' },
}

function renderPage(token = 'jeton-invitation') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/invitation?token=${token}`]}>
        <AuthProvider>
          <Routes>
            <Route path="/invitation" element={<AcceptInvitePage />} />
            <Route path="/mon-profil" element={<p>Espace arbitre</p>} />
            <Route path="/admin" element={<p>Espace administrateur</p>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => setAccessToken(null))
afterEach(() => vi.restoreAllMocks())

describe("page d'activation de compte", () => {
  it('refuse un lien sans jeton', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse({ detail: 'non' }, 401))),
    )
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/invitation']}>
          <AuthProvider>
            <AcceptInvitePage />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Ce lien d'invitation est incomplet.",
    )
  })

  it('exige deux mots de passe identiques', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse({ detail: 'non' }, 401))),
    )
    renderPage()

    await userEvent.type(await screen.findByLabelText('Mot de passe'), 'MotDePasse!2026')
    await userEvent.type(screen.getByLabelText('Confirmer le mot de passe'), 'Different!2026')
    await userEvent.click(screen.getByRole('button', { name: 'Activer mon compte' }))

    expect(
      await screen.findByText('Les deux mots de passe ne correspondent pas.'),
    ).toBeInTheDocument()
  })

  it('refuse un mot de passe trop court, comme le backend', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse({ detail: 'non' }, 401))),
    )
    renderPage()

    await userEvent.type(await screen.findByLabelText('Mot de passe'), 'court')
    await userEvent.type(screen.getByLabelText('Confirmer le mot de passe'), 'court')
    await userEvent.click(screen.getByRole('button', { name: 'Activer mon compte' }))

    expect(
      await screen.findByText('Le mot de passe doit contenir au moins 10 caractères.'),
    ).toBeInTheDocument()
  })

  it("active le compte et ouvre l'espace arbitre", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, _init?: RequestInit) => {
      const url = requestUrl(input)
      if (url.endsWith('/auth/refresh')) return Promise.resolve(jsonResponse({}, 401))
      if (url.endsWith('/auth/accept-invite')) {
        return Promise.resolve(
          jsonResponse({
            access_token: 'jeton-arbitre',
            token_type: 'bearer',
            expires_in: 900,
          }),
        )
      }
      if (url.endsWith('/auth/me')) return Promise.resolve(jsonResponse(REFEREE))
      return Promise.resolve(jsonResponse({}, 404))
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await userEvent.type(await screen.findByLabelText('Mot de passe'), 'ArbitrePass!2026')
    await userEvent.type(screen.getByLabelText('Confirmer le mot de passe'), 'ArbitrePass!2026')
    await userEvent.click(screen.getByRole('button', { name: 'Activer mon compte' }))

    expect(await screen.findByText('Espace arbitre')).toBeInTheDocument()

    const call = fetchMock.mock.calls.find(([url]) =>
      requestUrl(url).endsWith('/auth/accept-invite'),
    )
    expect(JSON.parse(requestBody(call?.[1]))).toEqual({
      token: 'jeton-invitation',
      password: 'ArbitrePass!2026',
    })
  })

  it("n'hérite jamais de la session déjà ouverte dans le navigateur", async () => {
    // Régression : un administrateur était connecté sur ce navigateur. L'arbitre
    // qui active son compte doit atterrir dans SON espace, pas dans celui de
    // l'administrateur. L'état React doit suivre le changement de session.
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = requestUrl(input)
      // La session administrateur est restaurée au montage.
      if (url.endsWith('/auth/refresh')) {
        return Promise.resolve(
          jsonResponse({ access_token: 'jeton-admin', token_type: 'bearer', expires_in: 900 }),
        )
      }
      if (url.endsWith('/auth/accept-invite')) {
        return Promise.resolve(
          jsonResponse({
            access_token: 'jeton-arbitre',
            token_type: 'bearer',
            expires_in: 900,
          }),
        )
      }
      if (url.endsWith('/auth/me')) {
        // Avant l'activation : l'administrateur. Après : le nouvel arbitre.
        return Promise.resolve(
          jsonResponse(
            fetchMock.mock.calls.some(([u]) => requestUrl(u).endsWith('/auth/accept-invite'))
              ? REFEREE
              : ADMIN,
          ),
        )
      }
      return Promise.resolve(jsonResponse({}, 404))
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await userEvent.type(await screen.findByLabelText('Mot de passe'), 'ArbitrePass!2026')
    await userEvent.type(screen.getByLabelText('Confirmer le mot de passe'), 'ArbitrePass!2026')
    await userEvent.click(screen.getByRole('button', { name: 'Activer mon compte' }))

    expect(await screen.findByText('Espace arbitre')).toBeInTheDocument()
    expect(screen.queryByText('Espace administrateur')).not.toBeInTheDocument()
  })

  it('affiche le refus du serveur sur un lien expiré', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = requestUrl(input)
        if (url.endsWith('/auth/accept-invite')) {
          return Promise.resolve(
            jsonResponse(
              { detail: "Lien d'invitation invalide ou expiré.", code: 'validation_error' },
              422,
            ),
          )
        }
        return Promise.resolve(jsonResponse({}, 401))
      }),
    )
    renderPage()

    await userEvent.type(await screen.findByLabelText('Mot de passe'), 'ArbitrePass!2026')
    await userEvent.type(screen.getByLabelText('Confirmer le mot de passe'), 'ArbitrePass!2026')
    await userEvent.click(screen.getByRole('button', { name: 'Activer mon compte' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        "Lien d'invitation invalide ou expiré.",
      )
    })
  })
})
