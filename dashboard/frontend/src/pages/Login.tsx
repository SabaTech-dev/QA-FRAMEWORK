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
import { authAPI, onboardingAPI } from '../api/client'
import useAuthStore from '../stores/authStore'
import toast from 'react-hot-toast'
import LoadingButton from '../components/common/LoadingButton'

// Decodifica el payload de un JWT sin verificar la firma (lectura cliente del `sub`).
// Necesario porque el backend no expone un endpoint /me: el login solo devuelve tokens.
function decodeJwtPayload(token: string): Record<string, any> {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=')
    return JSON.parse(atob(padded))
  } catch {
    return {}
  }
}

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
        // Guarda el token primero para que las siguientes llamadas lo incluyan
        useAuthStore.getState().setToken(access_token)

        try {
          // El login solo devuelve tokens. Obtenemos el username desde el JWT
          // y el estado de onboarding desde la API de onboarding (no existe /me).
          const payload = decodeJwtPayload(access_token)
          const tokenUsername = payload.sub || username || 'user'

          let onboardingCompleted = true
          try {
            const obResponse = await onboardingAPI.getState()
            onboardingCompleted = !!obResponse.data?.completed
          } catch {
            // Si no podemos leer el estado, asumimos completado para no bloquear
            onboardingCompleted = true
          }

          const user = {
            id: payload.user_id || 0,
            username: tokenUsername,
            email: payload.email || '',
            is_active: true,
            is_superuser: !!payload.is_superuser,
            onboarding_completed: onboardingCompleted,
          }

          login(access_token, user)
          toast.success('Login successful!')

          navigate(onboardingCompleted ? '/dashboard' : '/onboarding', { replace: true })
        } catch (error) {
          toast.error('Failed to complete login')
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
              Demo: alfred / AlfredDemo2026!
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}