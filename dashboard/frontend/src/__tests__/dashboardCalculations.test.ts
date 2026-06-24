import { describe, it, expect } from 'vitest'
import {
  computeOutcomes,
  computeWeekOverWeek,
  formatRunTime,
  buildOutcomeChartData,
  type TrendPoint,
} from '../utils/dashboardCalculations'

const trends: TrendPoint[] = [
  { date: '2026-06-10', total: 10, passed: 8, failed: 2 },
  { date: '2026-06-11', total: 10, passed: 9, failed: 1 },
  { date: '2026-06-12', total: 10, passed: 7, failed: 3 },
  { date: '2026-06-13', total: 10, passed: 10, failed: 0 },
  { date: '2026-06-14', total: 10, passed: 6, failed: 4 },
  { date: '2026-06-15', total: 10, passed: 9, failed: 1 },
  { date: '2026-06-16', total: 10, passed: 8, failed: 2 },
  { date: '2026-06-17', total: 10, passed: 9, failed: 1 },
  { date: '2026-06-18', total: 10, passed: 10, failed: 0 },
  { date: '2026-06-19', total: 10, passed: 7, failed: 3 },
  { date: '2026-06-20', total: 10, passed: 9, failed: 1 },
  { date: '2026-06-21', total: 10, passed: 8, failed: 2 },
  { date: '2026-06-22', total: 10, passed: 10, failed: 0 },
  { date: '2026-06-23', total: 10, passed: 9, failed: 1 },
]

describe('computeOutcomes', () => {
  it('sums passed and failed across all trend points', () => {
    const result = computeOutcomes(trends)
    // 14 points * 10 total each = 140 total
    expect(result.total).toBe(140)
    // passed sum: 8+9+7+10+6+9+8+9+10+7+9+8+10+9 = 119
    expect(result.passed).toBe(119)
    // failed sum: 140 - 119 = 21
    expect(result.failed).toBe(21)
  })

  it('returns zeros for empty trends', () => {
    expect(computeOutcomes([])).toEqual({ total: 0, passed: 0, failed: 0 })
  })
})

describe('computeWeekOverWeek', () => {
  it('compares last 7 data points against previous 7 and reports a direction', () => {
    // last7 total = 70, prev7 total = 70 -> 0% change -> neutral
    const result = computeWeekOverWeek(trends)
    expect(result.direction).toBe('neutral')
    expect(result.label).toMatch(/%/)
  })

  it('reports "up" when recent week has more executions', () => {
    const growing: TrendPoint[] = [
      ...trends.slice(0, 7).map((t) => ({ ...t, total: 5 })),
      ...trends.slice(7).map((t) => ({ ...t, total: 20 })),
    ]
    const result = computeWeekOverWeek(growing)
    expect(result.direction).toBe('up')
    expect(result.label).toContain('+')
  })

  it('reports "down" when recent week has fewer executions', () => {
    const shrinking: TrendPoint[] = [
      ...trends.slice(0, 7).map((t) => ({ ...t, total: 20 })),
      ...trends.slice(7).map((t) => ({ ...t, total: 5 })),
    ]
    const result = computeWeekOverWeek(shrinking)
    expect(result.direction).toBe('down')
    expect(result.label).toContain('-')
  })

  it('returns neutral "needs more data" when fewer than 14 data points', () => {
    const result = computeWeekOverWeek(trends.slice(0, 5))
    expect(result.direction).toBe('neutral')
    expect(result.label).toMatch(/more data/i)
  })
})

describe('formatRunTime', () => {
  it('formats hours with one decimal', () => {
    // 127 hours
    expect(formatRunTime(127 * 3600)).toBe('127.0h')
  })

  it('formats sub-hour durations as minutes', () => {
    expect(formatRunTime(45 * 60)).toBe('45m')
  })

  it('returns 0m for zero or negative input', () => {
    expect(formatRunTime(0)).toBe('0m')
    expect(formatRunTime(-5)).toBe('0m')
  })

  it('rounds minutes when below an hour', () => {
    // 90 minutes = 1.5h -> shown as hours
    expect(formatRunTime(90 * 60)).toBe('1.5h')
  })
})

describe('buildOutcomeChartData', () => {
  it('builds a chart dataset from outcomes using real counts', () => {
    const chart = buildOutcomeChartData({ total: 100, passed: 80, failed: 20 })
    expect(chart.labels).toEqual(['Passed', 'Failed'])
    expect(chart.datasets[0].data).toEqual([80, 20])
    // background colors must be two entries
    expect(chart.datasets[0].backgroundColor).toHaveLength(2)
  })

  it('still renders zeroed data rather than fake mock numbers', () => {
    const chart = buildOutcomeChartData({ total: 0, passed: 0, failed: 0 })
    expect(chart.datasets[0].data).toEqual([0, 0])
    // must never contain the old hardcoded mock numbers
    expect(chart.datasets[0].data).not.toContain(12)
    expect(chart.datasets[0].data).not.toContain(19)
  })
})
