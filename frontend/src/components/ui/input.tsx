import { forwardRef, type InputHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

export type InputProps = InputHTMLAttributes<HTMLInputElement>

/**
 * `forwardRef` est indispensable : react-hook-form enregistre le champ via sa
 * ref. Sans elle, le formulaire ne voit jamais les valeurs saisies.
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        'h-10 w-full rounded-lg border border-border-subtle bg-surface-raised px-3 text-sm',
        'text-ink placeholder:text-ink-muted',
        'focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand',
        'aria-[invalid=true]:border-danger disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
})
