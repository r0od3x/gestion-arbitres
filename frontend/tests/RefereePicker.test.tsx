import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { setAccessToken } from '@/api/client'
import type { AssignmentWithReferee, Referee } from '@/api/types'
import { RefereePicker } from '@/features/tournaments/RefereePicker'

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

function makeAssignment(overrides: Partial<AssignmentWithReferee> = {}): AssignmentWithReferee {
  return {
    id: 'a1',
    tournament_id: 'tour1',
    referee_id: 'r1',
    role_in_tournament: null,
    status: 'confirmed',
    responded_at: '2026-02-01T00:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
    referee: {
      id: 'r1',
      first_name: 'Youssef',
      last_name: 'El Amrani',
      phone_e164: '+212612345671',
      whatsapp_opt_in: true,
      city: 'Casablanca',
    },
    notification_status: null,
    notification_error: null,
    is_notifiable: true,
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

function requestBody(init: RequestInit | undefined): string {
  return typeof init?.body === 'string' ? init.body : '{}'
}

function mockApi(handler: (url: string, init?: RequestInit) => Response) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(handler(requestUrl(input), init)),
  )
}

function renderPicker(editable = true) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
  return render(<RefereePicker tournamentId="tour1" editable={editable} />, { wrapper })
}

const TWO_REFEREES = [
  makeReferee(),
  makeReferee({ id: 'r2', first_name: 'Salma', last_name: 'Benali', email: 'salma@test.ma' }),
]

beforeEach(() => setAccessToken('jeton-de-test'))
afterEach(() => vi.restoreAllMocks())

describe('sélecteur d’arbitres', () => {
  it('pré-coche les arbitres déjà convoqués', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi((url) =>
        url.includes('/assignments')
          ? jsonResponse([makeAssignment()])
          : jsonResponse({ items: TWO_REFEREES, total: 2, page: 1, size: 100 }),
      ),
    )
    renderPicker()

    const checkboxes = await screen.findAllByRole('checkbox')
    await waitFor(() => expect(checkboxes[0]).toBeChecked())
    expect(checkboxes[1]).not.toBeChecked()
    expect(screen.getByText('1 sélectionné(s)')).toBeInTheDocument()
  })

  it('envoie la liste complète des arbitres sélectionnés', async () => {
    const fetchMock = mockApi((url, init) => {
      if (url.includes('/assignments') && init?.method === 'PUT') {
        return jsonResponse({ added: 1, cancelled: 0, unchanged: 1 })
      }
      if (url.includes('/assignments')) return jsonResponse([makeAssignment()])
      return jsonResponse({ items: TWO_REFEREES, total: 2, page: 1, size: 100 })
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPicker()

    const checkboxes = await screen.findAllByRole('checkbox')
    await waitFor(() => expect(checkboxes[0]).toBeChecked())

    // On ajoute le second : la requête doit porter les DEUX identifiants.
    await userEvent.click(checkboxes[1]!)
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer les désignations' }))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT')
      expect(call).toBeDefined()
      const body = JSON.parse(requestBody(call?.[1])) as { referee_ids: string[] }
      expect(new Set(body.referee_ids)).toEqual(new Set(['r1', 'r2']))
    })
  })

  it('affiche le différentiel renvoyé par le serveur', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi((url, init) => {
        if (url.includes('/assignments') && init?.method === 'PUT') {
          return jsonResponse({ added: 1, cancelled: 2, unchanged: 3 })
        }
        if (url.includes('/assignments')) return jsonResponse([])
        return jsonResponse({ items: TWO_REFEREES, total: 2, page: 1, size: 100 })
      }),
    )
    renderPicker()

    await screen.findAllByRole('checkbox')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer les désignations' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      '1 ajout(s), 2 annulation(s), 3 inchangée(s).',
    )
  })

  it('signale un arbitre sélectionné qui ne recevra pas de WhatsApp', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi((url) =>
        url.includes('/assignments')
          ? jsonResponse([makeAssignment({ is_notifiable: false })])
          : jsonResponse({ items: TWO_REFEREES, total: 2, page: 1, size: 100 }),
      ),
    )
    renderPicker()

    expect(await screen.findByText('Ne recevra pas de WhatsApp')).toBeInTheDocument()
  })

  it('ne demande que les arbitres actifs', async () => {
    const fetchMock = mockApi((url) =>
      url.includes('/assignments')
        ? jsonResponse([])
        : jsonResponse({ items: [], total: 0, page: 1, size: 100 }),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderPicker()

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url]) =>
            requestUrl(url).includes('/referees?') && requestUrl(url).includes('active=true'),
        ),
      ).toBe(true)
    })
  })

  it('verrouille la sélection sur un tournoi figé', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi((url) =>
        url.includes('/assignments')
          ? jsonResponse([])
          : jsonResponse({ items: TWO_REFEREES, total: 2, page: 1, size: 100 }),
      ),
    )
    renderPicker(false)

    expect(
      await screen.findByText('Ce tournoi n’accepte plus de convocation.'),
    ).toBeInTheDocument()
    for (const checkbox of await screen.findAllByRole('checkbox')) {
      expect(checkbox).toBeDisabled()
    }
    expect(screen.getByRole('button', { name: 'Enregistrer les désignations' })).toBeDisabled()
  })

  it('remonte le refus du serveur', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi((url, init) => {
        if (url.includes('/assignments') && init?.method === 'PUT') {
          return jsonResponse(
            {
              detail: 'Arbitre(s) désactivé(s), non convocable(s) : Omar Bennis',
              code: 'validation_error',
            },
            422,
          )
        }
        if (url.includes('/assignments')) return jsonResponse([])
        return jsonResponse({ items: TWO_REFEREES, total: 2, page: 1, size: 100 })
      }),
    )
    renderPicker()

    await screen.findAllByRole('checkbox')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer les désignations' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'non convocable(s) : Omar Bennis',
    )
  })
})
