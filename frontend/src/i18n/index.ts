import { fr, type TranslationKey } from './fr'

/** Catalogues disponibles. Ajouter une langue = ajouter une entrée ici. */
const catalogs = { fr } as const

export type Locale = keyof typeof catalogs

export const defaultLocale: Locale = 'fr'

/**
 * Traduit une clé, avec interpolation `{nom}`.
 * La clé étant typée, une clé absente est une erreur de compilation.
 */
export function translate(
  key: TranslationKey,
  values?: Record<string, string | number>,
  locale: Locale = defaultLocale,
): string {
  const template: string = catalogs[locale][key]
  if (!values) return template
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in values ? String(values[name]) : match,
  )
}

export const t = translate
export type { TranslationKey }
