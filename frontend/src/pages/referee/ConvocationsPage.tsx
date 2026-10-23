import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { t } from '@/i18n'

/** Convocations de l'arbitre connecté. Branchée sur `GET /me/assignments` au jalon M3. */
export function ConvocationsPage() {
  return (
    <>
      <PageHeader title={t('convocations.title')} />
      <EmptyState message={t('convocations.empty')} />
    </>
  )
}
