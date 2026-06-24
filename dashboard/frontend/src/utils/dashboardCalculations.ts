/**
 * Pure calculation helpers for the dashboard.
 *
 * These replace the previously hardcoded "mock" values (e.g. the fake
 * [12, 19, 3, 5, 2] test-type distribution, the literal "127h" time-saved
 * card, the "8" flaky count and the "+12% from last week" trend text) with
 * values derived from the real data returned by the dashboard API.
 *
 * Keeping them pure (no React, no chart.js) makes them trivial to unit test.
 */

export interface TrendPoint {
  date: string
  total: number
  passed: number
  failed: number
}

export interface Outcomes {
  total: number
  passed: number
  failed: number
}

export type TrendDirection = 'up' | 'down' | 'neutral'

export interface WeekOverWeek {
  direction: TrendDirection
  label: string
}

/**
 * Sum pass/fail totals across a trends series.
 */
export function computeOutcomes(trends: TrendPoint[]): Outcomes {
  return trends.reduce<Outcomes>(
    (acc, t) => ({
      total: acc.total + (t.total || 0),
      passed: acc.passed + (t.passed || 0),
      failed: acc.failed + (t.failed || 0),
    }),
    { total: 0, passed: 0, failed: 0 }
  )
}

/**
 * Compare the last 7 data points against the previous 7 to derive a
 * week-over-week direction. Returns a neutral "needs more data" verdict
 * when there is not enough history.
 */
export function computeWeekOverWeek(trends: TrendPoint[]): WeekOverWeek {
  if (!trends || trends.length < 14) {
    return { direction: 'neutral', label: 'Needs more data' }
  }

  const sum = (slice: TrendPoint[]) => slice.reduce((a, t) => a + (t.total || 0), 0)
  const previous7 = sum(trends.slice(-14, -7))
  const last7 = sum(trends.slice(-7))

  if (previous7 === 0) {
    return { direction: last7 > 0 ? 'up' : 'neutral', label: 'New activity' }
  }

  const pct = ((last7 - previous7) / previous7) * 100
  const rounded = Math.round(Math.abs(pct))

  if (pct > 0) {
    return { direction: 'up', label: `+${rounded}% vs last week` }
  }
  if (pct < 0) {
    return { direction: 'down', label: `-${rounded}% vs last week` }
  }
  return { direction: 'neutral', label: '0% vs last week' }
}

/**
 * Format a duration (in seconds) as a compact, human-readable string.
 * Used for the "Total Run Time" card derived from avg_duration * executions.
 */
export function formatRunTime(totalSeconds: number): string {
  if (!totalSeconds || totalSeconds <= 0) return '0m'
  const hours = totalSeconds / 3600
  if (hours >= 1) {
    return `${hours.toFixed(1)}h`
  }
  const minutes = Math.max(1, Math.round(totalSeconds / 60))
  return `${minutes}m`
}

/**
 * Build a chart.js-compatible dataset for the execution-outcomes doughnut,
 * driven by real pass/fail counts instead of hardcoded mock numbers.
 */
export function buildOutcomeChartData(outcomes: Outcomes) {
  return {
    labels: ['Passed', 'Failed'],
    datasets: [
      {
        data: [outcomes.passed, outcomes.failed],
        backgroundColor: [
          'rgba(16, 185, 129, 0.8)', // passed - green
          'rgba(239, 68, 68, 0.8)', // failed - red
        ],
      },
    ],
  }
}
