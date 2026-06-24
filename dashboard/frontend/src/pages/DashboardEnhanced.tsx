import { useQuery, useQueryClient } from 'react-query'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  CircularProgress,
  Button,
  Fade,
  Breadcrumbs,
  Link,
} from '@mui/material'
import {
  TrendingUp,
  TrendingDown,
  Folder,
  PlayArrow,
  CheckCircle,
  Schedule,
  AutoFixHigh,
  Warning,
  Add,
  PlayCircle,
  Assessment,
  Refresh,
  FiberManualRecord,
} from '@mui/icons-material'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler,
} from 'chart.js'
import { Line, Doughnut } from 'react-chartjs-2'
import { dashboardAPI, executionsAPI, suitesAPI } from '../api/client'
import AdvancedFilter from '../components/filters/AdvancedFilter'
import type { FilterConfig } from '../components/filters/AdvancedFilter'
import ExportImport from '../components/common/ExportImport'
import { useRealTimeUpdates } from '../hooks/useRealTimeUpdates'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import {
  computeOutcomes,
  computeWeekOverWeek,
  buildOutcomeChartData,
  type TrendPoint,
} from '../utils/dashboardCalculations'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
)

// Moving average helper for the trends chart.
function calculateMovingAverage(data: number[], windowSize = 7): number[] {
  const result: number[] = []
  for (let i = 0; i < data.length; i++) {
    const start = Math.max(0, i - windowSize + 1)
    const window = data.slice(start, i + 1)
    const avg = window.reduce((a, b) => a + b, 0) / window.length
    result.push(avg)
  }
  return result
}

