import { useAuth } from '@/auth/useAuth'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { t } from '@/i18n'

/** Profil de l'arbitre. L'édition arrive au jalon M2 (`PATCH /me/profile`). */
export function ProfilePage() {
  const { user } = useAuth()
  const profile = user?.referee_profile

  return (
    <>
      <PageHeader title={t('profile.title')} />
      <Card>
        <CardContent className="space-y-3 pt-6">
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-sm text-ink-muted">{t('login.email')}</dt>
              <dd className="text-ink">{user?.email}</dd>
            </div>
            {profile && (
              <>
                <div>
                  <dt className="text-sm text-ink-muted">Nom</dt>
                  <dd className="text-ink">
                    {profile.first_name} {profile.last_name}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-ink-muted">WhatsApp</dt>
                  <dd className="text-ink">{profile.phone_e164 ?? '—'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-ink-muted">{t('profile.whatsappOptIn')}</dt>
                  <dd className="text-ink">{profile.whatsapp_opt_in ? 'Oui' : 'Non'}</dd>
                </div>
              </>
            )}
          </dl>
        </CardContent>
      </Card>
    </>
  )
}
