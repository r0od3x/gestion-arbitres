/** Hooks TanStack Query pour les arbitres. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query'

import { api } from './client'
import type {
  MyProfileUpdate,
  Page,
  Referee,
  RefereeAdminUpdate,
  RefereeFilters,
  RefereeInviteRequest,
  RefereeInviteResponse,
  RefereeProfile,
} from './types'

/** Clés de cache. Une clé par filtre : changer un filtre refait la requête. */
export const refereeKeys = {
  all: ['referees'] as const,
  list: (filters: RefereeFilters) => [...refereeKeys.all, 'list', filters] as const,
  detail: (id: string) => [...refereeKeys.all, 'detail', id] as const,
  myProfile: ['me', 'profile'] as const,
}

function toQueryString(filters: RefereeFilters): string {
  const params = new URLSearchParams()
  if (filters.grade) params.set('grade', filters.grade)
  if (filters.city) params.set('city', filters.city)
  if (filters.active !== undefined) params.set('active', String(filters.active))
  if (filters.q) params.set('q', filters.q)
  params.set('page', String(filters.page ?? 1))
  params.set('size', String(filters.size ?? 20))
  return params.toString()
}

export function useReferees(filters: RefereeFilters): UseQueryResult<Page<Referee>> {
  return useQuery({
    queryKey: refereeKeys.list(filters),
    queryFn: () => api.get<Page<Referee>>(`/referees?${toQueryString(filters)}`),
    // Garde la page précédente affichée pendant le chargement de la suivante.
    placeholderData: (previous) => previous,
  })
}

export function useReferee(id: string | undefined): UseQueryResult<Referee> {
  return useQuery({
    queryKey: refereeKeys.detail(id ?? ''),
    queryFn: () => api.get<Referee>(`/referees/${id ?? ''}`),
    enabled: id !== undefined,
  })
}

export function useInviteReferee(): UseMutationResult<
  RefereeInviteResponse,
  Error,
  RefereeInviteRequest
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: RefereeInviteRequest) =>
      api.post<RefereeInviteResponse>('/referees/invite', payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: refereeKeys.all }),
  })
}

export function useUpdateReferee(
  id: string,
): UseMutationResult<Referee, Error, RefereeAdminUpdate> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: RefereeAdminUpdate) => api.patch<Referee>(`/referees/${id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: refereeKeys.all }),
  })
}

export function useSetRefereeActive(): UseMutationResult<
  Referee,
  Error,
  { id: string; active: boolean }
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, active }) =>
      api.post<Referee>(`/referees/${id}/${active ? 'activate' : 'deactivate'}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: refereeKeys.all }),
  })
}

export function useResendInvite(): UseMutationResult<RefereeInviteResponse, Error, string> {
  return useMutation({
    mutationFn: (id: string) =>
      api.post<RefereeInviteResponse>(`/referees/${id}/invite/resend`),
  })
}

export function useMyProfile(): UseQueryResult<RefereeProfile> {
  return useQuery({
    queryKey: refereeKeys.myProfile,
    queryFn: () => api.get<RefereeProfile>('/me/profile'),
  })
}

export function useUpdateMyProfile(): UseMutationResult<
  RefereeProfile,
  Error,
  MyProfileUpdate
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: MyProfileUpdate) => api.patch<RefereeProfile>('/me/profile', payload),
    onSuccess: (profile) => {
      queryClient.setQueryData(refereeKeys.myProfile, profile)
      void queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}
