import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Limpia el DOM entre tests de componentes React
afterEach(() => {
  cleanup()
  // Resetea sessionStorage para aislar el estado por sesión de cada test
  sessionStorage.clear()
})
