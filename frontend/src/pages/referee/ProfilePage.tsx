import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { ApiError } from '@/api/client'
import { useMyProfile, useUpdateMyProfile } from '@/api/referees'
import type { RefereeGrade } from '@/api/types'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { t } from '@/i18n'

const GRADE_LABELS: Record<RefereeGrade, string> = {
  regional: t('grade.regional'),
  national: t('grade.national'),
  continental: t('grade.continental'),
  international: t('grade.international'),
}

const profileSchema = z.object({
  first_name: z.string().min(1, t('profile.error.firstNameRequired')),
  last_name: z.string().min(1, t('profile.error.lastNameRequired')),
  phone: z.string().optional(),
  city: z.string().optional(),
  club: z.string().optional(),
  league: z.string().optional(),
  whatsapp_opt_in: z.boolean(),
})

type ProfileValues = z.infer<typeof profileSchema>

export function ProfilePage() {
  const { data: profile, isPending, isError } = useMyProfile()
  const update = useUpdateMyProfile()
  const [formError, setFormError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProfileValues>({ resolver: zodResolver(profileSchema) })

  // Le formulaire est rempli dès que le profil arrive du serveur.
  useEffect(() => {
    if (!profile) return
    reset({
      first_name: profile.first_name,
      last_name: profile.last_name,
      phone: profile.phone_e164 ?? '',
      city: profile.city ?? '',
      club: profile.club ?? '',
      league: profile.league ?? '',
      whatsapp_opt_in: profile.whatsapp_opt_in,
    })
  }, [profile, reset])

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    setSaved(false)
    try {
      await update.mutateAsync({
        ...values,
        phone: values.phone?.trim() ? values.phone.trim() : null,
        city: values.city?.trim() ? values.city.trim() : null,
        club: values.club?.trim() ? values.club.trim() : null,
        league: values.league?.trim() ? values.league.trim() : null,
      })
      setSaved(true)
    } catch (error) {
      setFormError(error instanceof ApiError ? error.detail : t('common.error'))
    }
  })

  if (isPending) {
    return (
      <>
        <PageHeader title={t('profile.title')} />
        <p className="text-sm text-ink-muted">{t('common.loading')}</p>
      </>
    )
  }

  if (isError || !profile) {
    return (
      <>
        <PageHeader title={t('profile.title')} />
        <p role="alert" className="text-sm text-danger">
          {t('common.error')}
        </p>
      </>
    )
  }

  return (
    <>
      <PageHeader title={t('profile.title')} />

      <form onSubmit={(event) => void onSubmit(event)} className="space-y-6" noValidate>
        <Card>
          <CardHeader>
            <CardTitle>{t('profile.identity')}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field
              id="first_name"
              label={t('profile.firstName')}
              error={errors.first_name?.message}
            >
              <Input
                id="first_name"
                aria-invalid={errors.first_name !== undefined}
                {...register('first_name')}
              />
            </Field>

            <Field
              id="last_name"
              label={t('profile.lastName')}
              error={errors.last_name?.message}
            >
              <Input
                id="last_name"
                aria-invalid={errors.last_name !== undefined}
                {...register('last_name')}
              />
            </Field>

            {/* Gérés par un administrateur : affichés, non modifiables. */}
            <div>
              <p className="text-sm font-medium text-ink">{t('profile.grade')}</p>
              <p className="text-ink-muted">{GRADE_LABELS[profile.grade]}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-ink">{t('profile.licenseNumber')}</p>
              <p className="text-ink-muted">
                {profile.license_number ?? t('common.notProvided')}
              </p>
            </div>
            <p className="text-xs text-ink-muted sm:col-span-2">{t('profile.readOnlyHint')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('profile.contact')}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field id="phone" label={t('profile.phone')} error={errors.phone?.message}>
              <Input id="phone" type="tel" {...register('phone')} />
            </Field>

            <Field id="city" label={t('profile.city')}>
              <Input id="city" {...register('city')} />
            </Field>

            <Field id="club" label={t('profile.club')}>
              <Input id="club" {...register('club')} />
            </Field>

            <Field id="league" label={t('profile.league')}>
              <Input id="league" {...register('league')} />
            </Field>

            <div className="sm:col-span-2">
              <label className="flex items-start gap-2 text-sm text-ink">
                <Checkbox className="mt-0.5" {...register('whatsapp_opt_in')} />
                <span>
                  {t('profile.whatsappOptIn')}
                  <span className="mt-0.5 block text-xs text-ink-muted">
                    {t('profile.whatsappHint')}
                  </span>
                </span>
              </label>
            </div>
          </CardContent>
        </Card>

        {formError && (
          <p role="alert" className="text-sm text-danger">
            {formError}
          </p>
        )}
        {saved && (
          <p role="status" className="text-sm text-success">
            {t('profile.saved')}
          </p>
        )}

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? t('profile.saving') : t('common.save')}
        </Button>
      </form>
    </>
  )
}
