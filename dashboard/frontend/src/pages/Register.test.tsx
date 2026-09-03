import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import Register from './Register'

// Register usa useNavigate/Link (Router) y useMutation (QueryClient),
// por eso hay que envolverlo antes de renderizar.
function renderRegister() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// React 18 emite los propTypes warnings estilo printf:
// console.error('Warning: Failed %s type: %s%s', 'prop', 'Invalid prop `error` ...', stack)
// El texto util esta repartido entre argumentos, por eso se inspeccionan todos.
// Nota: React deduplica estos warnings por componente dentro del proceso, asi que
// este test DEBE renderizar Register antes que los demas (orden del describe).
function hasPropTypesErrorWarning(spy: ReturnType<typeof vi.spyOn>): boolean {
  return spy.mock.calls.some((call) =>
    call.some((arg) => String(arg).includes('Invalid prop `error`'))
  )
}

describe('Register - prop error de TextField/FormControl (card 9151895a)', () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    // MUI valida propTypes cuando NODE_ENV !== production: los warnings de
    // React llegan via console.error, asi que espiamos ahi.
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleErrorSpy.mockRestore()
  })

  it('con confirmPassword vacio no emite propTypes warning por error:string', () => {
    renderRegister()

    expect(hasPropTypesErrorWarning(consoleErrorSpy)).toBe(false)
  })

  it('muestra helper de mismatch cuando password y confirm no coinciden', async () => {
    const user = userEvent.setup()
    renderRegister()

    await user.type(screen.getByLabelText('Username'), 'joker')
    await user.type(screen.getByLabelText('Email'), 'joker@test.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.type(screen.getByLabelText('Confirm Password'), 'password999')

    expect(await screen.findByText('Passwords do not match')).toBeInTheDocument()
  })

  it('no muestra helper de error cuando las passwords coinciden', async () => {
    const user = userEvent.setup()
    renderRegister()

    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.type(screen.getByLabelText('Confirm Password'), 'password123')

    expect(
      screen.queryByText('Passwords do not match')
    ).not.toBeInTheDocument()
  })
})
