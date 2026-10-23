import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { setAccessToken } from '@/api/client'
import type { TournamentWithCounts } from '@/api/types'
import { TournamentsPage } from '@/pages/admin/TournamentsPage'

function makeTournament(overrides: Partial<TournamentWithCounts> = {}): TournamentWithCounts {
  return {
    id: 'tour1',
    title: 'Championnat régional',
    description: null,
    venue: 'Complexe Mohammed V',
    city: 'Casablanca',
    start_date: '2026-11-12',
    end_date: '2026-11-14',
    convocation_time: '08:30:00',
    referees_needed: 4,
    status: 'draft',
    created_at: '2026-01-01T00:00:00Z',
    assigned_count: 2,
    confirmed_count: 1,
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

function page(items: TournamentWithCounts[], total = items.length) {
  return jsonResponse({ items, total, page: 1, size: 20 })
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
  return render(<TournamentsPage />, { wrapper })
}

beforeEach(() => setAccessToken('jeton-de-test'))
afterEach(() => vi.restoreAllMocks())

describe('page des tournois', () => {
  it('affiche le tournoi et son effectif', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => page([makeTournament()])),
    )
    renderPage()

    expect(await screen.findByText('Championnat régional')).toBeInTheDocument()
    const table = screen.getByRole('table')
    expect(within(table).getByText('2/4 désigné(s), 1 confirmé(s)')).toBeInTheDocument()
  })

  it("n'affiche que les transitions permises par le statut", async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => page([makeTournament({ status: 'draft' })])),
    )
    renderPage()

    const table = await screen.findByRole('table')
    // Un brouillon se publie ou s'annule, il ne se clôture pas.
    expect(within(table).getByRole('button', { name: 'Publier' })).toBeInTheDocument()
    expect(
      within(table).getByRole('button', { name: 'Annuler le tournoi' }),
    ).toBeInTheDocument()
    expect(within(table).queryByRole('button', { name: 'Clôturer' })).not.toBeInTheDocument()
  })

  it('ne propose aucune transition sur un tournoi annulé', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => page([makeTournament({ status: 'cancelled' })])),
    )
    renderPage()

    const table = await screen.findByRole('table')
    expect(within(table).queryByRole('button', { name: 'Publier' })).not.toBeInTheDocument()
    expect(within(table).queryByRole('button', { name: 'Clôturer' })).not.toBeInTheDocument()
    expect(within(table).getByText('Annulé')).toBeInTheDocument()
  })

  it('publie un tournoi', async () => {
    const fetchMock = mockApi((url, init) => {
      if (url.includes('/publish') && init?.method === 'POST') {
        return jsonResponse(makeTournament({ status: 'published' }))
      }
      return page([makeTournament()])
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    const table = await screen.findByRole('table')
    await userEvent.click(within(table).getByRole('button', { name: 'Publier' }))

    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => requestUrl(url).includes('/publish'))).toBe(
        true,
      )
    })
  })

  it('transmet les filtres de statut et de période', async () => {
    const fetchMock = mockApi(() => page([]))
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await screen.findByText('Aucun tournoi pour le moment.')
    await userEvent.selectOptions(screen.getByLabelText('Statut'), 'published')
    await userEvent.selectOptions(screen.getByLabelText('Dates'), 'true')

    await waitFor(() => {
      const last = requestUrl(fetchMock.mock.calls.at(-1)?.[0] ?? '')
      expect(last).toContain('status=published')
      expect(last).toContain('upcoming=true')
    })
  })

  it('crée un tournoi et envoie les champs au bon format', async () => {
    const fetchMock = mockApi((url, init) => {
      if (url.endsWith('/tournaments') && init?.method === 'POST') {
        return jsonResponse(makeTournament(), 201)
      }
      return page([])
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Créer un tournoi' }))
    await userEvent.type(screen.getByLabelText('Titre'), 'Coupe du Trône')
    await userEvent.type(screen.getByLabelText('Ville'), 'Rabat')
    await userEvent.type(screen.getByLabelText('Date de début'), '2026-12-01')
    await userEvent.type(screen.getByLabelText('Date de fin'), '2026-12-03')
    await userEvent.type(screen.getByLabelText('Heure de convocation'), '09:00')
    await userEvent.type(screen.getByLabelText('Arbitres nécessaires'), '6')
    await userEvent.click(screen.getByRole('button', { name: 'Créer le tournoi' }))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) => requestUrl(url).endsWith('/tournaments') && init?.method === 'POST',
      )
      expect(call).toBeDefined()
      expect(JSON.parse(requestBody(call?.[1]))).toMatchObject({
        title: 'Coupe du Trône',
        city: 'Rabat',
        start_date: '2026-12-01',
        end_date: '2026-12-03',
        // Le backend attend HH:MM:SS, le champ HTML donne HH:MM.
        convocation_time: '09:00:00',
        referees_needed: 6,
      })
    })
  })

  it('refuse une date de fin antérieure au début, sans appel réseau', async () => {
    const fetchMock = mockApi(() => page([]))
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Créer un tournoi' }))
    await userEvent.type(screen.getByLabelText('Titre'), 'Tournoi')
    await userEvent.type(screen.getByLabelText('Ville'), 'Fès')
    await userEvent.type(screen.getByLabelText('Date de début'), '2026-12-10')
    await userEvent.type(screen.getByLabelText('Date de fin'), '2026-12-01')
    await userEvent.click(screen.getByRole('button', { name: 'Créer le tournoi' }))

    expect(
      await screen.findByText('La date de fin ne peut pas précéder la date de début.'),
    ).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false)
  })
})
