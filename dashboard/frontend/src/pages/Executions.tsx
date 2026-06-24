import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useNavigate } from 'react-router-dom'
import {
  Box,
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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material'
import {
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Visibility as VisibilityIcon,
  Add as AddIcon,
} from '@mui/icons-material'
import { executionsAPI, suitesAPI } from '../api/client'
import toast from 'react-hot-toast'
import EmptyState from '../components/common/EmptyState'
import { TableSkeleton } from '../components/common/SkeletonLoader'
import LoadingButton from '../components/common/LoadingButton'

// Mapa de colores de estado basado en el enum del backend:
// running | passed | failed | skipped | error
function statusColor(status: string): 'success' | 'error' | 'primary' | 'warning' | 'default' {
  switch (status) {
    case 'passed':
      return 'success'
    case 'failed':
      return 'error'
    case 'running':
      return 'primary'
    case 'error':
      return 'warning'
    default:
      return 'default'
  }
}

export default function Executions() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [openDialog, setOpenDialog] = useState(false)
  const [selectedSuiteId, setSelectedSuiteId] = useState<string>('')

  const { data: executions, isLoading } = useQuery('executions', () =>
    executionsAPI.getAll()
  )

  const { data: suites } = useQuery('executions-suites', () => suitesAPI.getAll())

  const suitesList = suites?.data || []
  const suiteNameById = new Map<number, string>()
  suitesList.forEach((s: any) => suiteNameById.set(s.id, s.name))

  const createMutation = useMutation(
    (suiteId: number) => executionsAPI.create({ suite_id: suiteId }),
    {
      onSuccess: async (_res, suiteId) => {
        // Arranca la ejecución recién creada y refresca la lista.
        const execution = (_res as any)?.data
        try {
          if (execution?.id) {
            await executionsAPI.start(execution.id)
          }
        } catch {
          // La creación ya dejó la ejecución en estado running; no es fatal.
        }
        toast.success(`Execution started for "${suiteNameById.get(suiteId) || 'suite'}"`)
        queryClient.invalidateQueries('executions')
        queryClient.invalidateQueries('dashboard-stats')
        queryClient.invalidateQueries('dashboard-recent')
        setOpenDialog(false)
        setSelectedSuiteId('')
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to create execution')
      },
    }
  )

  const startMutation = useMutation((id: number) => executionsAPI.start(id), {
    onSuccess: () => {
      toast.success('Execution started')
      queryClient.invalidateQueries('executions')
    },
    onError: () => toast.error('Failed to start execution'),
  })

  const stopMutation = useMutation((id: number) => executionsAPI.stop(id), {
    onSuccess: () => {
      toast.success('Execution stopped')
      queryClient.invalidateQueries('executions')
    },
    onError: () => toast.error('Failed to stop execution'),
  })

  const handleCreate = () => {
    if (!selectedSuiteId) {
      toast.error('Please select a test suite')
      return
    }
    createMutation.mutate(parseInt(selectedSuiteId))
  }

  const executionsList = executions?.data || []

  if (isLoading) {
    return (
      <Box>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4">Test Executions</Typography>
        </Box>
        <TableSkeleton rows={5} />
      </Box>
    )
  }

  if (executionsList.length === 0) {
    return (
      <Box>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4">Test Executions</Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
          >
            New Execution
          </Button>
        </Box>
        <EmptyState
          illustration="/illustrations/empty-executions.svg"
          title="No Executions Yet"
          description="Run your test suites to see execution results and test reports here. Track your test history and analyze performance over time."
          actionLabel="Run Your First Test"
          onAction={() => setOpenDialog(true)}
        />
        {renderCreateDialog(openDialog, setOpenDialog, selectedSuiteId, setSelectedSuiteId, suitesList, handleCreate, createMutation.isLoading)}
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Test Executions</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpenDialog(true)}
        >
          New Execution
        </Button>
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
            {executionsList.map((execution: any) => {
              const suiteName = suiteNameById.get(execution.suite_id) || `Suite #${execution.suite_id}`
              const startedAt = execution.started_at
                ? new Date(execution.started_at).toLocaleString()
                : '—'
              return (
                <TableRow key={execution.id} hover>
                  <TableCell>{execution.id}</TableCell>
                  <TableCell>{suiteName}</TableCell>
                  <TableCell>
                    <Chip label={execution.status} color={statusColor(execution.status)} size="small" />
                  </TableCell>
                  <TableCell>
                    <Chip label={execution.environment || 'production'} size="small" />
                  </TableCell>
                  <TableCell>{startedAt}</TableCell>
                  <TableCell>{execution.duration != null ? `${execution.duration}s` : '—'}</TableCell>
                  <TableCell>
                    <Box display="flex" gap={0.5} flexWrap="wrap">
                      <Chip label={`P:${execution.passed_tests ?? 0}`} size="small" color="success" />
                      <Chip label={`F:${execution.failed_tests ?? 0}`} size="small" color="error" />
                      <Chip label={`S:${execution.skipped_tests ?? 0}`} size="small" color="warning" />
                    </Box>
                  </TableCell>
                  <TableCell>
                    {execution.status === 'running' ? (
                      <Tooltip title="Stop Execution">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => stopMutation.mutate(execution.id)}
                          disabled={stopMutation.isLoading}
                          aria-label="Stop running execution"
                        >
                          {stopMutation.isLoading ? <CircularProgress size={20} /> : <StopIcon />}
                        </IconButton>
                      </Tooltip>
                    ) : (
                      <Tooltip title="Run Again">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => startMutation.mutate(execution.id)}
                          disabled={startMutation.isLoading}
                          aria-label="Start execution"
                        >
                          {startMutation.isLoading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
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
              )
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {renderCreateDialog(openDialog, setOpenDialog, selectedSuiteId, setSelectedSuiteId, suitesList, handleCreate, createMutation.isLoading)}
    </Box>
  )
}

function renderCreateDialog(
  open: boolean,
  setOpen: (v: boolean) => void,
  selectedSuiteId: string,
  setSelectedSuiteId: (v: string) => void,
  suitesList: any[],
  onCreate: () => void,
  loading: boolean
) {
  return (
    <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
      <DialogTitle>New Execution</DialogTitle>
      <DialogContent>
        {suitesList.length === 0 ? (
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            No test suites available.{' '}
            <Button size="small" onClick={() => (window.location.href = '/suites')}>
              Create one first
            </Button>
          </Typography>
        ) : (
          <FormControl fullWidth sx={{ mt: 1 }}>
            <InputLabel>Test Suite</InputLabel>
            <Select
              value={selectedSuiteId}
              label="Test Suite"
              onChange={(e) => setSelectedSuiteId(e.target.value)}
            >
              {suitesList.map((s: any) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setOpen(false)}>Cancel</Button>
        <LoadingButton
          loading={loading}
          onClick={onCreate}
          variant="contained"
          disabled={suitesList.length === 0}
        >
          Start Execution
        </LoadingButton>
      </DialogActions>
    </Dialog>
  )
}
