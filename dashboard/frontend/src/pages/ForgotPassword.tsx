import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  InputAdornment,
  IconButton,
} from '@mui/material'
import {
  Visibility,
  VisibilityOff,
  Email,
  ArrowBack,
} from '@mui/icons-material'
import { useMutation } from 'react-query'
import { authAPI } from '../api/client'
import toast from 'react-hot-toast'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [showEmailIcon, setShowEmailIcon] = useState(true)

  const resetMutation = useMutation(
    () => authAPI.forgotPassword(email),
    {
      onSuccess: () => {
        toast.success('Reset instructions sent to your email')
        setSent(true)
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to send reset email')
      },
    }
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) {
      toast.error('Please enter your email')
      return
    }
    resetMutation.mutate()
  }

  if (sent) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          p: 2,
        }}
      >
        <Card sx={{ maxWidth: 500, width: '100%' }}>
          <CardContent sx={{ p: 4, textAlign: 'center' }}>
            <Email sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />
            <Typography variant="h4" gutterBottom sx={{ fontWeight: "bold" }}>
              Check Your Email
            </Typography>
            <Typography color="textSecondary" component="p">
              We've sent password reset instructions to:
            </Typography>
            <Typography variant="h6" color="primary" sx={{ mb: 3 }}>
              {email}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Didn't receive the email? Check your spam folder or{' '}
              <Link
                to="/forgot-password"
                style={{ color: '#667eea', textDecoration: 'none', fontWeight: 'bold' }}
                onClick={() => setSent(false)}
              >
                try again
              </Link>
            </Typography>
            <Button
              component={Link}
              to="/login"
              fullWidth
              variant="outlined"
              size="large"
              sx={{ mt: 3 }}
            >
              Back to Login
            </Button>
          </CardContent>
        </Card>
      </Box>
    )
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        p: 2,
      }}
    >
      <Card sx={{ maxWidth: 500, width: '100%' }}>
        <CardContent sx={{ p: 4 }}>
          <Button
            component={Link}
            to="/login"
            startIcon={<ArrowBack />}
            sx={{ mb: 2 }}
          >
            Back to Login
          </Button>
          
          <Typography variant="h4" gutterBottom sx={{ fontWeight: "bold" }}>
            Forgot Password?
          </Typography>
          <Typography color="textSecondary" component="p">
            No worries, we'll send you reset instructions.
          </Typography>

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Email"
              type="email"
              variant="outlined"
              slotProps={{ input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <Email />
                  </InputAdornment>
                ),
              } }}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              
            />
            <Button
              fullWidth
              type="submit"
              variant="contained"
              size="large"
              sx={{ mt: 3 }}
              disabled={resetMutation.isLoading}
            >
              {resetMutation.isLoading ? 'Sending...' : 'Reset Password'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </Box>
  )
}
