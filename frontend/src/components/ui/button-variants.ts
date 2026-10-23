import { cva } from 'class-variance-authority'

/**
 * Séparé du composant : un fichier qui n'exporte pas que des composants
 * casse le rafraîchissement à chaud de Vite.
 */
export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium ' +
    'transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 ' +
    'focus-visible:outline-brand disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-brand text-brand-ink hover:opacity-90',
        secondary: 'bg-surface-raised text-ink border border-border-subtle hover:bg-surface',
        ghost: 'text-ink hover:bg-surface-raised',
        danger: 'bg-danger text-white hover:opacity-90',
      },
      size: {
        sm: 'h-8 px-3',
        md: 'h-10 px-4',
        lg: 'h-11 px-6 text-base',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
)
