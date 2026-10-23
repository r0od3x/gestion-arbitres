import { describe, expect, it } from 'vitest'

import { cn, formatDate, formatDateRange } from '@/lib/utils'

describe('cn', () => {
  it('résout les classes Tailwind en conflit en gardant la dernière', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4')
  })

  it('ignore les valeurs falsy', () => {
    expect(cn('a', false, undefined, null, 'b')).toBe('a b')
  })
})

describe('formatDate', () => {
  it('formate une date ISO en français', () => {
    expect(formatDate('2026-11-12')).toBe('12 novembre 2026')
  })

  it('retourne la valeur brute si la date est illisible', () => {
    expect(formatDate('pas-une-date')).toBe('pas-une-date')
  })
})

describe('formatDateRange', () => {
  it('ne répète pas une date identique', () => {
    expect(formatDateRange('2026-11-12', '2026-11-12')).toBe('12 novembre 2026')
  })

  it('affiche les deux bornes sinon', () => {
    expect(formatDateRange('2026-11-12', '2026-11-14')).toBe(
      '12 novembre 2026 — 14 novembre 2026',
    )
  })
})
