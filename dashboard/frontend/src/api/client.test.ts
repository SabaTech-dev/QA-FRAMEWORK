// @vitest-environment node
//
// jsdom 29 define window.location como propiedad propia no configurable:
// no se puede stubbar el redirect alli. Este archivo corre en entorno node
// con un window stubbeado (location observable), lo que permite assertar
// window.location.href === '/login' con precision. client.ts solo toca
// window.location dentro del handler 401, por lo que el orden
// import-then-stub es seguro: el stub existe antes de cualquier peticion.
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import useAuthStore from '../stores/authStore'
import apiClient, { authAPI } from './client'

const INITIAL_HREF = 'http://localhost:3000/dashboard'

vi.stubGlobal('window', { location: { href: INITIAL_HREF } })

// El adaptador http de axios (node) requiere URL absoluta; capturamos el
// baseURL relativo de fabrica antes de sobreescribirlo para los smoke.
const DEFAULT_BASE_URL = apiClient.defaults.baseURL
const API_ORIGIN = 'http://localhost:8000'
apiClient.defaults.baseURL = `${API_ORIGIN}/api/v1`

// Duplicado deliberado del contrato de client.ts (AUTH_FLOW_PATHS): si la
// lista cambia en el codigo, estos tests deben fallar y forzar revision.
const AUTH_FLOW_PATHS = [
  '/auth/login',
  '/auth/register',
  '/auth/change-password',
  '/auth/forgot-password',
  '/auth/reset-password',
  '/auth/verify-email',
]

const fakeUser = {
  id: 1,
  username: 'tester',
  email: 'tester@example.com',
  is_active: true,
  is_superuser: false,
}

function login() {
  useAuthStore.getState().login('token-123', fakeUser)
}

beforeEach(() => {
  useAuthStore.setState({
    token: null,
    user: null,
    isAuthenticated: false,
    needsOnboarding: false,
  })
  window.location.href = INITIAL_HREF
})

describe('client.ts smoke', () => {
  it('expone apiClient con baseURL relativo por defecto /api/v1', () => {
    expect(DEFAULT_BASE_URL).toBe('/api/v1')
  })

  it('roundtrip exitoso contra MSW', async () => {
    server.use(
      http.get(`${API_ORIGIN}/api/v1/suites`, () =>
        HttpResponse.json({ items: [{ id: 1 }] })
      )
    )
    const res = await apiClient.get('/suites')
    expect(res.status).toBe(200)
    expect(res.data).toEqual({ items: [{ id: 1 }] })
  })

  it('adjunta Bearer token del authStore en cada peticion', async () => {
    login()
    server.use(
      http.get(`${API_ORIGIN}/api/v1/me`, ({ request }) =>
        HttpResponse.json({
          authorization: request.headers.get('authorization'),
        })
      )
    )
    const { data } = await apiClient.get('/me')
    expect(data.authorization).toBe('Bearer token-123')
  })

  it('sin token en el store no envia cabecera Authorization', async () => {
    server.use(
      http.get(`${API_ORIGIN}/api/v1/me`, ({ request }) =>
        HttpResponse.json({
          authorization: request.headers.get('authorization'),
        })
      )
    )
    const { data } = await apiClient.get('/me')
    expect(data.authorization).toBeNull()
  })
})

describe('interceptor 401 — endpoint regular', () => {
  it('401 expira la sesion: logout + redirect a /login', async () => {
    login()
    server.use(
      http.get(`${API_ORIGIN}/api/v1/suites`, () =>
        HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 })
      )
    )

    await expect(apiClient.get('/suites')).rejects.toMatchObject({
      response: { status: 401 },
    })

    const state = useAuthStore.getState()
    expect(state.token).toBeNull()
    expect(state.user).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(window.location.href).toBe('/login')
  })

  it('otros errores (500) NO disparan logout ni redirect', async () => {
    login()
    server.use(
      http.get(`${API_ORIGIN}/api/v1/suites`, () =>
        HttpResponse.json({ detail: 'boom' }, { status: 500 })
      )
    )

    await expect(apiClient.get('/suites')).rejects.toMatchObject({
      response: { status: 500 },
    })

    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    expect(window.location.href).toBe(INITIAL_HREF)
  })
})

describe('interceptor 401 — AUTH_FLOW_PATHS (sin logout, error inline)', () => {
  it.each(AUTH_FLOW_PATHS)('401 en %s NO hace logout ni redirect', async (path) => {
    login()
    server.use(
      http.post(`${API_ORIGIN}/api/v1${path}`, () =>
        HttpResponse.json({ detail: 'auth flow error' }, { status: 401 })
      )
    )

    // El error se propaga al caller (render inline), con payload visible
    await expect(apiClient.post(path, {})).rejects.toMatchObject({
      response: { status: 401, data: { detail: 'auth flow error' } },
    })

    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(true)
    expect(state.token).toBe('token-123')
    expect(window.location.href).toBe(INITIAL_HREF)
  })

  it('B1 (card 4920f947): changePassword con current-password erroneo NO expulsa la sesion', async () => {
    login()
    server.use(
      http.post(`${API_ORIGIN}/api/v1/auth/change-password`, () =>
        HttpResponse.json({ detail: 'Current password is incorrect' }, { status: 401 })
      )
    )

    await expect(
      authAPI.changePassword('wrong-current', 'NewPass123!')
    ).rejects.toMatchObject({
      response: {
        status: 401,
        data: { detail: 'Current password is incorrect' },
      },
    })

    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    expect(window.location.href).toBe(INITIAL_HREF)
  })

  it('authAPI.login con credenciales invalidas rechaza 401 sin redirect', async () => {
    server.use(
      http.post(`${API_ORIGIN}/api/v1/auth/login`, () =>
        HttpResponse.json({ detail: 'Incorrect username or password' }, { status: 401 })
      )
    )

    await expect(authAPI.login('user', 'wrong-pass')).rejects.toMatchObject({
      response: {
        status: 401,
        data: { detail: 'Incorrect username or password' },
      },
    })

    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(window.location.href).toBe(INITIAL_HREF)
  })
})
