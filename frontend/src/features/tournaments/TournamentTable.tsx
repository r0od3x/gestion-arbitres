import { Link } from 'react-router-dom'

import { useTournamentTransition } from '@/api/tournaments'
import type { TournamentStatus, TournamentWithCounts } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { t } from '@/i18n'
import { formatDateRange } from '@/lib/utils'

const STATUS_LABELS: Record<TournamentStatus, string> = {
  draft: t('status.draft'),
  published: t('status.published'),
  cancelled: t('status.cancelled'),
  completed: t('status.completed'),
}

const STATUS_TONES: Record<TournamentStatus, 'neutral' | 'success' | 'warning' | 'danger'> = {
  draft: 'warning',
  published: 'success',
  cancelled: 'danger',
  completed: 'neutral',
}

/** Transitions proposées, alignées sur la machine à états du backend. */
const ACTIONS: Record<TournamentStatus, ('publish' | 'cancel' | 'complete')[]> = {
  draft: ['publish', 'cancel'],
  published: ['complete', 'cancel'],
  cancelled: [],
  completed: [],
}

const ACTION_LABELS = {
  publish: t('tournaments.action.publish'),
  cancel: t('tournaments.action.cancel'),
  complete: t('tournaments.action.complete'),
} as const

function Staffing({ tournament }: { tournament: TournamentWithCounts }) {
  const { assigned_count, confirmed_count, referees_needed } = tournament
  const text =
    referees_needed === null
      ? t('tournaments.staffing', { assigned: assigned_count, confirmed: confirmed_count })
      : t('tournaments.staffingNeeded', {
          assigned: assigned_count,
          needed: referees_needed,
          confirmed: confirmed_count,
        })
  return <span className="text-sm text-ink-muted">{text}</span>
}

export function TournamentTable({ tournaments }: { tournaments: TournamentWithCounts[] }) {
  const transition = useTournamentTransition()

  return (
    <div className="overflow-x-auto rounded-xl border border-border-subtle">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border-subtle bg-surface-raised text-left">
            <th scope="col" className="px-4 py-3 font-medium">
              {t('tournaments.column.title')}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('tournaments.column.dates')}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('tournaments.column.city')}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('tournaments.column.referees')}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('tournaments.column.status')}
            </th>
            <th scope="col" className="px-4 py-3 text-right font-medium">
              {t('tournaments.column.actions')}
            </th>
          </tr>
        </thead>
        <tbody>
          {tournaments.map((tournament) => (
            <tr key={tournament.id} className="border-b border-border-subtle last:border-0">
              <td className="px-4 py-3">
                <div className="font-medium text-ink">{tournament.title}</div>
                {tournament.venue && (
                  <div className="text-xs text-ink-muted">{tournament.venue}</div>
                )}
              </td>
              <td className="px-4 py-3 text-ink-muted">
                {formatDateRange(tournament.start_date, tournament.end_date)}
              </td>
              <td className="px-4 py-3">{tournament.city}</td>
              <td className="px-4 py-3">
                <Staffing tournament={tournament} />
              </td>
              <td className="px-4 py-3">
                <Badge tone={STATUS_TONES[tournament.status]}>
                  {STATUS_LABELS[tournament.status]}
                </Badge>
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap justify-end gap-2">
                  <Link
                    to={`/admin/tournois/${tournament.id}`}
                    className="inline-flex h-8 items-center rounded-lg border border-border-subtle px-3 text-sm hover:bg-surface"
                  >
                    {t('tournaments.action.manage')}
                  </Link>
                  {ACTIONS[tournament.status].map((action) => (
                    <Button
                      key={action}
                      variant={action === 'cancel' ? 'ghost' : 'secondary'}
                      size="sm"
                      disabled={transition.isPending}
                      onClick={() => transition.mutate({ id: tournament.id, action })}
                    >
                      {ACTION_LABELS[action]}
                    </Button>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
