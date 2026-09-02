import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
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
  Edit as EditIcon,
  Delete as DeleteIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material'
import { casesAPI } from '../api/client'
import toast from 'react-hot-toast'
import LoadingButton from '../components/common/LoadingButton'
import SkeletonLoader, { TableSkeleton } from '../components/common/SkeletonLoader'

export default function TestCases() {
  const { suiteId } = useParams<{ suiteId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [openDialog, setOpenDialog] = useState(false)
  const [editingCase, setEditingCase] = useState<any>(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    test_code: '',
    test_type: 'api',
    priority: 'medium',
    tags: '',
  })

  const { data: cases, isLoading } = useQuery(['cases', suiteId], () =>
    casesAPI.getAll(suiteId ? parseInt(suiteId) : undefined)
  )

  const createMutation = useMutation(
    (data: any) => casesAPI.create({ ...data, suite_id: parseInt(suiteId!) }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['cases', suiteId])
        toast.success('Test case created successfully')
        handleCloseDialog()
      },
      onError: () => { toast.error('Failed to create test case') },
    }
  )

  const deleteMutation = useMutation(
    (id: number) => casesAPI.delete(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['cases', suiteId])
        toast.success('Test case deleted successfully')
      },
      onError: () => { toast.error('Failed to delete test case') },
    }
  )

  const handleOpenDialog = (testCase?: any) => {
    if (testCase) {
      setEditingCase(testCase)
      setFormData({
        name: testCase.name,
        description: testCase.description || '',
        test_code: testCase.test_code,
        test_type: testCase.test_type,
        priority: testCase.priority,
        tags: testCase.tags?.join(', ') || '',
      })
    } else {
      setEditingCase(null)
      setFormData({
        name: '',
        description: '',
        test_code: '',
        test_type: 'api',
        priority: 'medium',
        tags: '',
      })
    }
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setEditingCase(null)
  }

  const handleSubmit = () => {
    if (!formData.name || !formData.test_code) {
      toast.error('Name and test code are required')
      return
    }
    
    const data = {
      ...formData,
      tags: formData.tags.split(',').map(t => t.trim()).filter(t => t),
    }
    
    createMutation.mutate(data)
  }

  if (isLoading) {
    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}   >
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}  >
            <IconButton disabled>
              <ArrowBackIcon />
            </IconButton>
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
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}   >
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}  >
          <Tooltip title="Back to Suites">
            <IconButton 
              onClick={() => navigate('/suites')}
              aria-label="Go back to test suites"
            >
              <ArrowBackIcon />
            </IconButton>
          </Tooltip>
          <Typography variant="h4">Test Cases</Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
          aria-label="Create new test case"
        >
          New Test Case
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>Tags</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {cases?.data?.map((testCase: any) => (
              <TableRow key={testCase.id}>
                <TableCell>{testCase.name}</TableCell>
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
                        : 'default'
                    }
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {testCase.tags?.map((tag: string) => (
                    <Chip key={tag} label={tag} size="small" sx={{ mr: 0.5 }} />
                  ))}
                </TableCell>
                <TableCell>
                  <Chip
                    label={testCase.is_active ? 'Active' : 'Inactive'}
                    color={testCase.is_active ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Tooltip title="Edit Test Case">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(testCase)}
                      aria-label="Edit test case"
                    >
                      <EditIcon />
                    </IconButton>
                  </Tooltip>
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

      {/* Create/Edit Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingCase ? 'Edit Test Case' : 'Create Test Case'}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Description"
            multiline
            rows={2}
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Test Code"
            multiline
            rows={6}
            value={formData.test_code}
            onChange={(e) => setFormData({ ...formData, test_code: e.target.value })}
            sx={{ mb: 2 }}
            placeholder="def test_example():&#10;    assert True"
          />
          <Box sx={{ display: "flex", gap: 2, mt: 2 }}  >
            <FormControl fullWidth>
              <InputLabel>Test Type</InputLabel>
              <Select
                value={formData.test_type}
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
            sx={{ mb: 2 }}
            placeholder="smoke, regression, api"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <LoadingButton
            loading={createMutation.isLoading}
            onClick={handleSubmit}
            variant="contained"
          >
            {editingCase ? 'Update' : 'Create'}
          </LoadingButton>
        </DialogActions>
      </Dialog>
    </Box>
  )
}