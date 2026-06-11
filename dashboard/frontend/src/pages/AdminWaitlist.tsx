import { useState, useEffect } from 'react'
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
  Button,
  Chip,
  IconButton,
  TextField,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  TablePagination,
} from '@mui/material'
import {
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  Visibility as ViewIcon,
  People as PeopleIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import apiClient from '../api/client'
import toast from 'react-hot-toast'
import { format } from 'date-fns'

interface WaitlistEntry {
  id: number
  email: string
  name: string
  role: string | null
  company: string | null
  use_case: string | null
  status: 'pending' | 'approved' | 'rejected'
  source: string | null
  created_at: string
  invite_sent_at: string | null
  approved_at: string | null
}

interface WaitlistStats {
  total: number
  by_status: Record<string, number>
  by_role: Record<string, number>
  by_source: Record<string, number>
  conversion_rate: number
}

const ROLE_LABELS: Record<string, string> = {
  qa_engineer: 'QA Engineer',
  developer: 'Developer',
  devops: 'DevOps Engineer',
  engineering_manager: 'Engineering Manager',
  cto: 'CTO / VP Engineering',
  other: 'Other',
}

const STATUS_COLORS: Record<string, 'warning' | 'success' | 'error'> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'error',
}

export default function AdminWaitlistPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(20)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [roleFilter, setRoleFilter] = useState<string>('')
  const [selectedEntry, setSelectedEntry] = useState<WaitlistEntry | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  const { data, isLoading } = useQuery(
    ['waitlist', page, rowsPerPage, statusFilter, roleFilter],
    () => apiClient.get('/waitlist/list', {
      params: {
        page: page + 1,
        page_size: rowsPerPage,
        ...(statusFilter && { status_filter: statusFilter }),
        ...(roleFilter && { role_filter: roleFilter }),
      },
    }).then(r => r.data),
    { keepPreviousData: true }
  )

  const { data: stats } = useQuery(
    'waitlist-stats',
    () => apiClient.get('/waitlist/stats').then(r => r.data),
    { refetchInterval: 30000 }
  )

  const approveMutation = useMutation(
    (id: number) => apiClient.post(`/waitlist/approve/${id}`),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('waitlist')
        queryClient.invalidateQueries('waitlist-stats')
        toast.success('Applicant approved!')
      },
      onError: () => toast.error('Failed to approve'),
    }
  )

  const handleApprove = (id: number) => {
    if (confirm('Approve this applicant and send them beta access?')) {
      approveMutation.mutate(id)
    }
  }

  const handleViewDetails = (entry: WaitlistEntry) => {
    setSelectedEntry(entry)
    setDetailOpen(true)
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
        Waitlist Management
      </Typography>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="overline">Total Signups</Typography>
              <Typography variant="h3">{stats?.total || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="overline">Pending Review</Typography>
              <Typography variant="h3" color="warning.main">
                {stats?.by_status?.pending || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="overline">Approved</Typography>
              <Typography variant="h3" color="success.main">
                {stats?.by_status?.approved || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="overline">Conversion Rate</Typography>
              <Typography variant="h3">{stats?.conversion_rate || 0}%</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <TextField
          select
          size="small"
          label="Status"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0) }}
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">All Statuses</MenuItem>
          <MenuItem value="pending">Pending</MenuItem>
          <MenuItem value="approved">Approved</MenuItem>
          <MenuItem value="rejected">Rejected</MenuItem>
        </TextField>
        <TextField
          select
          size="small"
          label="Role"
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setPage(0) }}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="">All Roles</MenuItem>
          {Object.entries(ROLE_LABELS).map(([value, label]) => (
            <MenuItem key={value} value={value}>{label}</MenuItem>
          ))}
        </TextField>
      </Box>

      {/* Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Role</TableCell>
              <TableCell>Company</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Signed Up</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data?.items?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">No waitlist signups found</TableCell>
              </TableRow>
            ) : (
              data?.items?.map((entry: WaitlistEntry) => (
                <TableRow key={entry.id} hover>
                  <TableCell>{entry.name}</TableCell>
                  <TableCell>{entry.email}</TableCell>
                  <TableCell>{ROLE_LABELS[entry.role] || entry.role || '-'}</TableCell>
                  <TableCell>{entry.company || '-'}</TableCell>
                  <TableCell>
                    <Chip
                      label={entry.status}
                      color={STATUS_COLORS[entry.status]}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {format(new Date(entry.created_at), 'MMM d, yyyy')}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => handleViewDetails(entry)} title="View details">
                      <ViewIcon />
                    </IconButton>
                    {entry.status === 'pending' && (
                      <IconButton
                        size="small"
                        color="success"
                        onClick={() => handleApprove(entry.id)}
                        title="Approve"
                      >
                        <ApproveIcon />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={data?.total || 0}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10))
            setPage(0)
          }}
          rowsPerPageOptions={[10, 20, 50]}
        />
      </TableContainer>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onClose={() => setDetailOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Waitlist Entry Details</DialogTitle>
        <DialogContent>
          {selectedEntry && (
            <Box sx={{ pt: 1 }}>
              <Typography variant="body2"><strong>Name:</strong> {selectedEntry.name}</Typography>
              <Typography variant="body2"><strong>Email:</strong> {selectedEntry.email}</Typography>
              <Typography variant="body2"><strong>Role:</strong> {ROLE_LABELS[selectedEntry.role] || selectedEntry.role || '-'}</Typography>
              <Typography variant="body2"><strong>Company:</strong> {selectedEntry.company || '-'}</Typography>
              <Typography variant="body2"><strong>Status:</strong>
                <Chip
                  label={selectedEntry.status}
                  color={STATUS_COLORS[selectedEntry.status]}
                  size="small"
                  sx={{ ml: 1 }}
                />
              </Typography>
              {selectedEntry.use_case && (
                <>
                  <Typography variant="body2" sx={{ mt: 2 }}><strong>Use Case:</strong></Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
                    {selectedEntry.use_case}
                  </Typography>
                </>
              )}
              <Typography variant="body2" sx={{ mt: 2 }}>
                <strong>Signed up:</strong> {format(new Date(selectedEntry.created_at), 'MMM d, yyyy HH:mm')}
              </Typography>
              {selectedEntry.approved_at && (
                <Typography variant="body2">
                  <strong>Approved:</strong> {format(new Date(selectedEntry.approved_at), 'MMM d, yyyy HH:mm')}
                </Typography>
              )}
              {selectedEntry.source && (
                <Typography variant="body2"><strong>Source:</strong> {selectedEntry.source}</Typography>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {selectedEntry?.status === 'pending' && (
            <Button
              variant="contained"
              color="success"
              onClick={() => {
                handleApprove(selectedEntry.id)
                setDetailOpen(false)
              }}
              startIcon={<ApproveIcon />}
            >
              Approve & Send Invite
            </Button>
          )}
          <Button onClick={() => setDetailOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
