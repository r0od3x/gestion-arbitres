import { Navigate, Route, Routes } from 'react-router-dom'

import { RequireAdmin, RequireAuth, RequireReferee } from '@/auth/guards'
import { useAuth } from '@/auth/useAuth'
import { AppLayout } from '@/components/AppLayout'
import { DashboardPage } from '@/pages/admin/DashboardPage'
import { RefereesPage } from '@/pages/admin/RefereesPage'
import { TournamentsPage } from '@/pages/admin/TournamentsPage'
import { AcceptInvitePage } from '@/pages/AcceptInvitePage'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ConvocationsPage } from '@/pages/referee/ConvocationsPage'
import { ProfilePage } from '@/pages/referee/ProfilePage'

/** Redirige la racine vers l'espace correspondant au rôle. */
function HomeRedirect() {
  const { isAdmin } = useAuth()
  return <Navigate to={isAdmin ? '/admin' : '/mes-convocations'} replace />
}

export function App() {
  return (
    <Routes>
      <Route path="/connexion" element={<LoginPage />} />
      <Route path="/invitation" element={<AcceptInvitePage />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomeRedirect />} />

          <Route element={<RequireAdmin />}>
            <Route path="/admin" element={<DashboardPage />} />
            <Route path="/admin/arbitres" element={<RefereesPage />} />
            <Route path="/admin/tournois" element={<TournamentsPage />} />
          </Route>

          <Route element={<RequireReferee />}>
            <Route path="/mes-convocations" element={<ConvocationsPage />} />
            <Route path="/mon-profil" element={<ProfilePage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
