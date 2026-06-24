import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  CircularProgress,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material'
import { casesAPI, suitesAPI } from '../api/client'
import toast from 'react-hot-toast'
import EmptyState from '../components/common/EmptyState'
import LoadingButton from '../components/common/LoadingButton'
import { TableSkeleton } from '../components/common/SkeletonLoader'

const EMPTY_FORM = {
  name: '',
  description: '',
  test_code: '',
  test_type: 'api',
  priority: 'medium',
  tags: '',
  suite_id: '',
}

export default function TestCases() {
  const { suiteId } = useParams<{ suiteId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [openDialog, setOpenDialog] = useState(false)
  const [formData, setFormData] = useState({ ...EMPTY_FORM })

  const { data: cases, isLoading } = useQuery(['cases', suiteId], () =>
    casesAPI.getAll(suiteId ? parseInt(suiteId) : undefined)
  )

  const { data: suites } = useQuery('cases-suites', () => suitesAPI.getAll())

  const suitesList = suites?.data || []
  const suiteNameById = new Map<number, string>()
  suitesList.forEach((s: any) => suiteNameById.set(s.id, s.name))

  const createMutation = useMutation(
    (data: any) => casesAPI.create(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['cases', suiteId])
        queryClient.invalidateQueries('dashboard-stats')
        toast.success('Test case created successfully')
        handleCloseDialog()
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to create test case')
      },
    }
  )

  const deleteMutation = useMutation(
    (id: number) => casesAPI.delete(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['cases', suiteId])
        queryClient.invalidateQueries('dashboard-stats')
        toast.success('Test case deleted successfully')
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to delete test case')
      },
    }
  )

  const handleOpenDialog = () => {
    setFormData({
      ...EMPTY_FORM,
      suite_id: suiteId ? String(suiteId) : (suitesList[0]?.id ? String(suitesList[0].id) : ''),
    })
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
  }

  const handleSubmit = () => {
    if (!formData.name) {
      toast.error('Name is required')
      return
    }
    if (!formData.test_code || formData.test_code.length < 10) {
      toast.error('Test code is required (min 10 characters)')
      return
    }
    const suiteIdValue = formData.suite_id || (suiteId ?? '')
    if (!suiteIdValue) {
      toast.error('Please select a test suite')
      return
    }

    const payload = {
      suite_id: parseInt(suiteIdValue),
      name: formData.name,
      description: formData.description || undefined,
      test_code: formData.test_code,
      test_type: formData.test_type,
      priority: formData.priority,
      tags: formData.tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    }
    createMutation.mutate(payload)
  }

  const casesList = cases?.data || []

  if (isLoading) {
    return (
      <Box>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box display="flex" alignItems="center" gap={2}>
            {suiteId && (
              <IconButton disabled>
                <ArrowBackIcon />
              </IconButton>
            )}
            <Typography variant="h4">Test Cases</Typography>
          </Box>
          <Button variant="contained" disabled>
            New Test Case
          </Button>
        </Box>
        <TableSkeleton rows={5} />
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={2}>
          {suiteId && (
            <Tooltip title="Back to Suites">
              <IconButton onClick={() => navigate('/suites')} aria-label="Go back to test suites">
                <ArrowBackIcon />
              </IconButton>
            </Tooltip>
          )}
          <Typography variant="h4">
            Test Cases{suiteId && suiteNameById.has(parseInt(suiteId)) ? ` — ${suiteNameById.get(parseInt(suiteId))}` : ''}
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenDialog}
          aria-label="Create new test case"
        >
          New Test Case
        </Button>
      </Box>

      {casesList.length === 0 ? (
        <EmptyState
          illustration="/illustrations/empty-cases.svg"
          title="No Test Cases Yet"
          description="Create your first test case to start automating your QA process. Test cases contain the code that gets executed within a suite."
          actionLabel="Create First Test Case"
          onAction={handleOpenDialog}
        />
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                {!suiteId && <TableCell>Suite</TableCell>}
                <TableCell>Type</TableCell>
                <TableCell>Priority</TableCell>
                <TableCell>Tags</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {casesList.map((testCase: any) => (
                <TableRow key={testCase.id} hover>
                  <TableCell>{testCase.name}</TableCell>
                  {!suiteId && (
                    <TableCell>
                      {suiteNameById.get(testCase.suite_id) || `Suite #${testCase.suite_id}`}
                    </TableCell>
                  )}
                  <TableCell>
                    <Chip label={testCase.test_type} size="small" />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={testCase.priority}
                      color={
                        testCase.priority === 'critical'
                          ? 'error'
                          : testCase.priority === 'high'
                          ? 'warning'
                          : testCase.priority === 'medium'
                          ? 'default'
                          : 'success'
                      }
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {testCase.tags?.length ? (
                      testCase.tags.map((tag: string) => (
                        <Chip key={tag} label={tag} size="small" sx={{ mr: 0.5 }} />
                      ))
                    ) : (
                      '—'
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={testCase.is_active ? 'Active' : 'Inactive'}
                      color={testCase.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Delete Test Case">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => deleteMutation.mutate(testCase.id)}
                        disabled={deleteMutation.isLoading}
                        aria-label="Delete test case"
                      >
                        {deleteMutation.isLoading ? <CircularProgress size={20} /> : <DeleteIcon />}
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>Create Test Case</DialogTitle>
        <DialogContent>
          {!suiteId && (
            <FormControl fullWidth margin="normal">
              <InputLabel>Test Suite</InputLabel>
              <Select
                value={formData.suite_id}
                label="Test Suite"
                onChange={(e) => setFormData({ ...formData, suite_id: e.target.value })}
              >
                {suitesList.length === 0 ? (
                  <MenuItem value="" disabled>
                    No suites available — create one first
                  </MenuItem>
                ) : (
                  suitesList.map((s: any) => (
                    <MenuItem key={s.id} value={s.id}>
                      {s.name}
                    </MenuItem>
                  ))
                )}
              </Select>
            </FormControl>
          )}
          <TextField
            fullWidth
            label="Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Description"
            multiline
            rows={2}
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Test Code"
            multiline
            rows={6}
            value={formData.test_code}
            onChange={(e) => setFormData({ ...formData, test_code: e.target.value })}
            margin="normal"
            placeholder={'def test_example():\n    assert True'}
            helperText="Minimum 10 characters"
          />
          <Box display="flex" gap={2} mt={2}>
            <FormControl fullWidth>
              <InputLabel>Test Type</InputLabel>
              <Select
                value={formData.test_type}
                label="Test Type"
                onChange={(e) => setFormData({ ...formData, test_type: e.target.value })}
              >
                <MenuItem value="api">API Testing</MenuItem>
                <MenuItem value="ui">UI Testing</MenuItem>
                <MenuItem value="db">Database Testing</MenuItem>
                <MenuItem value="security">Security Testing</MenuItem>
                <MenuItem value="performance">Performance Testing</MenuItem>
                <MenuItem value="mobile">Mobile Testing</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                value={formData.priority}
                label="Priority"
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
              >
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
              </Select>
            </FormControl>
          </Box>
          <TextField
            fullWidth
            label="Tags (comma-separated)"
            value={formData.tags}
            onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
            margin="normal"
            placeholder="smoke, regression, api"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <LoadingButton
            loading={createMutation.isLoading}
            onClick={handleSubmit}
            variant="contained"
            disabled={!suiteId && suitesList.length === 0}
          >
            Create
          </LoadingButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
