import { useMemo, useState } from 'react'

import { ApiError } from '@/api/client'
import { useReferees } from '@/api/referees'
import { useReplaceAssignments, useTournamentAssignments } from '@/api/tournaments'
import type { RefereeFilters as Filters, RefereeGrade } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { RefereeFilters } from '@/features/referees/RefereeFilters'
import { t } from '@/i18n'

const GRADE_LABELS: Record<RefereeGrade, string> = {
  regional: t('grade.regional'),
  national: t('grade.national'),
  continental: t('grade.continental'),
  international: t('grade.international'),
}

interface RefereePickerProps {
  tournamentId: string
  /** Faux si le tournoi est annulé ou terminé : plus aucune désignation. */
  editable: boolean
}

export function RefereePicker({ tournamentId, editable }: RefereePickerProps) {
  // Seuls les comptes actifs sont convocables : le backend refuse les autres.
  const [filters, setFilters] = useState<Filters>({ page: 1, size: 100, active: true })
  const { data: referees, isPending } = useReferees(filters)
  const { data: assignments } = useTournamentAssignments(tournamentId)
  const replace = useReplaceAssignments(tournamentId)

  // `null` = l'utilisateur n'a rien touché, la sélection suit le serveur.
  // Dès qu'il coche quelque chose, son brouillon prend le relais. Pas d'effet
  // de synchronisation : la valeur affichée est dérivée, jamais recopiée.
  const [draft, setDraft] = useState<Set<string> | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const assignedIds = useMemo(
    () => (assignments ?? []).map((assignment) => assignment.referee_id),
    [assignments],
  )
  const serverSelection = useMemo(() => new Set(assignedIds), [assignedIds])
  const selected = draft ?? serverSelection

  const notifiableById = useMemo(() => {
    const map = new Map<string, boolean>()
    for (const assignment of assignments ?? []) {
      map.set(assignment.referee_id, assignment.is_notifiable)
    }
    return map
  }, [assignments])

  function toggle(refereeId: string) {
    const next = new Set(selected)
    if (next.has(refereeId)) next.delete(refereeId)
    else next.add(refereeId)
    setDraft(next)
  }

  async function save() {
    setFormError(null)
    try {
      await replace.mutateAsync([...selected])
      // Le serveur fait de nouveau foi : on repasse sur sa version.
      setDraft(null)
    } catch (error) {
      setFormError(error instanceof ApiError ? error.detail : t('common.error'))
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('assignments.title')}</CardTitle>
        <CardDescription>
          {editable ? t('assignments.description') : t('assignments.frozen')}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <RefereeFilters filters={filters} onChange={setFilters} />

        {isPending && <p className="text-sm text-ink-muted">{t('common.loading')}</p>}

        {referees && referees.items.length > 0 && (
          <ul className="divide-y divide-border-subtle rounded-lg border border-border-subtle">
            {referees.items.map((referee) => {
              const isSelected = selected.has(referee.id)
              // Pour un arbitre déjà convoqué, le serveur fait foi ; sinon on
              // déduit du profil (consentement + numéro).
              const notifiable =
                notifiableById.get(referee.id) ??
                (referee.whatsapp_opt_in && referee.phone_e164 !== null)

              return (
                <li key={referee.id}>
                  <label className="flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-surface">
                    <Checkbox
                      checked={isSelected}
                      disabled={!editable}
                      onChange={() => toggle(referee.id)}
                    />
                    <span className="flex-1">
                      <span className="font-medium text-ink">
                        {referee.first_name} {referee.last_name}
                      </span>
                      <span className="block text-xs text-ink-muted">
                        {GRADE_LABELS[referee.grade]}
                        {referee.city && ` · ${referee.city}`}
                      </span>
                    </span>
                    {isSelected && !notifiable && (
                      <Badge tone="warning" title={t('assignments.notNotifiableHint')}>
                        {t('assignments.notNotifiable')}
                      </Badge>
                    )}
                  </label>
                </li>
              )
            })}
          </ul>
        )}

        {referees && referees.items.length === 0 && (
          <p className="text-sm text-ink-muted">{t('referees.emptyFiltered')}</p>
        )}

        {formError && (
          <p role="alert" className="text-sm text-danger">
            {formError}
          </p>
        )}

        {replace.isSuccess && !formError && (
          <p role="status" className="text-sm text-success">
            {t('assignments.saved', {
              added: replace.data.added,
              cancelled: replace.data.cancelled,
              unchanged: replace.data.unchanged,
            })}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <Button disabled={!editable || replace.isPending} onClick={() => void save()}>
            {replace.isPending ? t('assignments.saving') : t('assignments.save')}
          </Button>
          <span className="text-sm text-ink-muted">
            {selected.size === 0
              ? t('assignments.noneSelected')
              : t('assignments.selected', { count: selected.size })}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
