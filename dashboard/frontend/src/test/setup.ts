import '@testing-library/jest-dom/vitest'
import { afterEach, afterAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import { server } from './server'

// MSW: intercepta HTTP/XHR/fetch en todos los tests. Las peticiones sin
// handler pasan through (warn), asi los tests existentes no cambian.
server.listen({ onUnhandledRequest: 'warn' })

// Limpia el DOM entre tests de componentes React
afterEach(() => {
  // Env-agnostico: los tests con @vitest-environment node no tienen DOM
  if (typeof document !== 'undefined') cleanup()
  // Resetea sessionStorage para aislar el estado por sesión de cada test
  globalThis.sessionStorage?.clear()
  server.resetHandlers()
})

afterAll(() => {
  server.close()
})
