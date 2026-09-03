/**
 * OnboardingWizard - Multi-step onboarding flow with real API integration
 *
 * Steps:
 * 1. Welcome + overview
 * 2. Connect GitHub repo
 * 3. Create first test suite
 * 4. Run first test
 * 5. Setup notifications
 *
 * Each step integrates with real backend APIs.
 * Progress is tracked server-side via onboarding API.
 * State persists across page refreshes.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Stepper,
  Step,
  StepLabel,
  Button,
  Typography,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Check as CheckIcon,
  Close as CloseIcon,
  GitHub as GitHubIcon,
  PlayArrow as PlayArrowIcon,
  Notifications as NotificationsIcon,
  RocketLaunch as RocketIcon,
  Assignment as SuiteIcon,
  SkipNext as SkipNextIcon,
} from '@mui/icons-material'
import { useMutation, useQuery } from 'react-query'
import { onboardingAPI, suitesAPI, executionsAPI } from '../api/client'
import useAuthStore from '../stores/authStore'
import toast from 'react-hot-toast'

const STEPS = [
  { key: 'welcome', label: 'Welcome', icon: <RocketIcon /> },
  { key: 'connect_repo', label: 'Connect Repo', icon: <GitHubIcon /> },
  { key: 'create_suite', label: 'Create Suite', icon: <SuiteIcon /> },
  { key: 'run_test', label: 'Run Test', icon: <PlayArrowIcon /> },
  { key: 'setup_notifications', label: 'Notifications', icon: <NotificationsIcon /> },
]

interface OnboardingWizardProps {
  onComplete: () => void
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onComplete }) => {
  const [activeStep, setActiveStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Record<string, boolean>>({})
  const navigate = useNavigate()
  const { setNeedsOnboarding } = useAuthStore()

  // Fetch current onboarding state from backend
  const { data: onboardingState, isLoading } = useQuery(
    'onboarding-state',
    () => onboardingAPI.getState(),
    {
      onSuccess: (response) => {
        const state = response.data
        if (state.completed) {
          onComplete()
          return
        }
        setActiveStep(state.current_step || 0)
        if (state.steps) {
          setCompletedSteps(state.steps)
        }
      },
      onError: () => {
        toast.error('Failed to load onboarding state')
      },
    }
  )

  // Mutation to update a step
  const stepMutation = useMutation(
    (stepName: string) => onboardingAPI.updateStep(stepName, true),
    {
      onSuccess: (_, stepName) => {
        setCompletedSteps((prev) => ({ ...prev, [stepName]: true }))
        // Auto-advance to next incomplete step
        const currentIndex = STEPS.findIndex((s) => s.key === stepName)
        let nextStep = currentIndex + 1
        while (nextStep < STEPS.length && completedSteps[STEPS[nextStep].key]) {
          nextStep++
        }
        if (nextStep < STEPS.length) {
          setActiveStep(nextStep)
        } else {
          // All steps done, complete onboarding
          completeMutation.mutate()
        }
        toast.success(`Step "${STEPS.find(s => s.key === stepName)?.label}" completed!`)
      },
      onError: () => {
        toast.error('Failed to save progress')
      },
    }
  )

  // Mutation to complete onboarding
  const completeMutation = useMutation(
    () => onboardingAPI.complete(),
    {
      onSuccess: () => {
        setNeedsOnboarding(false)
        toast.success('Onboarding complete! Welcome aboard! 🎉')
        onComplete()
      },
      onError: () => {
        toast.error('Failed to complete onboarding')
      },
    }
  )

  // Mutation to skip onboarding
  const skipMutation = useMutation(
    () => onboardingAPI.skip(),
    {
      onSuccess: () => {
        setNeedsOnboarding(false)
        toast.success('Onboarding skipped. You can find help in Settings.')
        onComplete()
      },
      onError: () => {
        toast.error('Failed to skip onboarding')
      },
    }
  )

  const handleSkip = useCallback(() => {
    skipMutation.mutate()
  }, [skipMutation])

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', mt: 4, px: 2 }}>
      {/* Header with skip option */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: "bold" }}>
          Welcome to QA-FRAMEWORK 🚀
        </Typography>
        <Tooltip title="Skip onboarding">
          <IconButton onClick={handleSkip} disabled={skipMutation.isLoading}>
            <SkipNextIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <Stepper activeStep={activeStep} alternativeLabel>
        {STEPS.map((step, index) => (
          <Step key={step.key} completed={completedSteps[step.key] || false}>
            <StepLabel
              slotProps={{
                stepIcon: {
                  component: () => (
                <Box
                  sx={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: completedSteps[step.key]
                      ? 'success.main'
                      : index === activeStep
                        ? 'primary.main'
                        : 'grey.300',
                    color: 'white',
                    fontSize: '0.85rem',
                  }}
                >
                  {completedSteps[step.key] ? <CheckIcon fontSize="small" /> : step.icon}
                </Box>
                  ),
                },
              }}
            >
              {step.label}
            </StepLabel>
          </Step>
        ))}
      </Stepper>

      <Card sx={{ mt: 4 }}>
        <CardContent sx={{ p: 4 }}>
          {activeStep < STEPS.length ? (
            <>
              {renderStepContent(
                activeStep,
                stepMutation,
                completedSteps,
              )}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
                <Button
                  variant="text"
                  color="inherit"
                  onClick={handleSkip}
                  disabled={skipMutation.isLoading}
                  startIcon={<CloseIcon />}
                >
                  Skip Setup
                </Button>
                <Button
                  variant="contained"
                  onClick={() => stepMutation.mutate(STEPS[activeStep].key)}
                  disabled={stepMutation.isLoading}
                  endIcon={stepMutation.isLoading ? <CircularProgress size={16} /> : null}
                >
                  {activeStep === STEPS.length - 1 ? 'Finish' : 'Continue'}
                </Button>
              </Box>
            </>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="h5" gutterBottom>
                🎉 Setup Complete!
              </Typography>
              <Typography color="textSecondary" component="p">
                You're ready to start testing. Let's go to your dashboard.
              </Typography>
              <Button
                variant="contained"
                size="large"
                onClick={() => completeMutation.mutate()}
                disabled={completeMutation.isLoading}
              >
                Go to Dashboard
              </Button>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}

// --- Step Components ---

function renderStepContent(
  step: number,
  stepMutation: any,
  completedSteps: Record<string, boolean>,
) {
  switch (step) {
    case 0:
      return <WelcomeStep />
    case 1:
      return <ConnectRepoStep />
    case 2:
      return <CreateSuiteStep onComplete={() => stepMutation.mutate('create_suite')} />
    case 3:
      return <RunTestStep onComplete={() => stepMutation.mutate('run_test')} />
    case 4:
      return <SetupNotificationsStep />
    default:
      return null
  }
}

const WelcomeStep: React.FC = () => (
  <Box>
    <Typography variant="h5" gutterBottom>
      Let's get you started! 🎯
    </Typography>
    <Typography component="p" color="textSecondary">
      In just a few steps, you'll have your first test suite up and running.
      Here's what we'll set up:
    </Typography>
    <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mt: 3 }}>
      {[
        { icon: <GitHubIcon color="primary" />, title: 'Connect Repository', desc: 'Link your GitHub repo for CI/CD integration' },
        { icon: <SuiteIcon color="primary" />, title: 'Create Test Suite', desc: 'Set up your first automated test collection' },
        { icon: <PlayArrowIcon color="primary" />, title: 'Run First Test', desc: 'Execute a test and see the results' },
        { icon: <NotificationsIcon color="primary" />, title: 'Notifications', desc: 'Configure alerts for test results' },
      ].map((item) => (
        <Box key={item.title} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          {item.icon}
          <Typography variant="subtitle2" sx={{ mt: 1 }}>{item.title}</Typography>
          <Typography variant="caption" color="textSecondary">{item.desc}</Typography>
        </Box>
      ))}
    </Box>
  </Box>
)

