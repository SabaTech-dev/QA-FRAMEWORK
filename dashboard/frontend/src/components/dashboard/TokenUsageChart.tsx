// Token Usage Chart - Estilo ClawX
// Gráfico de barras apiladas mostrando input/output/cache tokens

import { Box, Typography, Paper, Tooltip } from '@mui/material'
import { useQuery } from 'react-query'
import { dashboardAPI } from '../../api/client'

interface TokenUsageData {
  label: string
  inputTokens: number
  outputTokens: number
  cacheTokens: number
  totalTokens: number
}

interface TokenUsageChartProps {
  data?: TokenUsageData[]
  loading?: boolean
}

const TokenUsageBar = ({ data }: { data: TokenUsageData }) => {
  const maxTokens = Math.max(data.totalTokens, 1)
  const inputPercent = (data.inputTokens / data.totalTokens) * 100
  const outputPercent = (data.outputTokens / data.totalTokens) * 100
  const cachePercent = (data.cacheTokens / data.totalTokens) * 100
  const barWidth = Math.max((data.totalTokens / maxTokens) * 100, 6)

  const formatTokens = (value: number): string => {
    return Intl.NumberFormat().format(value)
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 0.5 }}   >
        <Typography variant="body2"  noWrap sx={{ maxWidth: '60%', fontWeight: "medium" }}>
          {data.label}
        </Typography>
        <Typography variant="caption" color="textSecondary">
          {formatTokens(data.totalTokens)} tokens
        </Typography>
      </Box>
      <Box
        sx={{
          height: 12,
          bgcolor: 'grey.200',
          borderRadius: 6,
          overflow: 'hidden',
        }}
      >
        <Tooltip
          title={
            <Box>
              <div>Input: {formatTokens(data.inputTokens)}</div>
              <div>Output: {formatTokens(data.outputTokens)}</div>
              <div>Cache: {formatTokens(data.cacheTokens)}</div>
            </Box>
          }
          arrow
        >
          <Box
            sx={{
              height: '100%',
              width: `${barWidth}%`,
              display: 'flex',
              borderRadius: 6,
              overflow: 'hidden',
              cursor: 'pointer',
              transition: 'width 0.3s ease',
            }}
          >
            {data.inputTokens > 0 && (
              <Box
                sx={{
                  width: `${inputPercent}%`,
                  bgcolor: '#0ea5e9', // sky-500
                }}
              />
            )}
            {data.outputTokens > 0 && (
              <Box
                sx={{
                  width: `${outputPercent}%`,
                  bgcolor: '#8b5cf6', // violet-500
                }}
              />
            )}
            {data.cacheTokens > 0 && (
              <Box
                sx={{
                  width: `${cachePercent}%`,
                  bgcolor: '#f59e0b', // amber-500
                }}
              />
            )}
          </Box>
        </Tooltip>
      </Box>
    </Box>
  )
}

export default function TokenUsageChart({ data: propData, loading }: TokenUsageChartProps) {
  // Use provided data or fetch from API
  const { data: apiData, isLoading } = useQuery(
    'token-usage',
    async (): Promise<{ data: TokenUsageData[] }> => {
      const response = await dashboardAPI.getTokenUsage?.()
      return response ?? { data: [] }
    },
    { enabled: !propData }
  )

  const usageData = propData || apiData?.data || []
  const isLoadingData = loading || isLoading

  // Legend
  const LegendItem = ({ color, label }: { color: string; label: string }) => (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}  >
      <Box
        sx={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          bgcolor: color,
        }}
      />
      <Typography variant="caption" color="textSecondary">
        {label}
      </Typography>
    </Box>
  )

  if (isLoadingData) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Token Usage
        </Typography>
        <Box sx={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}   >
          <Typography color="textSecondary">Loading...</Typography>
        </Box>
      </Paper>
    )
  }

  if (usageData.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Token Usage
        </Typography>
        <Box sx={{ py: 4, textAlign: "center" }} >
          <Typography color="textSecondary">
            No token usage data available yet.
          </Typography>
        </Box>
      </Paper>
    )
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Token Usage
      </Typography>

      {/* Legend */}
      <Box sx={{ display: "flex", gap: 3, mb: 3 }}  >
        <LegendItem color="#0ea5e9" label="Input" />
        <LegendItem color="#8b5cf6" label="Output" />
        <LegendItem color="#f59e0b" label="Cache" />
      </Box>

      {/* Bars */}
      <Box>
        {usageData.slice(0, 8).map((item, index) => (
          <TokenUsageBar key={index} data={item} />
        ))}
      </Box>
    </Paper>
  )
}