// Enhanced Stat Card Component
function EnhancedStatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendLabel,
  gradient,
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  trendLabel?: string
  gradient: string
}) {
  return (
    <Card
      sx={{
        background: gradient,
        color: 'white',
        transition: 'transform 0.2s, box-shadow 0.2s',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
        },
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              {title}
            </Typography>
            <Typography variant="h3" fontWeight="bold" sx={{ my: 1 }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" sx={{ opacity: 0.8 }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box sx={{ opacity: 0.8 }}>{icon}</Box>
        </Box>
        {trend && trendLabel && (
          <Box display="flex" alignItems="center" mt={1}>
            {trend === 'up' && <TrendingUp sx={{ mr: 0.5 }} />}
            {trend === 'down' && <TrendingDown sx={{ mr: 0.5 }} />}
            <Typography variant="caption">{trendLabel}</Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  )
}

// Quick Action Button Component
function QuickActionButton({
  icon,
  label,
  onClick,
  color = 'primary',
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  color?: 'primary' | 'secondary' | 'success' | 'warning'
}) {
  return (
    <Button
      variant="contained"
      color={color}
      startIcon={icon}
      onClick={onClick}
      sx={{
        px: 3,
        py: 1,
        borderRadius: 2,
        textTransform: 'none',
        fontWeight: 600,
      }}
    >
      {label}
    </Button>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState<FilterConfig>({})
  const [savedFilters, setSavedFilters] = useState<{ name: string; config: FilterConfig }[]>([])

  // Real-time updates
  const { isLive, lastUpdate, toggleLive } = useRealTimeUpdates({
    interval: 10000, // 10 seconds
    queriesToRefresh: ['dashboard-stats', 'dashboard-trends', 'dashboard-recent'],
    enabled: true,
  })

  // All data comes from the real dashboard API (src/api/client.ts).
  const { data: stats, isLoading: statsLoading } = useQuery('dashboard-stats', () =>
    dashboardAPI.getStats()
  )
  const { data: trends, isLoading: trendsLoading } = useQuery('dashboard-trends', () =>
    dashboardAPI.getTrends(30)
  )
  // The backend does not expose /dashboard/recent-executions; we list executions
  // directly and resolve suite names from the suites endpoint.
  const { data: recent, isLoading: recentLoading } = useQuery('dashboard-recent', () =>
    executionsAPI.getAll(undefined, undefined, 0, 10)
  )
  const { data: suites } = useQuery('dashboard-suites', () => suitesAPI.getAll())

  if (statsLoading || trendsLoading || recentLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    )
  }

  const statsData = stats?.data
  const suiteNameById = new Map<number, string>()
  ;(suites?.data || []).forEach((s: any) => suiteNameById.set(s.id, s.name))
  const trendsData: TrendPoint[] = (trends?.data || []).map((t: any) => ({
    date: t.date,
    total: t.total ?? t.executions ?? 0,
    passed: t.passed ?? 0,
    failed: t.failed ?? 0,
  }))
  const recentData = recent?.data || []

  // Moving averages for the trends chart.
  const totalMovingAvg = calculateMovingAverage(trendsData.map((t) => t.total))

  const lineChartData = {
    labels: trendsData.map((t) => t.date),
    datasets: [
      {
        label: 'Total Executions',
        data: trendsData.map((t) => t.total),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.1)',
        fill: true,
      },
      {
        label: '7-Day Moving Average',
        data: totalMovingAvg,
        borderColor: 'rgb(59, 130, 246)',
        borderDash: [5, 5],
        fill: false,
        pointRadius: 0,
      },
      {
        label: 'Passed',
        data: trendsData.map((t) => t.passed),
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
      },
      {
        label: 'Failed',
        data: trendsData.map((t) => t.failed),
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        fill: true,
      },
    ],
  }

  // Real execution-outcomes distribution derived from the trends data
  // (replaces the previous hardcoded [12, 19, 3, 5, 2] test-type mock chart).
  const outcomes = computeOutcomes(trendsData)
  const outcomeChartData = buildOutcomeChartData(outcomes)

  // Real week-over-week trend derived from trends data.
  const wow = computeWeekOverWeek(trendsData)

  const handleExport = async (format: 'csv' | 'json' | 'pdf') => {
    const data = {
      stats: statsData,
      trends: trendsData,
      recent: recentData,
      exportedAt: new Date().toISOString(),
    }

    let content: string
    let filename: string
    let mimeType: string

    if (format === 'json') {
      content = JSON.stringify(data, null, 2)
      filename = 'dashboard-export.json'
      mimeType = 'application/json'
    } else if (format === 'csv') {
      const csvRows = [
        'Date,Total,Passed,Failed',
        ...trendsData.map((t) => `${t.date},${t.total},${t.passed},${t.failed}`),
      ]
      content = csvRows.join('\n')
      filename = 'dashboard-export.csv'
      mimeType = 'text/csv'
    } else {
      content = JSON.stringify(data, null, 2)
      filename = 'dashboard-export.txt'
      mimeType = 'text/plain'
    }

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImport = async (file: File, format: 'csv' | 'json') => {
    // Import is a future enhancement; log for now.
    console.log('Importing:', file.name, format)
  }

  const handleSaveFilter = (name: string, config: FilterConfig) => {
    setSavedFilters((prev) => [...prev, { name, config }])
  }

  return (
    <Box>
      {/* Breadcrumb Navigation */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link color="inherit" href="/" underline="hover">
          Home
        </Link>
        <Typography color="text.primary">Dashboard</Typography>
      </Breadcrumbs>

      {/* Header with Actions */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="h4" fontWeight="bold">
            Dashboard
          </Typography>
          {/* Live Indicator */}
          <Chip
            icon={
              <FiberManualRecord
                sx={{
                  fontSize: 12,
                  color: isLive ? '#00ff00' : 'grey.500',
                  animation: isLive ? 'pulse 2s infinite' : 'none',
                  '@keyframes pulse': {
                    '0%': { opacity: 1 },
                    '50%': { opacity: 0.5 },
                    '100%': { opacity: 1 },
                  },
                }}
              />
            }
            label={isLive ? 'Live' : 'Paused'}
            size="small"
            onClick={toggleLive}
            sx={{ cursor: 'pointer' }}
          />
          {lastUpdate && (
            <Typography variant="caption" color="text.secondary">
              Last update: {lastUpdate.toLocaleTimeString()}
            </Typography>
          )}
        </Box>

        {/* Export/Import */}
        <ExportImport
          onExport={handleExport}
          onImport={handleImport}
          exportLabel="Export"
          importLabel="Import"
        />
      </Box>

      {/* Advanced Filters */}
      <AdvancedFilter
        onFilterChange={setFilters}
        savedFilters={savedFilters}
        onSaveFilter={handleSaveFilter}
      />

      {/* Quick Actions */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <QuickActionButton
          icon={<Add />}
          label="New Test Suite"
          onClick={() => navigate('/suites')}
          color="primary"
        />
        <QuickActionButton
          icon={<PlayCircle />}
          label="Run Tests"
          onClick={() => navigate('/executions')}
          color="success"
        />
        <QuickActionButton
          icon={<AutoFixHigh />}
          label="AI Generate"
          onClick={() => navigate('/self-healing')}
          color="secondary"
        />
        <QuickActionButton
          icon={<Assessment />}
          label="View Reports"
          onClick={() => navigate('/executions')}
          color="warning"
        />
      </Box>

      {/* Stats Cards - all values come from the real /dashboard/stats API.
          Field names match the DashboardStats schema. */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={2.4}>
          <EnhancedStatCard
            title="Total Executions"
            value={statsData?.total_executions ?? 0}
            icon={<PlayArrow sx={{ fontSize: 48 }} />}
            trend={wow.direction}
            trendLabel={wow.label}
            gradient="linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={2.4}>
          <EnhancedStatCard
            title="Test Suites"
            value={statsData?.total_suites ?? 0}
            icon={<Folder sx={{ fontSize: 48 }} />}
            gradient="linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={2.4}>
          <EnhancedStatCard
            title="Success Rate"
            value={`${Number(statsData?.success_rate ?? 0).toFixed(1)}%`}
            subtitle={`${statsData?.total_cases ?? 0} test cases`}
            icon={<CheckCircle sx={{ fontSize: 48 }} />}
            gradient="linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={2.4}>
          <EnhancedStatCard
            title="Avg Duration"
            value={`${Math.round(statsData?.avg_duration ?? 0)}s`}
            subtitle="per execution"
            icon={<Schedule sx={{ fontSize: 48 }} />}
            gradient="linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={2.4}>
          <EnhancedStatCard
            title="Active Runs"
            value={statsData?.active_executions ?? 0}
            subtitle={`${statsData?.last_24h_executions ?? 0} in last 24h`}
            icon={<Warning sx={{ fontSize: 48 }} />}
            gradient="linear-gradient(135deg, #fa709a 0%, #fee140 100%)"
          />
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight="bold">
                Execution Trends (Last 30 Days)
              </Typography>
              <Line
                data={lineChartData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      position: 'top',
                    },
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                    },
                  },
                }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight="bold">
                Execution Results
              </Typography>
              <Doughnut
                data={outcomeChartData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      position: 'bottom',
                    },
                  },
                }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Executions - from /dashboard/recent-executions */}
      <Box sx={{ mt: 3 }}>
        <Card>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6" fontWeight="bold">
                Recent Executions
              </Typography>
              <Button
                size="small"
                endIcon={<Refresh />}
                onClick={() => {
                  queryClient.invalidateQueries('dashboard-recent')
                }}
              >
                Refresh
              </Button>
            </Box>
            {recentData.length === 0 ? (
              <Box py={3} textAlign="center">
                <Typography color="text.secondary">
                  No recent executions. Run a test suite to see results here.
                </Typography>
              </Box>
            ) : (
              recentData.map((execution: any) => {
                const startedAt = execution.started_at
                  ? new Date(execution.started_at).toLocaleString()
                  : '—'
                const suiteName =
                  suiteNameById.get(execution.suite_id) ||
                  execution.suite_name ||
                  `Execution #${execution.id}`
                const passed = execution.passed_tests ?? execution.passed ?? 0
                return (
                  <Fade in key={execution.id}>
                    <Box
                      display="flex"
                      alignItems="center"
                      justifyContent="space-between"
                      sx={{
                        py: 1.5,
                        px: 2,
                        mb: 1,
                        borderRadius: 1,
                        bgcolor: 'background.default',
                        transition: 'background-color 0.2s',
                        '&:hover': {
                          bgcolor: 'action.hover',
                        },
                      }}
                    >
                      <Box>
                        <Typography variant="body1" fontWeight="medium">
                          {suiteName}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {execution.environment || 'production'} • {startedAt}
                        </Typography>
                      </Box>
                      <Box display="flex" alignItems="center" gap={1}>
                        {execution.total_tests > 0 && (
                          <Chip
                            size="small"
                            label={`${passed}/${execution.total_tests} passed`}
                            color={
                              passed === execution.total_tests ? 'success' : 'warning'
                            }
                          />
                        )}
                        <Chip
                          size="small"
                          label={execution.status}
                          color={
                            execution.status === 'passed'
                              ? 'success'
                              : execution.status === 'failed' || execution.status === 'error'
                              ? 'error'
                              : execution.status === 'running'
                              ? 'primary'
                              : 'default'
                          }
                        />
                      </Box>
                    </Box>
                  </Fade>
                )
              })
            )}
          </CardContent>
        </Card>
      </Box>
    </Box>
  )
}
