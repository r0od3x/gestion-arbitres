import { useAuth } from '@/auth/useAuth'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { t } from '@/i18n'

/** Tableau de bord administrateur. Les compteurs arrivent au jalon M3. */
export function DashboardPage() {
  const { user } = useAuth()

  return (
    <>
      <PageHeader title={t('nav.dashboard')} />
      <Card>
        <CardHeader>
          <CardTitle>{t('app.title')}</CardTitle>
          <CardDescription>{user?.email}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-ink-muted">
            Les statistiques (arbitres actifs, tournois à venir, convocations en attente) seront
            ajoutées avec les jalons M2 et M3.
          </p>
        </CardContent>
      </Card>
    </>
  )
}
