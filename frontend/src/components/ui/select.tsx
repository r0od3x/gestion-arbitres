import { forwardRef, type SelectHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement>

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, ...props },
  ref,
) {
  return (
    <select
      ref={ref}
      className={cn(
        'h-10 w-full rounded-lg border border-border-subtle bg-surface-raised px-3 text-sm',
        'text-ink focus-visible:outline-2 focus-visible:outline-offset-1',
        'focus-visible:outline-brand disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
})
