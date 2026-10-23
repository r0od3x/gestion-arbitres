import { describe, expect, it } from 'vitest'

import { fr } from '@/i18n/fr'
import { t } from '@/i18n'

describe('traduction', () => {
  it('retourne la chaîne française', () => {
    expect(t('login.submit')).toBe('Se connecter')
  })

  it('interpole les variables', () => {
    expect(t('app.title')).toBe('Gestion des Arbitres')
  })

  it("n'a aucune valeur vide", () => {
    for (const [key, value] of Object.entries(fr)) {
      expect(value.trim(), `la clé ${key} est vide`).not.toBe('')
    }
  })
})
