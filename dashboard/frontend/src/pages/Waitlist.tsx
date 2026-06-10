import { useState } from 'react'
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  Alert,
  MenuItem,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  Grid,
} from '@mui/material'
import {
  CheckCircle as CheckIcon,
  HowToReg as RegisterIcon,
} from '@mui/icons-material'
import { useMutation } from 'react-query'
import apiClient from '../api/client'
import toast from 'react-hot-toast'

type UserRole = 'qa_engineer' | 'developer' | 'devops' | 'engineering_manager' | 'cto' | 'other'

interface WaitlistFormData {
  email: string
  name: string
  role: UserRole | ''
  company: string
  use_case: string
}

const USER_ROLES = [
  { value: 'qa_engineer', label: 'QA Engineer' },
  { value: 'developer', label: 'Developer' },
  { value: 'devops', label: 'DevOps Engineer' },
  { value: 'engineering_manager', label: 'Engineering Manager' },
  { value: 'cto', label: 'CTO / VP Engineering' },
  { value: 'other', label: 'Other' },
]

const STEPS = ['Your Info', 'Role & Use Case', 'Confirm']

export default function WaitlistPage() {
  const [activeStep, setActiveStep] = useState(0)
  const [submitted, setSubmitted] = useState(false)
  const [formData, setFormData] = useState<WaitlistFormData>({
    email: '',
    name: '',
    role: '',
    company: '',
    use_case: '',
  })

  const waitlistMutation = useMutation(
    () => apiClient.post('/waitlist/signup', {
      ...formData,
      source: 'waitlist_page',
    }),
    {
      onSuccess: () => {
        setSubmitted(true)
        toast.success('You\'re on the waitlist!')
      },
      onError: (error: any) => {
        if (error.response?.status === 409) {
          toast.error('This email is already on the waitlist')
        } else {
          toast.error(error.response?.data?.detail || 'Failed to join waitlist')
        }
      },
    }
  )

  const handleNext = () => {
    if (activeStep === 0) {
      if (!formData.name) { toast.error('Please enter your name'); return }
      if (!formData.email) { toast.error('Please enter your email'); return }
      if (!/\S+@\S+\.\S+/.test(formData.email)) { toast.error('Please enter a valid email'); return }
    }
    if (activeStep === 1 && !formData.role) {
      toast.error('Please select your role')
      return
    }
    setActiveStep((prev) => prev + 1)
  }

  const handleBack = () => setActiveStep((prev) => prev - 1)
  const handleSubmit = () => waitlistMutation.mutate()

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth
              required
              label="Full Name"
              placeholder="Jane Doe"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
            <TextField
              fullWidth
              required
              type="email"
              label="Email Address"
              placeholder="jane@company.com"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              helperText="We'll send your beta invite here"
            />
            <TextField
              fullWidth
              label="Company (Optional)"
              placeholder="Acme Inc."
              value={formData.company}
              onChange={(e) => setFormData({ ...formData, company: e.target.value })}
            />
          </Box>
        )

      case 1:
        return (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              select
              fullWidth
              required
              label="Your Role"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value as UserRole })}
            >
              {USER_ROLES.map((r) => (
                <MenuItem key={r.value} value={r.value}>{r.label}</MenuItem>
              ))}
            </TextField>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="How do you plan to use QA-FRAMEWORK? (Optional)"
              placeholder="E.g., Automated testing for our CI/CD pipeline, reducing flaky tests, AI test generation..."
              value={formData.use_case}
              onChange={(e) => setFormData({ ...formData, use_case: e.target.value })}
            />
          </Box>
        )

      case 2:
        return (
          <Box sx={{ textAlign: 'center', py: 2 }}>
            <Typography variant="h6" gutterBottom>
              Review Your Information
            </Typography>
            <Box sx={{ textAlign: 'left', bgcolor: 'grey.100', p: 2, borderRadius: 1, mb: 2 }}>
              <Typography variant="body2">
                <strong>Name:</strong> {formData.name}
              </Typography>
              <Typography variant="body2">
                <strong>Email:</strong> {formData.email}
              </Typography>
              {formData.company && (
                <Typography variant="body2">
                  <strong>Company:</strong> {formData.company}
                </Typography>
              )}
              <Typography variant="body2">
                <strong>Role:</strong> {USER_ROLES.find(r => r.value === formData.role)?.label || formData.role}
              </Typography>
              {formData.use_case && (
                <>
                  <Typography variant="body2" sx={{ mt: 1 }}><strong>Use Case:</strong></Typography>
                  <Typography variant="body2">{formData.use_case}</Typography>
                </>
              )}
            </Box>
            <Typography variant="body2" color="text.secondary">
              By joining, you agree to receive updates about the beta program.
              We'll never share your email with third parties.
            </Typography>
          </Box>
        )

      default:
        return null
    }
  }

  if (submitted) {
    return (
      <Container maxWidth="sm" sx={{ py: 8 }}>
        <Card sx={{ textAlign: 'center' }}>
          <CardContent sx={{ py: 6 }}>
            <CheckIcon sx={{ fontSize: 72, color: 'success.main', mb: 2 }} />
            <Typography variant="h4" gutterBottom>
              You're on the list! 🎉
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
              We've registered <strong>{formData.email}</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              We'll review your application and send you beta access as soon as spots open up.
              Keep an eye on your inbox!
            </Typography>
          </CardContent>
        </Card>
      </Container>
    )
  }

  return (
    <Box sx={{
      minHeight: '100vh',
      bgcolor: 'background.default',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      py: 8,
    }}>
      <Container maxWidth="sm">
        <Card>
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ textAlign: 'center', mb: 3 }}>
              <RegisterIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h4" gutterBottom>
                Join the Waitlist
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Be among the first to experience AI-powered testing that heals itself
              </Typography>
            </Box>

            <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
              {STEPS.map((label) => (
                <Step key={label}><StepLabel>{label}</StepLabel></Step>
              ))}
            </Stepper>

            {renderStepContent(activeStep)}

            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
              <Button disabled={activeStep === 0} onClick={handleBack}>
                Back
              </Button>
              {activeStep === STEPS.length - 1 ? (
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleSubmit}
                  disabled={waitlistMutation.isLoading}
                  startIcon={waitlistMutation.isLoading ? <CircularProgress size={20} /> : <CheckIcon />}
                >
                  {waitlistMutation.isLoading ? 'Submitting...' : 'Join Waitlist'}
                </Button>
              ) : (
                <Button variant="contained" color="primary" onClick={handleNext}>
                  Next
                </Button>
              )}
            </Box>

            {waitlistMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {waitlistMutation.error?.response?.data?.detail || 'Failed to join. Please try again.'}
              </Alert>
            )}
          </CardContent>
        </Card>

        <Box sx={{ textAlign: 'center', mt: 3 }}>
          <Typography variant="body2" color="white">
            Already have access? <a href="/login" style={{ color: 'white' }}>Sign in</a>
          </Typography>
        </Box>
      </Container>
    </Box>
  )
}
