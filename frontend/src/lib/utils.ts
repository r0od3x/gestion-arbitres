import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Fusionne des classes Tailwind en résolvant les conflits. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

/** Formate une date ISO (YYYY-MM-DD) au format français. */
export function formatDate(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return isoDate
  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' }).format(parsed)
}

/** Plage de dates d'un tournoi, sans répéter la date si elle est identique. */
export function formatDateRange(start: string, end: string): string {
  return start === end ? formatDate(start) : `${formatDate(start)} — ${formatDate(end)}`
}
