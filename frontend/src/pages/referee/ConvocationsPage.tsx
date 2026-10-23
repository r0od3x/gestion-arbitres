import { useState } from 'react'

import { ApiError } from '@/api/client'
import { useMyAssignments, useRespondToAssignment } from '@/api/tournaments'
import type { AssignmentStatus, AssignmentWithTournament } from '@/api/types'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { t } from '@/i18n'
import { cn, formatDate, formatDateRange } from '@/lib/utils'

const STATUS_LABELS: Record<AssignmentStatus, string> = {
  pending: t('status.pending'),
  confirmed: t('status.confirmed'),
  declined: t('status.declined'),
  cancelled: t('status.cancelled'),
}

const STATUS_TONES: Record<AssignmentStatus, 'neutral' | 'success' | 'warning' | 'danger'> = {
  pending: 'warning',
  confirmed: 'success',
  declined: 'danger',
  cancelled: 'neutral',
}

function ConvocationCard({
  assignment,
  canRespond,
}: {
  assignment: AssignmentWithTournament
  canRespond: boolean
}) {
  const respond = useRespondToAssignment()
  const [error, setError] = useState<string | null>(null)
  const { tournament } = assignment

  const isCancelledTournament = tournament.status === 'cancelled'
  const hasAnswered = assignment.status !== 'pending'

  async function send(confirm: boolean) {
    setError(null)
    try {
      await respond.mutateAsync({ id: assignment.id, confirm })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : t('common.error'))
    }
  }

  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold text-ink">{tournament.title}</h2>
            <p className="text-sm text-ink-muted">
              {formatDateRange(tournament.start_date, tournament.end_date)} · {tournament.city}
              {tournament.venue && ` — ${tournament.venue}`}
            </p>
            {tournament.convocation_time && (
              <p className="text-sm text-ink-muted">
                {t('convocations.convocationTime', {
                  time: tournament.convocation_time.slice(0, 5),
                })}
              </p>
            )}
          </div>
          <Badge tone={STATUS_TONES[assignment.status]}>
            {STATUS_LABELS[assignment.status]}
          </Badge>
        </div>

        {isCancelledTournament && (
          <p className="text-sm text-danger">{t('convocations.cancelledTournament')}</p>
        )}

        {assignment.responded_at ? (
          <p className="text-sm text-ink-muted">
            {t('convocations.respondedAt', {
              date: formatDate(assignment.responded_at.slice(0, 10)),
            })}
          </p>
        ) : (
          canRespond && <p className="text-sm text-ink-muted">{t('convocations.awaiting')}</p>
        )}

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}

        {canRespond && !isCancelledTournament && (
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant={assignment.status === 'confirmed' ? 'secondary' : 'primary'}
              disabled={respond.isPending}
              onClick={() => void send(true)}
            >
              {t('convocations.confirm')}
            </Button>
            <Button
              size="sm"
              variant={assignment.status === 'declined' ? 'secondary' : 'ghost'}
              disabled={respond.isPending}
              onClick={() => void send(false)}
            >
              {t('convocations.decline')}
            </Button>
            {hasAnswered && (
              <span className="self-center text-xs text-ink-muted">
                {t('convocations.change')}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function ConvocationsPage() {
  const [upcoming, setUpcoming] = useState(true)
  const { data, isPending, isError, refetch } = useMyAssignments(upcoming)

  const tabs = [
    { value: true, label: t('convocations.tabUpcoming') },
    { value: false, label: t('convocations.tabPast') },
  ]

  return (
    <>
      <PageHeader title={t('convocations.title')} />

      <div role="tablist" className="mb-4 flex gap-1">
        {tabs.map((tab) => (
          <button
            key={String(tab.value)}
            role="tab"
            type="button"
            aria-selected={upcoming === tab.value}
            onClick={() => setUpcoming(tab.value)}
            className={cn(
              'rounded-lg px-3 py-1.5 text-sm transition-colors',
              upcoming === tab.value
                ? 'bg-brand text-brand-ink'
                : 'text-ink-muted hover:bg-surface-raised hover:text-ink',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isPending && <p className="text-sm text-ink-muted">{t('common.loading')}</p>}

      {isError && (
        <EmptyState
          message={t('common.error')}
          action={
            <Button variant="secondary" onClick={() => void refetch()}>
              {t('common.retry')}
            </Button>
          }
        />
      )}

      {data && data.length === 0 && (
        <EmptyState
          message={upcoming ? t('convocations.emptyUpcoming') : t('convocations.emptyPast')}
        />
      )}

      {data && data.length > 0 && (
        <div className="space-y-4">
          {data.map((assignment) => (
            <ConvocationCard
              key={assignment.id}
              assignment={assignment}
              // On ne répond plus à un tournoi passé : le serveur refuserait.
              canRespond={upcoming}
            />
          ))}
        </div>
      )}
    </>
  )
}
