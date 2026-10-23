import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

type Tone = 'neutral' | 'success' | 'warning' | 'danger'

const TONES: Record<Tone, string> = {
  neutral: 'bg-surface text-ink-muted border-border-subtle',
  success: 'bg-success/12 text-success border-success/30',
  warning: 'bg-warning/15 text-warning border-warning/35',
  danger: 'bg-danger/12 text-danger border-danger/30',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone
}

export function Badge({ className, tone = 'neutral', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium',
        TONES[tone],
        className,
      )}
      {...props}
    />
  )
}