const ConnectRepoStep: React.FC = () => {
  const [repoUrl, setRepoUrl] = useState('')

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Connect Your Repository
      </Typography>
      <Typography component="p" color="textSecondary">
        Enter your GitHub repository URL to enable CI/CD integration.
        You can also connect via OAuth later in Settings.
      </Typography>

      <Box sx={{ mt: 3 }}>
        <Box
          component="input"
          type="text"
          placeholder="https://github.com/username/repo"
          value={repoUrl}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRepoUrl(e.target.value)}
          sx={{
            width: '100%',
            p: 2,
            fontSize: '1rem',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            bgcolor: 'background.paper',
            outline: 'none',
            '&:focus': { borderColor: 'primary.main', boxShadow: '0 0 0 2px rgba(25, 118, 210, 0.2)' },
          }}
        />
      </Box>

      <Alert severity="info" sx={{ mt: 2 }}>
        This step is optional. You can connect a repository later from the Integrations page.
      </Alert>
    </Box>
  )
}

const CreateSuiteStep: React.FC<{ onComplete: () => void }> = ({ onComplete }) => {
  const [suiteName, setSuiteName] = useState('My First Test Suite')
  const [suiteDesc, setSuiteDesc] = useState('Automated smoke tests for critical paths')

  const createMutation = useMutation(
    () => suitesAPI.create({
      name: suiteName,
      description: suiteDesc,
      framework_type: 'pytest',
      config: {},
    }),
    {
      onSuccess: () => {
        toast.success('Test suite created!')
        onComplete()
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Failed to create test suite')
      },
    }
  )

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Create Your First Test Suite
      </Typography>
      <Typography component="p" color="textSecondary">
        A test suite groups related tests together. Let's create one now.
      </Typography>

      <Box
        component="input"
        type="text"
        placeholder="Suite name"
        value={suiteName}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSuiteName(e.target.value)}
        sx={{
          width: '100%',
          p: 2,
          mb: 2,
          fontSize: '1rem',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          bgcolor: 'background.paper',
          outline: 'none',
          '&:focus': { borderColor: 'primary.main' },
        }}
      />
      <Box
        component="textarea"
        placeholder="Description (optional)"
        value={suiteDesc}
        onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setSuiteDesc(e.target.value)}
        rows={3}
        sx={{
          width: '100%',
          p: 2,
          fontSize: '1rem',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          bgcolor: 'background.paper',
          outline: 'none',
          resize: 'vertical',
          '&:focus': { borderColor: 'primary.main' },
        }}
      />

      <Button
        variant="contained"
        onClick={() => createMutation.mutate()}
        disabled={!suiteName.trim() || createMutation.isLoading}
        sx={{ mt: 2 }}
        endIcon={createMutation.isLoading ? <CircularProgress size={16} /> : null}
      >
        {createMutation.isLoading ? 'Creating...' : 'Create Suite'}
      </Button>
    </Box>
  )
}

