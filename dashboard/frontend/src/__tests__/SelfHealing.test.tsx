import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import fs from 'fs'
import path from 'path'

// Mock the API client so we never hit the network. The component must talk to
// healingAPI, not to hardcoded mock data.
vi.mock('../api/client', () => ({
  healingAPI: {
    getSelectors: vi.fn(),
    getSessions: vi.fn(),
    getSession: vi.fn(),
    healSelector: vi.fn(),
    deleteSelector: vi.fn(),
    createSelector: vi.fn(),
    updateSelector: vi.fn(),
    getResults: vi.fn(),
  },
}))

import SelfHealingDashboard from '../pages/SelfHealing'
import { healingAPI } from '../api/client'

// Typed accessors to the mocked functions.
const mockGetSelectors = healingAPI.getSelectors as unknown as ReturnType<typeof vi.fn>
const mockGetSessions = healingAPI.getSessions as unknown as ReturnType<typeof vi.fn>
const mockHealSelector = healingAPI.healSelector as unknown as ReturnType<typeof vi.fn>
const mockDeleteSelector = healingAPI.deleteSelector as unknown as ReturnType<typeof vi.fn>

// ---- Fixtures: realistic API-shaped payloads (NOT mock page data) ----
function selectorFixture(overrides: Partial<{
  id: number
  value: string
  selector_type: string
  confidence_score: number
  confidence_level: string
  is_active: boolean
  usage_count: number
  success_rate: number
}> = {}) {
  return {
    id: 1,
    value: "[data-testid='from-real-api']",
    selector_type: 'css',
    description: null,
    confidence_score: 0.4,
    confidence_level: 'low',
    is_active: true,
    usage_count: 5,
    success_rate: 0.5,
    ...overrides,
  }
}

function sessionFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: 11,
    status: 'success',
    total_selectors: 1,
    successful_heals: 1,
    failed_heals: 0,
    success_rate: 1.0,
    average_confidence: 0.8,
    started_at: '2026-06-27T10:00:00Z',
    completed_at: '2026-06-27T10:00:05Z',
    ...overrides,
  }
}

function healResultFixture() {
  return {
    id: 99,
    session_id: 11,
    selector_id: 1,
    original_selector_value: "[data-testid='from-real-api']",
    healed_selector_value: "[data-testid='from_real_api']",
    status: 'success',
    confidence_score: 0.8,
    confidence_level: 'high',
    healing_time_ms: 12,
    attempts: 3,
    created_at: '2026-06-27T10:00:05Z',
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('SelfHealingDashboard — API integration (no mock data)', () => {
  it('fetches and renders selectors from healingAPI on mount', async () => {
    mockGetSelectors.mockResolvedValue({ data: [selectorFixture()] })
    mockGetSessions.mockResolvedValue({ data: [] })

    render(<SelfHealingDashboard />)

    // The fixture value must appear. If the component used mock data, this
    // exact string (from the API) would never render.
    await screen.findByText("[data-testid='from-real-api']")
    expect(mockGetSelectors).toHaveBeenCalledTimes(1)
    expect(mockGetSessions).toHaveBeenCalledTimes(1)
  })

  it('shows the empty state when the API returns no selectors', async () => {
    mockGetSelectors.mockResolvedValue({ data: [] })
    mockGetSessions.mockResolvedValue({ data: [] })

    render(<SelfHealingDashboard />)

    await screen.findByText('No Selectors Found')
    expect(mockGetSelectors).toHaveBeenCalledTimes(1)
  })

  it('shows an error state with retry when the fetch rejects', async () => {
    mockGetSelectors.mockRejectedValue(new Error('network down'))
    mockGetSessions.mockResolvedValue({ data: [] })

    render(<SelfHealingDashboard />)

    await screen.findByText(/failed to load self-healing data/i)
    expect(screen.getByRole('button', { name: /retry/i })).toBeTruthy()
  })

  it('renders healing sessions from the API', async () => {
    mockGetSelectors.mockResolvedValue({ data: [selectorFixture()] })
    mockGetSessions.mockResolvedValue({ data: [sessionFixture()] })

    render(<SelfHealingDashboard />)

    // Session id is rendered as monospace text.
    await screen.findByText('11')
  })

  it('calls healSelector and shows the result when the heal button is clicked', async () => {
    const user = userEvent.setup()
    mockGetSelectors.mockResolvedValue({ data: [selectorFixture()] })
    mockGetSessions.mockResolvedValue({ data: [] })
    mockHealSelector.mockResolvedValue({ data: healResultFixture() })

    render(<SelfHealingDashboard />)
    await screen.findByText("[data-testid='from-real-api']")

    await user.click(screen.getByRole('button', { name: /heal selector/i }))

    await waitFor(() => {
      expect(mockHealSelector).toHaveBeenCalledWith(1)
    })
    // Healed selector value from the API response is shown.
    await screen.findByText('Healing completed successfully')
  })

  it('calls deleteSelector when the delete button is clicked', async () => {
    const user = userEvent.setup()
    mockGetSelectors.mockResolvedValue({ data: [selectorFixture()] })
    mockGetSessions.mockResolvedValue({ data: [] })
    mockDeleteSelector.mockResolvedValue({ data: null })

    render(<SelfHealingDashboard />)
    await screen.findByText("[data-testid='from-real-api']")

    await user.click(screen.getByRole('button', { name: /delete selector/i }))

    await waitFor(() => {
      expect(mockDeleteSelector).toHaveBeenCalledWith(1)
    })
  })
})

// Guards against regression: the page must never ship hardcoded mock data.
describe('SelfHealingDashboard — no hardcoded mock data (source guard)', () => {
  const source = fs.readFileSync(
    path.resolve(__dirname, '../pages/SelfHealing.tsx'),
    'utf8',
  )

  it('does not contain the old mock selector/session arrays', () => {
    expect(source).not.toMatch(/mockSelectors/)
    expect(source).not.toMatch(/mockSessions/)
    expect(source).not.toMatch(/mockResult/)
  })

  it('does not contain the "For now, using mock data" comment', () => {
    expect(source).not.toMatch(/For now, using mock data/i)
  })

  it('does not simulate healing with setTimeout', () => {
    // The old mock simulated healing with a fixed setTimeout; the real
    // implementation awaits healingAPI.healSelector instead.
    expect(source).not.toMatch(/setTimeout/)
  })

  it('imports and uses healingAPI', () => {
    expect(source).toMatch(/import.*healingAPI.*from.*'\.\.\/api\/client'/)
    expect(source).toMatch(/healingAPI\./)
  })
})
