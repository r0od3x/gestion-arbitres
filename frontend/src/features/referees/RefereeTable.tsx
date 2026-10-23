import { useSetRefereeActive } from '@/api/referees'
import type { Referee, RefereeGrade } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { t } from '@/i18n'

const GRADE_LABELS: Record<RefereeGrade, string> = {
  regional: t('grade.regional'),
  national: t('grade.national'),
  continental: t('grade.continental'),
  international: t('grade.international'),
}

function AccountBadge({ referee }: { referee: Referee }) {
  if (!referee.is_active) {
    return <Badge tone="danger">{t('referees.account.inactive')}</Badge>
  }
  // Un compte actif mais jamais activé par l'arbitre mérite d'être signalé :
  // il ne peut pas encore se connecter.
  if (!referee.has_accepted_invite) {
    return <Badge tone="warning">{t('referees.account.pending')}</Badge>
  }
  return <Badge tone="success">{t('referees.account.active')}</Badge>
}

export function RefereeTable({ referees }: { referees: Referee[] }) {
  const setActive = useSetRefereeActive()

  return (
    <div className="overflow-x-auto rounded-xl border border-border-subtle">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border-subtle bg-surface-raised text-left">
            <th scope="col" className="px-4 py-3 font-medium">
              {t('referees.column.name')}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('referees.column.contact')}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('referees.column.grade')}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('referees.column.city')}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('referees.column.status')}
            </th>
            <th scope="col" className="px-4 py-3 text-right font-medium">
              {t('referees.column.actions')}
            </th>
          </tr>
        </thead>
        <tbody>
          {referees.map((referee) => (
            <tr key={referee.id} className="border-b border-border-subtle last:border-0">
              <td className="px-4 py-3">
                <div className="font-medium text-ink">
                  {referee.first_name} {referee.last_name}
                </div>
                {referee.license_number && (
                  <div className="text-xs text-ink-muted">{referee.license_number}</div>
                )}
              </td>
              <td className="px-4 py-3">
                <div className="text-ink">{referee.email}</div>
                <div className="text-xs text-ink-muted">
                  {referee.phone_e164 ?? t('common.notProvided')}
                  {referee.phone_e164 && !referee.whatsapp_opt_in && (
                    <> · {t('referees.whatsapp.optedOut')}</>
                  )}
                </div>
              </td>
              <td className="px-4 py-3">{GRADE_LABELS[referee.grade]}</td>
              <td className="px-4 py-3">{referee.city ?? t('common.notProvided')}</td>
              <td className="px-4 py-3">
                <AccountBadge referee={referee} />
              </td>
              <td className="px-4 py-3 text-right">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={setActive.isPending}
                  onClick={() =>
                    setActive.mutate({ id: referee.id, active: !referee.is_active })
                  }
                >
                  {referee.is_active
                    ? t('referees.action.deactivate')
                    : t('referees.action.activate')}
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
