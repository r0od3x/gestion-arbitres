import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { ApiError } from '@/api/client'
import { useInviteReferee } from '@/api/referees'
import type { RefereeGrade } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field } from '@/components/ui/field'
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

const inviteSchema = z.object({
  first_name: z.string().min(1, t('invite.error.firstNameRequired')),
  last_name: z.string().min(1, t('invite.error.lastNameRequired')),
  email: z
    .string()
    .min(1, t('invite.error.emailRequired'))
    .email(t('invite.error.emailInvalid')),
  // Le format du téléphone est validé côté serveur, qui connaît la région.
  phone: z.string().optional(),
  grade: z.enum(['regional', 'national', 'continental', 'international']),
  city: z.string().optional(),
  license_number: z.string().optional(),
})

type InviteValues = z.infer<typeof inviteSchema>

interface InviteRefereeFormProps {
  onClose: () => void
}

export function InviteRefereeForm({ onClose }: InviteRefereeFormProps) {
  const invite = useInviteReferee()
  const [formError, setFormError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InviteValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { grade: 'regional' },
  })

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await invite.mutateAsync({
        ...values,
        phone: values.phone?.trim() ? values.phone.trim() : null,
        city: values.city?.trim() ? values.city.trim() : null,
        license_number: values.license_number?.trim() ? values.license_number.trim() : null,
      })
    } catch (error) {
      // Le serveur porte les messages utiles (e-mail déjà pris, téléphone invalide).
      setFormError(error instanceof ApiError ? error.detail : t('common.error'))
    }
  })

  async function copyLink(url: string) {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  if (invite.isSuccess) {
    const { invite_url, invite_expires_in_hours } = invite.data
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('invite.title')}</CardTitle>
          <CardDescription>{t('invite.success')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <code className="block overflow-x-auto rounded-lg border border-border-subtle bg-surface px-3 py-2 text-xs">
            {invite_url}
          </code>
          <p className="text-sm text-ink-muted">
            {t('invite.expires', { hours: invite_expires_in_hours })}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void copyLink(invite_url)}>
              {copied ? t('invite.copied') : t('invite.copyLink')}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                invite.reset()
                reset({ grade: 'regional' })
                setCopied(false)
              }}
            >
              {t('invite.another')}
            </Button>
            <Button variant="ghost" onClick={onClose}>
              {t('common.close')}
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('invite.title')}</CardTitle>
        <CardDescription>{t('invite.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              id="first_name"
              label={t('invite.firstName')}
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
              label={t('invite.lastName')}
              error={errors.last_name?.message}
            >
              <Input
                id="last_name"
                aria-invalid={errors.last_name !== undefined}
                {...register('last_name')}
              />
            </Field>

            <Field id="invite_email" label={t('invite.email')} error={errors.email?.message}>
              <Input
                id="invite_email"
                type="email"
                aria-invalid={errors.email !== undefined}
                {...register('email')}
              />
            </Field>

            <Field id="invite_phone" label={t('invite.phone')} error={errors.phone?.message}>
              <Input id="invite_phone" type="tel" {...register('phone')} />
              <p className="text-xs text-ink-muted">{t('invite.phoneHint')}</p>
            </Field>

            <Field id="invite_grade" label={t('invite.grade')}>
              <Select id="invite_grade" {...register('grade')}>
                {GRADES.map((grade) => (
                  <option key={grade} value={grade}>
                    {GRADE_LABELS[grade]}
                  </option>
                ))}
              </Select>
            </Field>

            <Field id="invite_city" label={t('invite.city')}>
              <Input id="invite_city" {...register('city')} />
            </Field>

            <Field id="invite_license" label={t('invite.licenseNumber')}>
              <Input id="invite_license" {...register('license_number')} />
            </Field>
          </div>

          {formError && (
            <p role="alert" className="text-sm text-danger">
              {formError}
            </p>
          )}

          <div className="flex gap-2">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? t('invite.pending') : t('invite.submit')}
            </Button>
            <Button type="button" variant="ghost" onClick={onClose}>
              {t('common.cancel')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
