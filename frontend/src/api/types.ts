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
