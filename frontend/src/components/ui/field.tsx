import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface FieldProps {
  id: string
  label: string
  error?: string
  children: ReactNode
  className?: string
}

/** Libellé + contrôle + message d'erreur, reliés pour les lecteurs d'écran. */
export function Field({ id, label, error, children, className }: FieldProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  )
}
