import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { ApiError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { t } from '@/i18n'

const loginSchema = z.object({
  email: z.string().min(1, t('login.error.emailRequired')).email(t('login.error.emailInvalid')),
  password: z.string().min(1, t('login.error.passwordRequired')),
})

type LoginValues = z.infer<typeof loginSchema>

export function LoginPage() {
  const { login, isAuthenticated, isAdmin, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) })

  if (!isLoading && isAuthenticated) {
    const from = (location.state as { from?: Location } | null)?.from?.pathname
    return <Navigate to={from ?? (isAdmin ? '/admin' : '/mes-convocations')} replace />
  }

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      const user = await login(values.email, values.password)
      navigate(user.role === 'admin' ? '/admin' : '/mes-convocations', { replace: true })
    } catch (error) {
      // 401 = identifiants ; tout le reste est une panne, à ne pas confondre.
      setFormError(
        error instanceof ApiError && error.isAuthError
          ? t('login.error.credentials')
          : t('login.error.generic'),
      )
    }
  })

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{t('login.title')}</CardTitle>
          <CardDescription>{t('login.subtitle')}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
            <Field id="email" label={t('login.email')} error={errors.email?.message}>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                aria-invalid={errors.email !== undefined}
                {...register('email')}
              />
            </Field>

            <Field id="password" label={t('login.password')} error={errors.password?.message}>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                aria-invalid={errors.password !== undefined}
                {...register('password')}
              />
            </Field>

            {formError && (
              <p role="alert" className="text-sm text-danger">
                {formError}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? t('login.pending') : t('login.submit')}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
