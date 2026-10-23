import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { z } from 'zod'

import { ApiError, api, setAccessToken } from '@/api/client'
import type { TokenResponse } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { t } from '@/i18n'

const acceptSchema = z
  .object({
    // Doit rester aligné sur la contrainte du backend (10 caractères).
    password: z.string().min(10, t('acceptInvite.error.tooShort')),
    confirm: z.string(),
  })
  .refine((values) => values.password === values.confirm, {
    message: t('acceptInvite.error.mismatch'),
    path: ['confirm'],
  })

type AcceptValues = z.infer<typeof acceptSchema>

export function AcceptInvitePage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AcceptValues>({ resolver: zodResolver(acceptSchema) })

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      const tokens = await api.post<TokenResponse>('/auth/accept-invite', {
        token,
        password: values.password,
      })
      // Le compte est actif : on enchaîne directement sur l'espace arbitre.
      setAccessToken(tokens.access_token)
      navigate('/mon-profil', { replace: true })
    } catch (error) {
      setFormError(error instanceof ApiError ? error.detail : t('common.error'))
    }
  })

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{t('acceptInvite.title')}</CardTitle>
          <CardDescription>{t('acceptInvite.subtitle')}</CardDescription>
        </CardHeader>
        <CardContent>
          {token === null ? (
            <p role="alert" className="text-sm text-danger">
              {t('acceptInvite.missingToken')}
            </p>
          ) : (
            <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
              <Field
                id="password"
                label={t('acceptInvite.password')}
                error={errors.password?.message}
              >
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  aria-invalid={errors.password !== undefined}
                  {...register('password')}
                />
              </Field>

              <Field
                id="confirm"
                label={t('acceptInvite.confirm')}
                error={errors.confirm?.message}
              >
                <Input
                  id="confirm"
                  type="password"
                  autoComplete="new-password"
                  aria-invalid={errors.confirm !== undefined}
                  {...register('confirm')}
                />
              </Field>

              {formError && (
                <p role="alert" className="text-sm text-danger">
                  {formError}
                </p>
              )}

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? t('acceptInvite.pending') : t('acceptInvite.submit')}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
