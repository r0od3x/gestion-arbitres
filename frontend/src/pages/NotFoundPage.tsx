import { Link } from 'react-router-dom'

import { buttonVariants } from '@/components/ui/button-variants'
import { t } from '@/i18n'

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <p className="text-5xl font-semibold text-ink-muted">404</p>
      <p className="text-ink">{t('common.notFound')}</p>
      <Link to="/" className={buttonVariants({ variant: 'secondary' })}>
        {t('common.backHome')}
      </Link>
    </div>
  )
}
