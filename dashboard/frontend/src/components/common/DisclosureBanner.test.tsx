import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DisclosureBanner, {
  DEFAULT_AI_DISCLOSURE_MESSAGE,
} from './DisclosureBanner'
import { useAIDisclosureStore } from '../../stores/aiDisclosureStore'

describe('DisclosureBanner', () => {
  beforeEach(() => {
    sessionStorage.clear()
    useAIDisclosureStore.setState({ dismissed: false })
  })

  describe('divulgacion obligatoria (Art. 50(1) EU AI Act)', () => {
    it('renderiza el mensaje de divulgacion exigido por defecto', () => {
      render(<DisclosureBanner />)
      expect(
        screen.getByText(DEFAULT_AI_DISCLOSURE_MESSAGE)
      ).toBeInTheDocument()
    })

    it('el texto por defecto menciona explicitamente IA y revision humana', () => {
      expect(DEFAULT_AI_DISCLOSURE_MESSAGE).toMatch(/AI-powered/i)
      expect(DEFAULT_AI_DISCLOSURE_MESSAGE).toMatch(/reviewed by qualified personnel/i)
    })

    it('es visible para el usuario (no oculto por defecto)', () => {
      render(<DisclosureBanner />)
      const banner = screen.getByText(DEFAULT_AI_DISCLOSURE_MESSAGE)
      expect(banner).toBeVisible()
    })

    it('permite personalizar el mensaje via prop', () => {
      const custom = 'Sistema con IA: verifica los resultados.'
      render(<DisclosureBanner message={custom} />)
      expect(screen.getByText(custom)).toBeInTheDocument()
    })
  })

  describe('descartable por sesion', () => {
    it('oculta el banner al pulsar el boton de cerrar', async () => {
      const user = userEvent.setup()
      render(<DisclosureBanner />)
      expect(
        screen.getByText(DEFAULT_AI_DISCLOSURE_MESSAGE)
      ).toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: /dismiss/i }))

      expect(
        screen.queryByText(DEFAULT_AI_DISCLOSURE_MESSAGE)
      ).not.toBeInTheDocument()
    })

    it('marca el store como descartado al cerrar', async () => {
      const user = userEvent.setup()
      render(<DisclosureBanner />)
      await user.click(screen.getByRole('button', { name: /dismiss/i }))
      expect(useAIDisclosureStore.getState().dismissed).toBe(true)
    })

    it('no renderiza nada si ya estaba descartado', () => {
      useAIDisclosureStore.setState({ dismissed: true })
      const { container } = render(<DisclosureBanner />)
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('accesibilidad', () => {
    it('expone un rol semantico de alerta informativa (role=status)', () => {
      render(<DisclosureBanner />)
      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('el boton de cerrar tiene una etiqueta accesible', () => {
      render(<DisclosureBanner />)
      expect(
        screen.getByRole('button', { name: /dismiss/i })
      ).toBeInTheDocument()
    })
  })

  describe('no bloqueante', () => {
    it('no impide renderizar contenido hermano', () => {
      const { container } = render(
        <div>
          <DisclosureBanner />
          <p>contenido-debajo</p>
        </div>
      )
      expect(screen.getByText('contenido-debajo')).toBeInTheDocument()
      // Sanity: el banner y el contenido coexisten sin solaparse en el arbol
      expect(container).toContainHTML('contenido-debajo')
    })
  })
})
