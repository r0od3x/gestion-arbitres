import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { setAccessToken } from '@/api/client'
import type { Referee } from '@/api/types'
import { RefereesPage } from '@/pages/admin/RefereesPage'

function makeReferee(overrides: Partial<Referee> = {}): Referee {
  return {
    id: 'r1',
    user_id: 'u1',
    email: 'youssef@test.ma',
    is_active: true,
    has_accepted_invite: true,
    created_at: '2026-01-01T00:00:00Z',
    first_name: 'Youssef',
    last_name: 'El Amrani',
    phone_e164: '+212612345671',
    whatsapp_opt_in: true,
    whatsapp_opt_in_at: '2026-01-01T00:00:00Z',
    grade: 'national',
    license_number: 'ARB-001',
    city: 'Casablanca',
    club: null,
    league: null,
    photo_url: null,
    notes_admin: null,
    ...overrides,
  }
}

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

/** Capture chaque URL appelée et renvoie la réponse fournie par le gestionnaire. */
function requestBody(init: RequestInit | undefined): string {
  return typeof init?.body === 'string' ? init.body : '{}'
}

function mockApi(handler: (url: string, init?: RequestInit) => Response) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(handler(requestUrl(input), init)),
  )
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
  return render(<RefereesPage />, { wrapper })
}

beforeEach(() => setAccessToken('jeton-de-test'))
afterEach(() => vi.restoreAllMocks())

describe('page des arbitres', () => {
  it('affiche les arbitres renvoyés par l’API', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => jsonResponse({ items: [makeReferee()], total: 1, page: 1, size: 20 })),
    )
    renderPage()

    expect(await screen.findByText('Youssef El Amrani')).toBeInTheDocument()
    const table = screen.getByRole('table')
    expect(within(table).getByText('youssef@test.ma')).toBeInTheDocument()
    expect(within(table).getByText('National')).toBeInTheDocument()
    expect(within(table).getByText('Actif')).toBeInTheDocument()
  })

  it('signale une invitation non encore acceptée', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() =>
        jsonResponse({
          items: [makeReferee({ has_accepted_invite: false })],
          total: 1,
          page: 1,
          size: 20,
        }),
      ),
    )
    renderPage()

    expect(await screen.findByText('Invitation en attente')).toBeInTheDocument()
  })

  it('distingue la liste vide filtrée de la liste vide tout court', async () => {
    const fetchMock = mockApi(() => jsonResponse({ items: [], total: 0, page: 1, size: 20 }))
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    expect(await screen.findByText('Aucun arbitre pour le moment.')).toBeInTheDocument()

    await userEvent.type(screen.getByPlaceholderText('Rechercher un arbitre…'), 'zzz')

    expect(
      await screen.findByText('Aucun arbitre ne correspond à ces critères.'),
    ).toBeInTheDocument()
  })

  it('transmet les filtres à l’API en query string', async () => {
    const fetchMock = mockApi(() => jsonResponse({ items: [], total: 0, page: 1, size: 20 }))
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await screen.findByText('Aucun arbitre pour le moment.')
    await userEvent.selectOptions(screen.getByLabelText('Grade'), 'national')

    await waitFor(() => {
      const urls = fetchMock.mock.calls.map(([url]) => requestUrl(url))
      expect(urls.some((url) => url.includes('grade=national'))).toBe(true)
    })
  })

  it('revient à la première page quand un filtre change', async () => {
    const fetchMock = mockApi(() =>
      jsonResponse({ items: [makeReferee()], total: 60, page: 2, size: 20 }),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Suivant' }))
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => requestUrl(url).includes('page=2'))).toBe(
        true,
      )
    })

    await userEvent.type(screen.getByPlaceholderText('Rechercher un arbitre…'), 'a')

    await waitFor(() => {
      const last = requestUrl(fetchMock.mock.calls.at(-1)?.[0] ?? '')
      expect(last).toContain('page=1')
      expect(last).toContain('q=a')
    })
  })

  it('affiche une erreur avec une action de réessai', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => jsonResponse({ detail: 'boum' }, 500)),
    )
    renderPage()

    expect(await screen.findByText('Une erreur est survenue.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
  })

  it('crée une invitation et montre le lien à transmettre', async () => {
    const fetchMock = mockApi((url, init) => {
      if (url.includes('/referees/invite') && init?.method === 'POST') {
        return jsonResponse(
          {
            referee: makeReferee({ has_accepted_invite: false }),
            invite_url: 'http://localhost:5173/invitation?token=abc123',
            invite_expires_in_hours: 72,
          },
          201,
        )
      }
      return jsonResponse({ items: [], total: 0, page: 1, size: 20 })
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Inviter un arbitre' }))

    await userEvent.type(screen.getByLabelText('Prénom'), 'Imane')
    await userEvent.type(screen.getByLabelText('Nom'), 'Cherkaoui')
    await userEvent.type(screen.getByLabelText('Adresse e-mail'), 'imane@test.ma')
    await userEvent.click(screen.getByRole('button', { name: "Créer l'invitation" }))

    expect(
      await screen.findByText('http://localhost:5173/invitation?token=abc123'),
    ).toBeInTheDocument()
    expect(screen.getByText('Ce lien expire dans 72 heures.')).toBeInTheDocument()

    const inviteCall = fetchMock.mock.calls.find(
      ([url, init]) => requestUrl(url).includes('/referees/invite') && init?.method === 'POST',
    )
    expect(JSON.parse(requestBody(inviteCall?.[1]))).toMatchObject({
      first_name: 'Imane',
      last_name: 'Cherkaoui',
      email: 'imane@test.ma',
      grade: 'regional',
      phone: null,
    })
  })

  it('remonte le message d’erreur du serveur sur une invitation refusée', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi((url, init) => {
        if (url.includes('/referees/invite') && init?.method === 'POST') {
          return jsonResponse(
            { detail: 'Un compte existe déjà avec cette adresse e-mail.', code: 'conflict' },
            409,
          )
        }
        return jsonResponse({ items: [], total: 0, page: 1, size: 20 })
      }),
    )
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Inviter un arbitre' }))
    await userEvent.type(screen.getByLabelText('Prénom'), 'Imane')
    await userEvent.type(screen.getByLabelText('Nom'), 'Cherkaoui')
    await userEvent.type(screen.getByLabelText('Adresse e-mail'), 'deja@test.ma')
    await userEvent.click(screen.getByRole('button', { name: "Créer l'invitation" }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Un compte existe déjà avec cette adresse e-mail.',
    )
  })

  it('désactive un arbitre depuis le tableau', async () => {
    const fetchMock = mockApi((url, init) => {
      if (url.includes('/deactivate') && init?.method === 'POST') {
        return jsonResponse(makeReferee({ is_active: false }))
      }
      return jsonResponse({ items: [makeReferee()], total: 1, page: 1, size: 20 })
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    const table = await screen.findByRole('table')
    await userEvent.click(within(table).getByRole('button', { name: 'Désactiver' }))

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([url]) => requestUrl(url).includes('/deactivate')),
      ).toBe(true)
    })
  })
})
