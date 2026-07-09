import { describe, it, expect, beforeEach } from 'vitest'
import { useAIDisclosureStore, STORAGE_KEY } from './aiDisclosureStore'

describe('aiDisclosureStore', () => {
  beforeEach(() => {
    sessionStorage.clear()
    // Resetea el store a su estado inicial antes de cada test
    useAIDisclosureStore.setState({ dismissed: false })
  })

  describe('estado inicial', () => {
    it('arranca no descartado (dismissed = false)', () => {
      expect(useAIDisclosureStore.getState().dismissed).toBe(false)
    })

    it('expone una accion dismiss', () => {
      expect(typeof useAIDisclosureStore.getState().dismiss).toBe('function')
    })

    it('expone una accion reset', () => {
      expect(typeof useAIDisclosureStore.getState().reset).toBe('function')
    })
  })

  describe('dismiss()', () => {
    it('marca dismissed = true', () => {
      useAIDisclosureStore.getState().dismiss()
      expect(useAIDisclosureStore.getState().dismissed).toBe(true)
    })

    it('persiste el estado en sessionStorage (alcance por sesion)', () => {
      useAIDisclosureStore.getState().dismiss()
      const raw = sessionStorage.getItem(STORAGE_KEY)
      expect(raw).not.toBeNull()
      expect(JSON.parse(raw as string).state.dismissed).toBe(true)
    })
  })

  describe('reset()', () => {
    it('vuelve a dismissed = false', () => {
      useAIDisclosureStore.getState().dismiss()
      useAIDisclosureStore.getState().reset()
      expect(useAIDisclosureStore.getState().dismissed).toBe(false)
    })
  })

  describe('alcance de sesion (sessionStorage, NO localStorage)', () => {
    it('usa la clave de almacenamiento dedicada y session-scoped', () => {
      useAIDisclosureStore.getState().dismiss()
      // Debe existir en sessionStorage...
      expect(sessionStorage.getItem(STORAGE_KEY)).not.toBeNull()
      // ...y NO en localStorage (para reaparecer en la proxima sesion del
      // navegador). localStorage puede no estar definido en algunos entornos
      // de test; si existe, confirmamos que la clave no se filtra alli.
      if (typeof localStorage !== 'undefined') {
        expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
      }
    })
  })
})
