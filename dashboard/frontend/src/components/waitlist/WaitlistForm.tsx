import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material'
import {
  CheckCircle as CheckIcon,
  Email as EmailIcon,
} from '@mui/icons-material'
import { useMutation } from 'react-query'
import { waitlistAPI } from '../../api/client'
import toast from 'react-hot-toast'

interface WaitlistFormData {
  email: string
  name: string
}

const WaitlistForm: React.FC = () => {
  const [formData, setFormData] = useState<WaitlistFormData>({
    email: '',
    name: '',
  })
  const [joined, setJoined] = useState(false)

  const joinMutation = useMutation(
    (data: WaitlistFormData) => waitlistAPI.join(data),
    {
      onSuccess: () => {
        toast.success('You\'re on the waitlist!')
        setJoined(true)
      },
      onError: (error: any) => {
        if (error?.response?.status === 409) {
          toast.error('This email is already on the waitlist')
        } else {
          toast.error('Something went wrong. Please try again.')
        }
      },
    }
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.email) return
    joinMutation.mutate(formData)
  }

  if (joined) {
    return (
      <Card sx={{ maxWidth: 500, mx: 'auto', textAlign: 'center', py: 4 }}>
        <CardContent>
          <CheckIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            You're on the list!
          </Typography>
          <Typography variant="body2" color="text.secondary">
            We'll notify you at <strong>{formData.email}</strong> when it's your turn.
          </Typography>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card sx={{ maxWidth: 500, mx: 'auto' }}>
      <CardContent sx={{ p: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <EmailIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
          <Typography variant="h5" gutterBottom>
            Join the Waitlist
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Be the first to know when we launch.
          </Typography>
        </Box>

        {joinMutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {joinMutation.error?.response?.status === 409
              ? 'This email is already on the waitlist.'
              : 'Something went wrong. Please try again.'}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
          <TextField
            fullWidth
            label="Name (optional)"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            sx={{ mb: 2 }}
            disabled={joinMutation.isLoading}
          />
          <TextField
            required
            fullWidth
            type="email"
            label="Email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            sx={{ mb: 3 }}
            disabled={joinMutation.isLoading}
          />
          <Button
            type="submit"
            fullWidth
            variant="contained"
            size="large"
            disabled={joinMutation.isLoading || !formData.email}
          >
            {joinMutation.isLoading ? (
              <CircularProgress size={24} color="inherit" />
            ) : (
              'Join Waitlist'
            )}
          </Button>
        </Box>
      </CardContent>
    </Card>
  )
}

export default WaitlistForm
