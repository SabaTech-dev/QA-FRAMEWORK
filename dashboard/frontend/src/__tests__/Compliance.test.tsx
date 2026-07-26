import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Compliance from '../pages/Compliance'

/**
 * Smoke + behaviour tests for the Compliance Center page.
 *
 * The page is the single entry point (reachable from the sidebar's
 * "Compliance" item) to all EU AI Act / CRA compliance documentation.
 * One of those documents is the QA-FRAMEWORK-scoped GPAI Inventory
 * (docs/compliance/GPAI-Inventory.md), which supersedes the legacy
 * AI_SYSTEMS_INVENTORY.md.
 */
describe('Compliance page', () => {
  it('renders without crashing', () => {
    const { container } = render(<Compliance />)
    expect(container).toBeTruthy()
  })

  it('exposes a link to the QA-FRAMEWORK GPAI Inventory document', () => {
    render(<Compliance />)

    const gpaiLink = screen
      .getAllByRole('link')
      .find((link) => (link.getAttribute('href') || '').endsWith('docs/compliance/GPAI-Inventory.md'))

    expect(gpaiLink).toBeDefined()
    expect(gpaiLink?.textContent ?? '').toMatch(/GPAI Inventory/i)
  })

  it('does not advertise the superseded AI_SYSTEMS_INVENTORY.md as the QA-FRAMEWORK inventory', () => {
    render(<Compliance />)

    const legacyLinks = screen
      .getAllByRole('link')
      .filter((link) => (link.getAttribute('href') || '').includes('AI_SYSTEMS_INVENTORY.md'))

    expect(legacyLinks).toHaveLength(0)
  })
})
