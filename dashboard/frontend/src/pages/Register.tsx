import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  InputAdornment,
  IconButton,
  Stepper,
  Step,
  StepLabel,
} from '@mui/material'
import {
  Visibility,
  VisibilityOff,
  Email,
  Person,
  Lock,
  Check,
} from '@mui/icons-material'
import { useMutation } from 'react-query'
import { authAPI } from '../api/client'
import toast from 'react-hot-toast'

const steps = ['Account', 'Details', 'Verify']

export default function Register() {
  const [activeStep, setActiveStep] = useState(0)
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [verificationCode, setVerificationCode] = useState('')
  const navigate = useNavigate()

  const registerMutation = useMutation(
    () => authAPI.register(formData),
    {
      onSuccess: () => {
        toast.success('Account created! Please verify your email.')
        setActiveStep(2)
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Registration failed')
      },
    }
  )

  const verifyMutation = useMutation(
    () => authAPI.verifyEmail(formData.email, verificationCode),
    {
      onSuccess: () => {
        toast.success('Email verified! You can now login.')
        navigate('/login')
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Verification failed')
      },
    }
  )

  const handleChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [field]: e.target.value })
  }

  const handleNext = () => {
    if (activeStep === 0) {
      if (!formData.username || !formData.email || !formData.password) {
        toast.error('Please fill in all fields')
        return
      }
      if (formData.password !== formData.confirmPassword) {
        toast.error('Passwords do not match')
        return
      }
      if (formData.password.length < 8) {
        toast.error('Password must be at least 8 characters')
        return
      }
    }
    
    if (activeStep === 1) {
      registerMutation.mutate()
      return
    }
    
    setActiveStep((prev) => prev + 1)
  }

  const handleBack = () => {
    setActiveStep((prev) => prev - 1)
  }

  const handleVerify = () => {
    if (!verificationCode) {
      toast.error('Please enter verification code')
      return
    }
    verifyMutation.mutate()
  }

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <>
            <TextField
              fullWidth
              label="Username"
              variant="outlined"
              slotProps={{ input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <Person />
                  </InputAdornment>
                ),
              } }}
              value={formData.username}
              onChange={handleChange('username')}
              
            />
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
              value={formData.email}
              onChange={handleChange('email')}
              
            />
            <TextField
              fullWidth
              label="Password"
              type={showPassword ? 'text' : 'password'}
              variant="outlined"
              slotProps={{ input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword(!showPassword)}>
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              } }}
              value={formData.password}
              onChange={handleChange('password')}
              
            />
            <TextField
              fullWidth
              label="Confirm Password"
              type="password"
              variant="outlined"
              sx={{ mb: 2 }}
              value={formData.confirmPassword}
              onChange={handleChange('confirmPassword')}
              error={formData.confirmPassword && formData.password !== formData.confirmPassword}
              helperText={
                formData.confirmPassword && formData.password !== formData.confirmPassword
                  ? 'Passwords do not match'
                  : ''
              }
            />
          </>
        )
      
      case 1:
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="h6" gutterBottom>
              Review Your Information
            </Typography>
            <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography><strong>Username:</strong> {formData.username}</Typography>
              <Typography><strong>Email:</strong> {formData.email}</Typography>
            </Box>
            <Alert severity="info" sx={{ mt: 2 }}>
              By registering, you agree to our Terms of Service and Privacy Policy.
            </Alert>
          </Box>
        )
      
      case 2:
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="h6" gutterBottom>
              Verify Your Email
            </Typography>
            <Typography color="textSecondary" component="p">
              We've sent a verification code to {formData.email}
            </Typography>
            <TextField
              fullWidth
              label="Verification Code"
              variant="outlined"
              sx={{ mb: 2 }}
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value)}
              placeholder="Enter 6-digit code"
            />
            <Button
              fullWidth
              variant="contained"
              size="large"
              sx={{ mt: 2 }}
              onClick={handleVerify}
              disabled={verifyMutation.isLoading}
            >
              {verifyMutation.isLoading ? 'Verifying...' : 'Verify Email'}
            </Button>
          </Box>
        )
      
      default:
        return null
    }
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
          <Typography variant="h4" gutterBottom align="center" sx={{ fontWeight: "bold" }}>
            Create Account
          </Typography>
          <Typography variant="body2" color="textSecondary" align="center" sx={{ mb: 3 }}>
            Join QA-FRAMEWORK and start testing smarter
          </Typography>

          <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          {renderStepContent(activeStep)}

          <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
            {activeStep > 0 && activeStep < 2 && (
              <Button
                fullWidth
                variant="outlined"
                size="large"
                onClick={handleBack}
              >
                Back
              </Button>
            )}
            {activeStep < 2 && (
              <Button
                fullWidth
                variant="contained"
                size="large"
                onClick={handleNext}
                disabled={registerMutation.isLoading}
              >
                {activeStep === 1
                  ? registerMutation.isLoading
                    ? 'Creating Account...'
                    : 'Create Account'
                  : 'Next'}
              </Button>
            )}
          </Box>

          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="textSecondary">
              Already have an account?{' '}
              <Link to="/login" style={{ color: '#667eea', textDecoration: 'none', fontWeight: 'bold' }}>
                Sign In
              </Link>
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}
