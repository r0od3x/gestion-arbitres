import { Link, useParams } from 'react-router-dom'

import { useTournament } from '@/api/tournaments'
import type { TournamentStatus } from '@/api/types'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { RefereePicker } from '@/features/tournaments/RefereePicker'
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

/** Un tournoi annulé ou terminé n'accepte plus de désignation. */
const FROZEN: TournamentStatus[] = ['cancelled', 'completed']

export function TournamentDetailPage() {
  const { tournamentId } = useParams<{ tournamentId: string }>()
  const { data: tournament, isPending, isError } = useTournament(tournamentId)

  if (isPending) {
    return (
      <>
        <PageHeader title={t('tournaments.title')} />
        <p className="text-sm text-ink-muted">{t('common.loading')}</p>
      </>
    )
  }

  if (isError || !tournament) {
    return (
      <>
        <PageHeader title={t('tournaments.title')} />
        <p role="alert" className="text-sm text-danger">
          {t('common.error')}
        </p>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title={tournament.title}
        action={
          <Link
            to="/admin/tournois"
            className="inline-flex h-10 items-center rounded-lg border border-border-subtle px-4 text-sm hover:bg-surface"
          >
            {t('tournaments.action.back')}
          </Link>
        }
      />

      <Card className="mb-6">
        <CardContent className="grid gap-4 pt-6 sm:grid-cols-3">
          <div>
            <p className="text-sm text-ink-muted">{t('tournaments.column.dates')}</p>
            <p className="text-ink">
              {formatDateRange(tournament.start_date, tournament.end_date)}
            </p>
          </div>
          <div>
            <p className="text-sm text-ink-muted">{t('tournaments.column.city')}</p>
            <p className="text-ink">
              {tournament.city}
              {tournament.venue && ` — ${tournament.venue}`}
            </p>
          </div>
          <div>
            <p className="text-sm text-ink-muted">{t('tournaments.column.status')}</p>
            <Badge tone={STATUS_TONES[tournament.status]}>
              {STATUS_LABELS[tournament.status]}
            </Badge>
          </div>
          {tournament.convocation_time && (
            <div>
              <p className="text-sm text-ink-muted">{t('tournamentForm.convocationTime')}</p>
              <p className="text-ink">{tournament.convocation_time.slice(0, 5)}</p>
            </div>
          )}
          {tournament.referees_needed !== null && (
            <div>
              <p className="text-sm text-ink-muted">{t('tournamentForm.refereesNeeded')}</p>
              <p className="text-ink">{tournament.referees_needed}</p>
            </div>
          )}
          {tournament.description && (
            <p className="text-sm text-ink-muted sm:col-span-3">{tournament.description}</p>
          )}
        </CardContent>
      </Card>

      {tournamentId && (
        <RefereePicker
          tournamentId={tournamentId}
          editable={!FROZEN.includes(tournament.status)}
        />
      )}
    </>
  )
}
