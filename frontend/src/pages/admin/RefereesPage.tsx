import { useState } from 'react'

import { useReferees } from '@/api/referees'
import type { RefereeFilters as Filters } from '@/api/types'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { InviteRefereeForm } from '@/features/referees/InviteRefereeForm'
import { RefereeFilters } from '@/features/referees/RefereeFilters'
import { RefereeTable } from '@/features/referees/RefereeTable'
import { t } from '@/i18n'

const PAGE_SIZE = 20

export function RefereesPage() {
  const [filters, setFilters] = useState<Filters>({ page: 1, size: PAGE_SIZE })
  const [isInviting, setIsInviting] = useState(false)
  const { data, isPending, isError, refetch } = useReferees(filters)

  const page = filters.page ?? 1
  const pages = data ? Math.max(1, Math.ceil(data.total / (data.size || PAGE_SIZE))) : 1
  const isFiltered =
    filters.q !== undefined ||
    filters.grade !== undefined ||
    filters.city !== undefined ||
    filters.active !== undefined

  return (
    <>
      <PageHeader
        title={t('referees.title')}
        action={
          !isInviting && (
            <Button onClick={() => setIsInviting(true)}>{t('referees.invite')}</Button>
          )
        }
      />

      {isInviting && (
        <div className="mb-6">
          <InviteRefereeForm onClose={() => setIsInviting(false)} />
        </div>
      )}

      <RefereeFilters filters={filters} onChange={setFilters} />

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
        <EmptyState message={isFiltered ? t('referees.emptyFiltered') : t('referees.empty')} />
      )}

      {data && data.items.length > 0 && (
        <>
          <p className="mb-2 text-sm text-ink-muted">
            {t('referees.count', { count: data.total })}
          </p>
          <RefereeTable referees={data.items} />

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
