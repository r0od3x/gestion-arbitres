import { t } from '@/i18n'

export function FullPageSpinner() {
  return (
    <div className="flex h-full min-h-screen items-center justify-center" role="status">
      <span className="sr-only">{t('common.loading')}</span>
      <div
        aria-hidden="true"
        className="size-8 animate-spin rounded-full border-2 border-border-subtle border-t-brand"
      />
    </div>
  )
}
