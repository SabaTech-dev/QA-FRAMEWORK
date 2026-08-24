import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

/**
 * Almacenamiento de la divulgacion de IA (EU AI Act, Articulo 50(1)).
 *
 * El estado de "descartado" se persiste en `sessionStorage` (NO en localStorage)
 * a proposito: asi el aviso reaparece en cada nueva sesion del navegador,
 * garantizando que el usuario vuelva a ser informado de que interactua con un
 * sistema de IA cada vez que abre el dashboard.
 */
export const STORAGE_KEY = 'ai-disclosure-storage'

interface AIDisclosureState {
  /** True cuando el usuario ha cerrado el aviso en la sesion actual. */
  dismissed: boolean
  /** Oculta el aviso para la sesion en curso. */
  dismiss: () => void
  /** Vuelve a mostrar el aviso (util para tests y re-divulgacion). */
  reset: () => void
}

const useAIDisclosureStore = create<AIDisclosureState>()(
  persist(
    (set) => ({
      dismissed: false,
      dismiss: () => set({ dismissed: true }),
      reset: () => set({ dismissed: false }),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => sessionStorage),
    }
  )
)

export { useAIDisclosureStore }
export default useAIDisclosureStore
