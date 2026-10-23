/** Hooks TanStack Query pour les tournois et les désignations. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query'

import { api } from './client'
import type {
  Assignment,
  AssignmentsDiff,
  AssignmentWithReferee,
  AssignmentWithTournament,
  Page,
  Tournament,
  TournamentCreate,
  TournamentFilters,
  TournamentUpdate,
  TournamentWithCounts,
} from './types'

export const tournamentKeys = {
  all: ['tournaments'] as const,
  list: (filters: TournamentFilters) => [...tournamentKeys.all, 'list', filters] as const,
  detail: (id: string) => [...tournamentKeys.all, 'detail', id] as const,
  assignments: (id: string) => [...tournamentKeys.all, 'assignments', id] as const,
  myAssignments: (upcoming?: boolean) => ['me', 'assignments', upcoming] as const,
}

function toQueryString(filters: TournamentFilters): string {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.city) params.set('city', filters.city)
  if (filters.upcoming !== undefined) params.set('upcoming', String(filters.upcoming))
  if (filters.q) params.set('q', filters.q)
  params.set('page', String(filters.page ?? 1))
  params.set('size', String(filters.size ?? 20))
  return params.toString()
}

export function useTournaments(
  filters: TournamentFilters,
): UseQueryResult<Page<TournamentWithCounts>> {
  return useQuery({
    queryKey: tournamentKeys.list(filters),
    queryFn: () =>
      api.get<Page<TournamentWithCounts>>(`/tournaments?${toQueryString(filters)}`),
    placeholderData: (previous) => previous,
  })
}

export function useTournament(id: string | undefined): UseQueryResult<Tournament> {
  return useQuery({
    queryKey: tournamentKeys.detail(id ?? ''),
    queryFn: () => api.get<Tournament>(`/tournaments/${id ?? ''}`),
    enabled: id !== undefined,
  })
}

export function useCreateTournament(): UseMutationResult<Tournament, Error, TournamentCreate> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: TournamentCreate) => api.post<Tournament>('/tournaments', payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tournamentKeys.all }),
  })
}

export function useUpdateTournament(
  id: string,
): UseMutationResult<Tournament, Error, TournamentUpdate> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: TournamentUpdate) =>
      api.patch<Tournament>(`/tournaments/${id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tournamentKeys.all }),
  })
}

/** Transition de statut : publish | cancel | complete. */
export function useTournamentTransition(): UseMutationResult<
  Tournament,
  Error,
  { id: string; action: 'publish' | 'cancel' | 'complete' }
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, action }) => api.post<Tournament>(`/tournaments/${id}/${action}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tournamentKeys.all }),
  })
}

export function useTournamentAssignments(
  tournamentId: string | undefined,
): UseQueryResult<AssignmentWithReferee[]> {
  return useQuery({
    queryKey: tournamentKeys.assignments(tournamentId ?? ''),
    queryFn: () =>
      api.get<AssignmentWithReferee[]>(`/tournaments/${tournamentId ?? ''}/assignments`),
    enabled: tournamentId !== undefined,
  })
}

/** Enregistre la liste complète des arbitres désignés (mise à jour différentielle). */
export function useReplaceAssignments(
  tournamentId: string,
): UseMutationResult<AssignmentsDiff, Error, string[]> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (refereeIds: string[]) =>
      api.put<AssignmentsDiff>(`/tournaments/${tournamentId}/assignments`, {
        referee_ids: refereeIds,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tournamentKeys.all }),
  })
}

export function useMyAssignments(
  upcoming?: boolean,
): UseQueryResult<AssignmentWithTournament[]> {
  return useQuery({
    queryKey: tournamentKeys.myAssignments(upcoming),
    queryFn: () => {
      const suffix = upcoming === undefined ? '' : `?upcoming=${String(upcoming)}`
      return api.get<AssignmentWithTournament[]>(`/me/assignments${suffix}`)
    },
  })
}

export function useRespondToAssignment(): UseMutationResult<
  Assignment,
  Error,
  { id: string; confirm: boolean }
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, confirm }) =>
      api.post<Assignment>(`/me/assignments/${id}/${confirm ? 'confirm' : 'decline'}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['me', 'assignments'] }),
  })
}