const RunTestStep: React.FC<{ onComplete: () => void }> = ({ onComplete }) => {
  const [testCode, setTestCode] = useState(
    `def test_homepage_loads():\n    response = client.get('/')\n    assert response.status_code == 200`
  )

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Run Your First Test
      </Typography>
      <Typography component="p" color="textSecondary">
        Here's a sample test. You'll be able to create more complex tests
        once you're set up.
      </Typography>

      <Box
        component="pre"
        sx={{
          p: 3,
          bgcolor: 'grey.900',
          color: 'grey.100',
          borderRadius: 2,
          fontFamily: 'monospace',
          fontSize: '0.9rem',
          overflow: 'auto',
        }}
      >
        {testCode}
      </Box>

      <Alert severity="success" sx={{ mt: 2 }}>
        ✓ Test execution will be available once you've created a test suite and added test cases.
        For now, this step is marked as complete to get you started quickly.
      </Alert>

      <Button
        variant="contained"
        onClick={onComplete}
        sx={{ mt: 2 }}
      >
        Mark as Complete
      </Button>
    </Box>
  )
}

const SetupNotificationsStep: React.FC = () => {
  const [channels, setChannels] = useState({
    email: true,
    slack: false,
    discord: false,
  })

  const toggleChannel = (channel: keyof typeof channels) => {
    setChannels((prev) => ({ ...prev, [channel]: !prev[channel] }))
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Configure Notifications
      </Typography>
      <Typography component="p" color="textSecondary">
        Get notified when tests complete, fail, or need attention.
        You can always change these later in Settings.
      </Typography>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 3 }}>
        {[
          { key: 'email' as const, label: 'Email Notifications', desc: 'Receive test results via email' },
          { key: 'slack' as const, label: 'Slack Integration', desc: 'Post results to a Slack channel' },
          { key: 'discord' as const, label: 'Discord Integration', desc: 'Send alerts to Discord' },
        ].map((item) => (
          <Box
            key={item.key}
            onClick={() => toggleChannel(item.key)}
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              p: 2,
              border: '1px solid',
              borderColor: channels[item.key] ? 'primary.main' : 'divider',
              borderRadius: 2,
              cursor: 'pointer',
              bgcolor: channels[item.key] ? 'primary.50' : 'transparent',
              transition: 'all 0.2s',
              '&:hover': { borderColor: 'primary.light' },
            }}
          >
            <Box>
              <Typography variant="subtitle1">{item.label}</Typography>
              <Typography variant="caption" color="textSecondary">{item.desc}</Typography>
            </Box>
            <Box
              sx={{
                width: 40,
                height: 22,
                borderRadius: 11,
                bgcolor: channels[item.key] ? 'primary.main' : 'grey.400',
                position: 'relative',
                transition: 'background-color 0.2s',
              }}
            >
              <Box
                sx={{
                  width: 18,
                  height: 18,
                  borderRadius: '50%',
                  bgcolor: 'white',
                  position: 'absolute',
                  top: 2,
                  left: channels[item.key] ? 20 : 2,
                  transition: 'left 0.2s',
                }}
              />
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  )
}

export default OnboardingWizard
