import type { RefereeFilters as Filters, RefereeGrade } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { t } from '@/i18n'

const GRADES: RefereeGrade[] = ['regional', 'national', 'continental', 'international']

const GRADE_LABELS: Record<RefereeGrade, string> = {
  regional: t('grade.regional'),
  national: t('grade.national'),
  continental: t('grade.continental'),
  international: t('grade.international'),
}

interface RefereeFiltersProps {
  filters: Filters
  onChange: (filters: Filters) => void
}

export function RefereeFilters({ filters, onChange }: RefereeFiltersProps) {
  /** Tout changement de filtre renvoie à la première page. */
  function update(patch: Partial<Filters>) {
    onChange({ ...filters, ...patch, page: 1 })
  }

  const hasFilters =
    filters.q !== undefined ||
    filters.grade !== undefined ||
    filters.city !== undefined ||
    filters.active !== undefined

  return (
    <div className="mb-4 flex flex-wrap items-end gap-3">
      <div className="min-w-56 flex-1">
        <label htmlFor="referee-search" className="sr-only">
          {t('referees.search')}
        </label>
        <Input
          id="referee-search"
          type="search"
          placeholder={t('referees.search')}
          value={filters.q ?? ''}
          onChange={(event) => update({ q: event.target.value || undefined })}
        />
      </div>

      <div>
        <label htmlFor="referee-grade" className="sr-only">
          {t('referees.column.grade')}
        </label>
        <Select
          id="referee-grade"
          value={filters.grade ?? ''}
          onChange={(event) =>
            update({ grade: (event.target.value || undefined) as RefereeGrade | undefined })
          }
        >
          <option value="">{t('referees.filters.allGrades')}</option>
          {GRADES.map((grade) => (
            <option key={grade} value={grade}>
              {GRADE_LABELS[grade]}
            </option>
          ))}
        </Select>
      </div>

      <div>
        <label htmlFor="referee-city" className="sr-only">
          {t('referees.filters.city')}
        </label>
        <Input
          id="referee-city"
          placeholder={t('referees.filters.city')}
          value={filters.city ?? ''}
          onChange={(event) => update({ city: event.target.value || undefined })}
        />
      </div>

      <div>
        <label htmlFor="referee-status" className="sr-only">
          {t('referees.column.status')}
        </label>
        <Select
          id="referee-status"
          value={filters.active === undefined ? '' : String(filters.active)}
          onChange={(event) =>
            update({
              active: event.target.value === '' ? undefined : event.target.value === 'true',
            })
          }
        >
          <option value="">{t('referees.filters.allStatuses')}</option>
          <option value="true">{t('referees.account.active')}</option>
          <option value="false">{t('referees.account.inactive')}</option>
        </Select>
      </div>

      {hasFilters && (
        <Button variant="ghost" onClick={() => onChange({ page: 1, size: filters.size })}>
          {t('referees.filters.reset')}
        </Button>
      )}
    </div>
  )
}
