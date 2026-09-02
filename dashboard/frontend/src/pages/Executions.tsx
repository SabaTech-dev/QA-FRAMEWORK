import { useQuery } from 'react-query'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  CircularProgress,
  Tooltip,
} from '@mui/material'
import {
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Visibility as VisibilityIcon,
} from '@mui/icons-material'
import { executionsAPI } from '../api/client'
import { celebrateFirstSuccess, celebratePerfectScore } from '../utils/celebrations'
import toast from 'react-hot-toast'
import EmptyState from '../components/common/EmptyState'
import SkeletonLoader, { TableSkeleton } from '../components/common/SkeletonLoader'

export default function Executions() {
  const { data: executions, isLoading, refetch } = useQuery('executions', () =>
    executionsAPI.getAll()
  )

  const handleSuccessCelebration = () => {
    // Celebrate first successful test (session-based)
    celebrateFirstSuccess()

    // Check for 100% pass rate
    executions?.data?.forEach((execution: any) => {
      if (
        execution.status === 'completed' &&
        execution.total_tests > 0 &&
        execution.passed_tests === execution.total_tests
      ) {
        celebratePerfectScore()
      }
    })
  }

  const startExecution = (executionId: number) => {
    executionsAPI.start(executionId).then(() => {
      toast.success('Execution started')
      refetch()
    }).catch(() => {
      toast.error('Failed to start execution')
    })
  }

  const stopExecution = (executionId: number) => {
    executionsAPI.stop(executionId).then(() => {
      toast.success('Execution stopped')
      refetch()
      handleSuccessCelebration()
    }).catch(() => {
      toast.error('Failed to stop execution')
    })
  }

  if (isLoading) {
    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}   >
          <Typography variant="h4">Test Executions</Typography>
        </Box>
        <TableSkeleton rows={5} />
      </Box>
    )
  }

  // Show empty state if no executions
  if (!executions?.data || executions.data.length === 0) {
    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}   >
          <Typography variant="h4">Test Executions</Typography>
        </Box>
        <EmptyState
          illustration="/illustrations/empty-executions.svg"
          title="No Executions Yet"
          description="Run your test suites to see execution results and test reports here. Track your test history and analyze performance over time."
          actionLabel="Run Your First Test"
          onAction={() => {
            // Navigate to suites to run a test
            window.location.href = '/suites'
          }}
        />
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}   >
        <Typography variant="h4">Test Executions</Typography>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Suite</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Environment</TableCell>
              <TableCell>Started</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell>Results</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {executions?.data?.map((execution: any) => (
              <TableRow key={execution.id}>
                <TableCell>{execution.id}</TableCell>
                <TableCell>{execution.suite_name}</TableCell>
                <TableCell>
                  <Chip
                    label={execution.status}
                    color={
                      execution.status === 'completed'
                        ? 'success'
                        : execution.status === 'running'
                        ? 'primary'
                        : execution.status === 'failed'
                        ? 'error'
                        : 'default'
                    }
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Chip label={execution.environment} size="small" />
                </TableCell>
                <TableCell>{new Date(execution.started_at).toLocaleString()}</TableCell>
                <TableCell>{execution.duration ? `${execution.duration}s` : '-'}</TableCell>
                <TableCell>
                  <Box sx={{ display: "flex", gap: 0.5 }} >
                    <Chip
                      label={`P:${execution.passed_tests}`}
                      size="small"
                      color="success"
                    />
                    <Chip
                      label={`F:${execution.failed_tests}`}
                      size="small"
                      color="error"
                    />
                    <Chip
                      label={`S:${execution.skipped_tests}`}
                      size="small"
                      color="warning"
                    />
                  </Box>
                </TableCell>
                <TableCell>
                  {execution.status === 'running' ? (
                    <Tooltip title="Stop Execution">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => stopExecution(execution.id)}
                        aria-label="Stop running execution"
                      >
                        <StopIcon />
                      </IconButton>
                    </Tooltip>
                  ) : (
                    <Tooltip title="Run Again">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => startExecution(execution.id)}
                        aria-label="Start execution"
                      >
                        <PlayArrowIcon />
                      </IconButton>
                    </Tooltip>
                  )}
                  <Tooltip title="View Details">
                    <IconButton size="small" aria-label="View execution details">
                      <VisibilityIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}
