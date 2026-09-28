import { setupServer } from 'msw/node'

// Servidor MSW compartido por todos los tests. El ciclo de vida global
// (listen/reset/close) vive en setup.ts; cada test añade handlers por caso
// con server.use(http.get(...), ...). Sin handlers base: cualquier peticion
// no mockueada pasa through (warn), igual que sin MSW.
export const server = setupServer()
