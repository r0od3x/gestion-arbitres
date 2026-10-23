import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { setAccessToken } from '@/api/client'
import type { AssignmentWithTournament } from '@/api/types'
import { ConvocationsPage } from '@/pages/referee/ConvocationsPage'

function makeAssignment(
  overrides: Partial<AssignmentWithTournament> = {},
): AssignmentWithTournament {
  return {
    id: 'a1',
    tournament_id: 'tour1',
    referee_id: 'ref1',
    role_in_tournament: null,
    status: 'pending',
    responded_at: null,
    created_at: '2026-01-01T00:00:00Z',
    tournament: {
      id: 'tour1',
      title: 'Championnat régional',
      description: null,
      venue: 'Complexe Mohammed V',
      city: 'Casablanca',
      start_date: '2026-11-12',
      end_date: '2026-11-14',
      convocation_time: '08:30:00',
      referees_needed: 4,
      status: 'published',
      created_at: '2026-01-01T00:00:00Z',
    },
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
  return render(<ConvocationsPage />, { wrapper })
}

beforeEach(() => setAccessToken('jeton-de-test'))
afterEach(() => vi.restoreAllMocks())

describe('mes convocations', () => {
  it('affiche la convocation avec ses détails', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => jsonResponse([makeAssignment()])),
    )
    renderPage()

    expect(await screen.findByText('Championnat régional')).toBeInTheDocument()
    expect(screen.getByText(/Casablanca/)).toBeInTheDocument()
    expect(screen.getByText('Présence à 08:30')).toBeInTheDocument()
    expect(screen.getByText('En attente')).toBeInTheDocument()
  })

  it('demande les convocations à venir par défaut', async () => {
    const fetchMock = mockApi(() => jsonResponse([]))
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await screen.findByText("Vous n'avez aucune convocation à venir.")
    expect(
      fetchMock.mock.calls.some(([url]) => requestUrl(url).includes('upcoming=true')),
    ).toBe(true)
  })

  it('bascule sur les convocations passées', async () => {
    const fetchMock = mockApi(() => jsonResponse([]))
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await screen.findByText("Vous n'avez aucune convocation à venir.")
    await userEvent.click(screen.getByRole('tab', { name: 'Passées' }))

    expect(
      await screen.findByText("Vous n'avez aucune convocation passée."),
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([url]) => requestUrl(url).includes('upcoming=false')),
      ).toBe(true)
    })
  })

  it('confirme une convocation', async () => {
    const fetchMock = mockApi((url, init) => {
      if (url.includes('/confirm') && init?.method === 'POST') {
        return jsonResponse(makeAssignment({ status: 'confirmed' }))
      }
      return jsonResponse([makeAssignment()])
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Je confirme' }))

    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => requestUrl(url).includes('/confirm'))).toBe(
        true,
      )
    })
  })

  it('décline une convocation', async () => {
    const fetchMock = mockApi((url, init) => {
      if (url.includes('/decline') && init?.method === 'POST') {
        return jsonResponse(makeAssignment({ status: 'declined' }))
      }
      return jsonResponse([makeAssignment()])
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Je ne peux pas' }))

    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => requestUrl(url).includes('/decline'))).toBe(
        true,
      )
    })
  })

  it("n'offre aucune réponse sur une convocation passée", async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => jsonResponse([makeAssignment({ status: 'confirmed' })])),
    )
    renderPage()

    await screen.findByText('Championnat régional')
    await userEvent.click(screen.getByRole('tab', { name: 'Passées' }))

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Je confirme' })).not.toBeInTheDocument()
    })
  })

  it('signale un tournoi annulé et retire les boutons', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() =>
        jsonResponse([
          makeAssignment({
            tournament: { ...makeAssignment().tournament, status: 'cancelled' },
          }),
        ]),
      ),
    )
    renderPage()

    expect(await screen.findByText('Ce tournoi a été annulé.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Je confirme' })).not.toBeInTheDocument()
  })

  it('remonte le refus du serveur sur une réponse impossible', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi((url, init) => {
        if (url.includes('/confirm') && init?.method === 'POST') {
          return jsonResponse(
            { detail: 'Ce tournoi est déjà passé.', code: 'invalid_state' },
            409,
          )
        }
        return jsonResponse([makeAssignment()])
      }),
    )
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Je confirme' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Ce tournoi est déjà passé.')
  })
})
