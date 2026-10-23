import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { t } from '@/i18n'

/** Liste des arbitres. Branchée sur `GET /referees` au jalon M2. */
export function RefereesPage() {
  return (
    <>
      <PageHeader
        title={t('referees.title')}
        action={<Button disabled>{t('referees.invite')}</Button>}
      />
      <EmptyState message={t('referees.empty')} />
    </>
  )
}
