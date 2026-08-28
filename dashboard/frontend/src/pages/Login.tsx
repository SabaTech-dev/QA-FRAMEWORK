import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Typography,
  Alert,
  useTheme,
  alpha,
} from '@mui/material'
import { useMutation } from 'react-query'
import { authAPI } from '../api/client'
import useAuthStore from '../stores/authStore'
import toast from 'react-hot-toast'
import LoadingButton from '../components/common/LoadingButton'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const theme = useTheme()

  const loginMutation = useMutation(
    () => authAPI.login(username, password),
    {
      onSuccess: async (response) => {
        const { access_token } = response.data
        // Save token first so getMe can use it
        useAuthStore.getState().setToken(access_token)
        
        // Now get user info with the token in headers
        try {
          const userResponse = await authAPI.getMe()
          login(access_token, userResponse.data)
          toast.success('Login successful!')
          
          // Redirect to onboarding or dashboard based on user state
          if (!userResponse.data.onboarding_completed) {
            navigate('/onboarding', { replace: true })
          } else {
            navigate('/dashboard', { replace: true })
          }
        } catch {
          toast.error('Failed to get user info')
          useAuthStore.getState().logout()
        }
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Login failed')
      },
    }
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!username || !password) {
      toast.error('Please fill in all fields')
      return
    }
    loginMutation.mutate()
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.secondary.dark} 100%)`,
        p: 2,
      }}
    >
      <Card sx={{ maxWidth: 400, width: '100%' }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom align="center" fontWeight="bold">
            QA Framework
          </Typography>
          <Typography variant="body2" gutterBottom align="center" color="textSecondary">
            Welcome back! Please login to your account.
          </Typography>

          {loginMutation.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Invalid username or password
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Username"
              variant="outlined"
              margin="normal"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loginMutation.isLoading}
              inputProps={{
                'aria-label': 'Username',
              }}
            />
            <TextField
              fullWidth
              label="Password"
              type="password"
              variant="outlined"
              margin="normal"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loginMutation.isLoading}
              inputProps={{
                'aria-label': 'Password',
              }}
            />
            <LoadingButton
              fullWidth
              type="submit"
              variant="contained"
              size="large"
              sx={{ mt: 3 }}
              loading={loginMutation.isLoading}
            >
              Login
            </LoadingButton>
          </form>

          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="textSecondary">
              <Link to="/forgot-password" style={{ color: theme.palette.primary.main, textDecoration: 'none' }}>
                Forgot password?
              </Link>
            </Typography>
          </Box>

          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography variant="body2" color="textSecondary">
              Don't have an account?{' '}
              <Link to="/register" style={{ color: theme.palette.primary.main, textDecoration: 'none', fontWeight: 'bold' }}>
                Sign Up
              </Link>
            </Typography>
          </Box>

          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography variant="caption" color="textSecondary">
              Demo: admin / admin123
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}