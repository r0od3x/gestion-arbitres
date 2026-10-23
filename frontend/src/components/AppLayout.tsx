import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/button'
import { t, type TranslationKey } from '@/i18n'
import { cn } from '@/lib/utils'

interface NavItem {
  to: string
  labelKey: TranslationKey
}

const ADMIN_NAV: NavItem[] = [
  { to: '/admin', labelKey: 'nav.dashboard' },
  { to: '/admin/arbitres', labelKey: 'nav.referees' },
  { to: '/admin/tournois', labelKey: 'nav.tournaments' },
]

const REFEREE_NAV: NavItem[] = [
  { to: '/mes-convocations', labelKey: 'nav.convocations' },
  { to: '/mon-profil', labelKey: 'nav.profile' },
]

export function AppLayout() {
  const { user, isAdmin, logout } = useAuth()
  const items = isAdmin ? ADMIN_NAV : REFEREE_NAV

  return (
    <div className="min-h-screen">
      <header className="border-b border-border-subtle bg-surface-raised">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3">
          <span className="font-semibold text-ink">{t('app.title')}</span>

          <nav className="flex flex-1 flex-wrap gap-1" aria-label={t('app.title')}>
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/admin'}
                className={({ isActive }) =>
                  cn(
                    'rounded-lg px-3 py-1.5 text-sm transition-colors',
                    isActive
                      ? 'bg-brand text-brand-ink'
                      : 'text-ink-muted hover:bg-surface hover:text-ink',
                  )
                }
              >
                {t(item.labelKey)}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-ink-muted sm:inline">{user?.email}</span>
            <Button variant="secondary" size="sm" onClick={() => void logout()}>
              {t('nav.logout')}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
