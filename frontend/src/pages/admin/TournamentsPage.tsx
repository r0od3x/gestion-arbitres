import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { t } from '@/i18n'

/** Liste des tournois. Branchée sur `GET /tournaments` au jalon M3. */
export function TournamentsPage() {
  return (
    <>
      <PageHeader
        title={t('tournaments.title')}
        action={<Button disabled>{t('tournaments.create')}</Button>}
      />
      <EmptyState message={t('tournaments.empty')} />
    </>
  )
}
