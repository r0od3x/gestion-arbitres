import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { ApiError } from '@/api/client'
import { useCreateTournament } from '@/api/tournaments'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { t } from '@/i18n'

const tournamentSchema = z
  .object({
    title: z.string().min(1, t('tournamentForm.error.titleRequired')),
    city: z.string().min(1, t('tournamentForm.error.cityRequired')),
    venue: z.string().optional(),
    start_date: z.string().min(1, t('tournamentForm.error.startRequired')),
    end_date: z.string().min(1, t('tournamentForm.error.endRequired')),
    convocation_time: z.string().optional(),
    referees_needed: z.string().optional(),
    description: z.string().optional(),
  })
  .refine((values) => values.end_date >= values.start_date, {
    // Les dates ISO se comparent correctement en ordre lexicographique.
    message: t('tournamentForm.error.endBeforeStart'),
    path: ['end_date'],
  })

type TournamentValues = z.infer<typeof tournamentSchema>

export function TournamentForm({ onClose }: { onClose: () => void }) {
  const create = useCreateTournament()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<TournamentValues>({ resolver: zodResolver(tournamentSchema) })

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await create.mutateAsync({
        title: values.title,
        city: values.city,
        venue: values.venue?.trim() ? values.venue.trim() : null,
        start_date: values.start_date,
        end_date: values.end_date,
        // Le backend attend HH:MM:SS.
        convocation_time: values.convocation_time ? `${values.convocation_time}:00` : null,
        referees_needed: values.referees_needed ? Number(values.referees_needed) : null,
        description: values.description?.trim() ? values.description.trim() : null,
      })
      onClose()
    } catch (error) {
      setFormError(error instanceof ApiError ? error.detail : t('common.error'))
    }
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('tournamentForm.title')}</CardTitle>
        <CardDescription>{t('tournamentForm.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              id="title"
              label={t('tournamentForm.name')}
              error={errors.title?.message}
              className="sm:col-span-2"
            >
              <Input
                id="title"
                aria-invalid={errors.title !== undefined}
                {...register('title')}
              />
            </Field>

            <Field id="city" label={t('tournamentForm.city')} error={errors.city?.message}>
              <Input id="city" aria-invalid={errors.city !== undefined} {...register('city')} />
            </Field>

            <Field id="venue" label={t('tournamentForm.venue')}>
              <Input id="venue" {...register('venue')} />
            </Field>

            <Field
              id="start_date"
              label={t('tournamentForm.startDate')}
              error={errors.start_date?.message}
            >
              <Input
                id="start_date"
                type="date"
                aria-invalid={errors.start_date !== undefined}
                {...register('start_date')}
              />
            </Field>

            <Field
              id="end_date"
              label={t('tournamentForm.endDate')}
              error={errors.end_date?.message}
            >
              <Input
                id="end_date"
                type="date"
                aria-invalid={errors.end_date !== undefined}
                {...register('end_date')}
              />
            </Field>

            <Field id="convocation_time" label={t('tournamentForm.convocationTime')}>
              <Input id="convocation_time" type="time" {...register('convocation_time')} />
            </Field>

            <Field id="referees_needed" label={t('tournamentForm.refereesNeeded')}>
              <Input
                id="referees_needed"
                type="number"
                min={1}
                {...register('referees_needed')}
              />
            </Field>

            <Field
              id="description"
              label={t('tournamentForm.descriptionField')}
              className="sm:col-span-2"
            >
              <Input id="description" {...register('description')} />
            </Field>
          </div>

          {formError && (
            <p role="alert" className="text-sm text-danger">
              {formError}
            </p>
          )}

          <div className="flex gap-2">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? t('tournamentForm.pending') : t('tournamentForm.submit')}
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
