import { useState } from 'react'

import { useTournaments } from '@/api/tournaments'
import type { TournamentFilters, TournamentStatus } from '@/api/types'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { TournamentForm } from '@/features/tournaments/TournamentForm'
import { TournamentTable } from '@/features/tournaments/TournamentTable'
import { t } from '@/i18n'

const PAGE_SIZE = 20

const STATUSES: TournamentStatus[] = ['draft', 'published', 'cancelled', 'completed']

const STATUS_LABELS: Record<TournamentStatus, string> = {
  draft: t('status.draft'),
  published: t('status.published'),
  cancelled: t('status.cancelled'),
  completed: t('status.completed'),
}

export function TournamentsPage() {
  const [filters, setFilters] = useState<TournamentFilters>({ page: 1, size: PAGE_SIZE })
  const [isCreating, setIsCreating] = useState(false)
  const { data, isPending, isError, refetch } = useTournaments(filters)

  const page = filters.page ?? 1
  const pages = data ? Math.max(1, Math.ceil(data.total / (data.size || PAGE_SIZE))) : 1
  const isFiltered =
    filters.q !== undefined || filters.status !== undefined || filters.upcoming !== undefined

  function update(patch: Partial<TournamentFilters>) {
    setFilters({ ...filters, ...patch, page: 1 })
  }

  return (
    <>
      <PageHeader
        title={t('tournaments.title')}
        action={
          !isCreating && (
            <Button onClick={() => setIsCreating(true)}>{t('tournaments.create')}</Button>
          )
        }
      />

      {isCreating && (
        <div className="mb-6">
          <TournamentForm onClose={() => setIsCreating(false)} />
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="min-w-56 flex-1">
          <label htmlFor="tournament-search" className="sr-only">
            {t('tournaments.search')}
          </label>
          <Input
            id="tournament-search"
            type="search"
            placeholder={t('tournaments.search')}
            value={filters.q ?? ''}
            onChange={(event) => update({ q: event.target.value || undefined })}
          />
        </div>

        <div>
          <label htmlFor="tournament-status" className="sr-only">
            {t('tournaments.column.status')}
          </label>
          <Select
            id="tournament-status"
            value={filters.status ?? ''}
            onChange={(event) =>
              update({
                status: (event.target.value || undefined) as TournamentStatus | undefined,
              })
            }
          >
            <option value="">{t('tournaments.filters.allStatuses')}</option>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {STATUS_LABELS[status]}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <label htmlFor="tournament-period" className="sr-only">
            {t('tournaments.column.dates')}
          </label>
          <Select
            id="tournament-period"
            value={filters.upcoming === undefined ? '' : String(filters.upcoming)}
            onChange={(event) =>
              update({
                upcoming: event.target.value === '' ? undefined : event.target.value === 'true',
              })
            }
          >
            <option value="">{t('tournaments.filters.allPeriods')}</option>
            <option value="true">{t('tournaments.filters.upcoming')}</option>
            <option value="false">{t('tournaments.filters.past')}</option>
          </Select>
        </div>
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

      {data && data.items.length === 0 && (
        <EmptyState
          message={isFiltered ? t('tournaments.emptyFiltered') : t('tournaments.empty')}
        />
      )}

      {data && data.items.length > 0 && (
        <>
          <p className="mb-2 text-sm text-ink-muted">
            {t('tournaments.count', { count: data.total })}
          </p>
          <TournamentTable tournaments={data.items} />

          {pages > 1 && (
            <div className="mt-4 flex items-center justify-between gap-3">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setFilters({ ...filters, page: page - 1 })}
              >
                {t('referees.page.previous')}
              </Button>
              <span className="text-sm text-ink-muted">
                {t('referees.page.position', { page, pages })}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= pages}
                onClick={() => setFilters({ ...filters, page: page + 1 })}
              >
                {t('referees.page.next')}
              </Button>
            </div>
          )}
        </>
      )}
    </>
  )
}
