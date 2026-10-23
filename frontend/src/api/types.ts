/**
 * Types de l'API.
 *
 * Provisoires : `npm run api:generate` produit `src/api/schema.d.ts` depuis
 * l'OpenAPI du backend, qui fera foi dès que les routes M2+ existeront.
 */

export type UserRole = 'admin' | 'referee'
export type RefereeGrade = 'regional' | 'national' | 'continental' | 'international'
export type TournamentStatus = 'draft' | 'published' | 'cancelled' | 'completed'
export type AssignmentStatus = 'pending' | 'confirmed' | 'declined' | 'cancelled'
export type NotificationStatus = 'queued' | 'sent' | 'delivered' | 'read' | 'failed'

export interface RefereeProfile {
  id: string
  first_name: string
  last_name: string
  phone_e164: string | null
  whatsapp_opt_in: boolean
  whatsapp_opt_in_at: string | null
  grade: RefereeGrade
  license_number: string | null
  city: string | null
  club: string | null
  league: string | null
  photo_url: string | null
}

export interface CurrentUser {
  id: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
  last_login_at: string | null
  referee_profile: RefereeProfile | null
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

/** Arbitre vu par un administrateur : profil + état du compte. */
export interface Referee extends RefereeProfile {
  user_id: string
  email: string
  is_active: boolean
  /** Faux tant que l'invitation n'a pas été acceptée. */
  has_accepted_invite: boolean
  created_at: string
  notes_admin: string | null
}

export interface RefereeInviteRequest {
  email: string
  first_name: string
  last_name: string
  phone?: string | null
  grade: RefereeGrade
  license_number?: string | null
  city?: string | null
  club?: string | null
  league?: string | null
  notes_admin?: string | null
}

export interface RefereeInviteResponse {
  referee: Referee
  invite_url: string
  invite_expires_in_hours: number
}

export interface RefereeAdminUpdate {
  first_name?: string
  last_name?: string
  phone?: string | null
  grade?: RefereeGrade
  license_number?: string | null
  city?: string | null
  club?: string | null
  league?: string | null
  notes_admin?: string | null
  whatsapp_opt_in?: boolean
}

/** Champs qu'un arbitre peut modifier lui-même. */
export interface MyProfileUpdate {
  first_name?: string
  last_name?: string
  phone?: string | null
  whatsapp_opt_in?: boolean
  city?: string | null
  club?: string | null
  league?: string | null
}

export interface RefereeFilters {
  grade?: RefereeGrade
  city?: string
  active?: boolean
  q?: string
  page?: number
  size?: number
}

export interface Tournament {
  id: string
  title: string
  description: string | null
  venue: string | null
  city: string
  start_date: string
  end_date: string
  convocation_time: string | null
  referees_needed: number | null
  status: TournamentStatus
  created_at: string
}

/** Vue liste : compteurs calculés côté serveur, pas de requête par ligne. */
export interface TournamentWithCounts extends Tournament {
  assigned_count: number
  confirmed_count: number
}

export interface TournamentCreate {
  title: string
  description?: string | null
  venue?: string | null
  city: string
  start_date: string
  end_date: string
  convocation_time?: string | null
  referees_needed?: number | null
}

export type TournamentUpdate = Partial<TournamentCreate>

export interface TournamentFilters {
  status?: TournamentStatus
  city?: string
  upcoming?: boolean
  q?: string
  page?: number
  size?: number
}

export interface AssignmentReferee {
  id: string
  first_name: string
  last_name: string
  phone_e164: string | null
  whatsapp_opt_in: boolean
  city: string | null
}

export interface Assignment {
  id: string
  tournament_id: string
  referee_id: string
  role_in_tournament: string | null
  status: AssignmentStatus
  responded_at: string | null
  created_at: string
}

/** Vue administrateur d'une désignation. */
export interface AssignmentWithReferee extends Assignment {
  referee: AssignmentReferee
  notification_status: NotificationStatus | null
  notification_error: string | null
  /** Faux si l'arbitre n'a pas consenti ou n'a pas de numéro valide. */
  is_notifiable: boolean
}

/** Vue arbitre : « mes convocations ». */
export interface AssignmentWithTournament extends Assignment {
  tournament: Tournament
}

export interface AssignmentsDiff {
  added: number
  cancelled: number
  unchanged: number
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface ApiErrorBody {
  detail: string
  code?: string
}
