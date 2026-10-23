import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { setAccessToken } from '@/api/client'
import type { RefereeProfile } from '@/api/types'
import { ProfilePage } from '@/pages/referee/ProfilePage'

function makeProfile(overrides: Partial<RefereeProfile> = {}): RefereeProfile {
  return {
    id: 'r1',
    first_name: 'Youssef',
    last_name: 'El Amrani',
    phone_e164: '+212612345671',
    whatsapp_opt_in: false,
    whatsapp_opt_in_at: null,
    grade: 'national',
    license_number: 'ARB-001',
    city: 'Casablanca',
    club: null,
    league: null,
    photo_url: null,
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

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
  return render(<ProfilePage />, { wrapper })
}

beforeEach(() => setAccessToken('jeton-de-test'))
afterEach(() => vi.restoreAllMocks())

describe('page profil arbitre', () => {
  it('pré-remplit le formulaire avec le profil chargé', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => jsonResponse(makeProfile())),
    )
    renderPage()

    await waitFor(() => {
      expect(screen.getByLabelText('Prénom')).toHaveValue('Youssef')
    })
    expect(screen.getByLabelText('Nom')).toHaveValue('El Amrani')
    expect(screen.getByLabelText('Téléphone')).toHaveValue('+212612345671')
    expect(screen.getByLabelText('Ville')).toHaveValue('Casablanca')
  })

  it('affiche grade et licence en lecture seule', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi(() => jsonResponse(makeProfile())),
    )
    renderPage()

    await screen.findByText('National')
    expect(screen.getByText('ARB-001')).toBeInTheDocument()
    // Ces champs ne sont pas éditables : aucun contrôle de formulaire associé.
    expect(screen.queryByLabelText('Grade')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Numéro de licence')).not.toBeInTheDocument()
  })

  it('enregistre les modifications et confirme', async () => {
    const fetchMock = mockApi((_url, init) => {
      if (init?.method === 'PATCH') {
        return jsonResponse(makeProfile({ city: 'Tanger' }))
      }
      return jsonResponse(makeProfile())
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await waitFor(() => expect(screen.getByLabelText('Ville')).toHaveValue('Casablanca'))
    await userEvent.clear(screen.getByLabelText('Ville'))
    await userEvent.type(screen.getByLabelText('Ville'), 'Tanger')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Profil enregistré.')

    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
    expect(JSON.parse(requestBody(patch?.[1]))).toMatchObject({ city: 'Tanger' })
  })

  it('envoie le consentement WhatsApp quand il est coché', async () => {
    const fetchMock = mockApi((_url, init) =>
      init?.method === 'PATCH'
        ? jsonResponse(makeProfile({ whatsapp_opt_in: true }))
        : jsonResponse(makeProfile()),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    const consent = await screen.findByRole('checkbox')
    await waitFor(() => expect(consent).not.toBeChecked())

    await userEvent.click(consent)
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    await waitFor(() => {
      const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
      expect(JSON.parse(requestBody(patch?.[1]))).toMatchObject({
        whatsapp_opt_in: true,
      })
    })
  })

  it('affiche le refus du serveur quand le consentement n’a pas de numéro', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi((_url, init) =>
        init?.method === 'PATCH'
          ? jsonResponse(
              {
                detail:
                  'Un numéro de téléphone est nécessaire pour recevoir les convocations par WhatsApp.',
                code: 'validation_error',
              },
              422,
            )
          : jsonResponse(makeProfile({ phone_e164: null })),
      ),
    )
    renderPage()

    await userEvent.click(await screen.findByRole('checkbox'))
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Un numéro de téléphone est nécessaire',
    )
  })

  it('refuse un prénom vide avant tout appel réseau', async () => {
    const fetchMock = mockApi(() => jsonResponse(makeProfile()))
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    await waitFor(() => expect(screen.getByLabelText('Prénom')).toHaveValue('Youssef'))
    await userEvent.clear(screen.getByLabelText('Prénom'))
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(await screen.findByText('Saisissez votre prénom.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(false)
  })
})
