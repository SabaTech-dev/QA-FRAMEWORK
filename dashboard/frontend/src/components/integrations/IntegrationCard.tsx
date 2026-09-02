import { useState } from 'react'
import {
  Card,
  CardContent,
  CardActions,
  CardHeader,
  Typography,
  Box,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  Divider,
  Avatar,
  Stack,
  useTheme,
} from '@mui/material'
import { 
  Settings as SettingsIcon,
  CheckCircle,
  Error as ErrorIcon,
  Link as LinkIcon,
  Cloud,
  Business,
  Bolt,
  Close,
} from '@mui/icons-material'
import { Provider, IntegrationConfig } from '../../api/integrations'
import useAuthStore from '../../stores/authStore'

interface IntegrationCardProps {
  provider: Provider
  onConfigure: (provider: Provider) => void
  onTest: (providerId: string) => void
}

export default function IntegrationCard({ provider, onConfigure, onTest }: IntegrationCardProps) {
  const theme = useTheme()
  const [openDialog, setOpenDialog] = useState(false)
  const [config, setConfig] = useState<IntegrationConfig>(provider.config || { enabled: false })
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const { token } = useAuthStore()

  const getStatusColor = () => {
    switch (provider.status) {
      case 'connected':
        return 'success'
      case 'disconnected':
        return 'default'
      case 'error':
        return 'error'
      default:
        return 'default'
    }
  }

  const getProviderIcon = () => {
    switch (provider.name.toLowerCase()) {
      case 'jira':
        return <Avatar sx={{ bgcolor: '#0052CC' }}>🔵</Avatar>
      case 'azure devops':
        return <Avatar sx={{ bgcolor: '#0089D6' }}>☁️</Avatar>
      case 'alm':
        return <Avatar sx={{ bgcolor: '#4285F4' }}>🏢</Avatar>
      case 'testlink':
        return <Avatar sx={{ bgcolor: '#FF6B6B' }}>🔗</Avatar>
      case 'zephyr':
        return <Avatar sx={{ bgcolor: '#FFB300' }}>⚡</Avatar>
      default:
        return <Avatar>{provider.icon}</Avatar>
    }
  }

  const handleOpenDialog = () => {
    setConfig(provider.config || { enabled: false })
    setOpenDialog(true)
    setTestResult(null)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setTestResult(null)
  }

  const handleSaveConfig = async () => {
    try {
      // This would typically call an API endpoint
      // For now, we'll just close the dialog
      onConfigure(provider)
      handleCloseDialog()
    } catch (error) {
      console.error('Failed to save configuration:', error)
    }
  }

  const handleTestConnection = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      // This would call the testConnection API endpoint
      // Simulating a test for now
      await new Promise((resolve) => setTimeout(resolve, 1000))
      setTestResult({
        success: true,
        message: 'Connection successful!',
      })
    } catch {
      setTestResult({
        success: false,
        message: 'Connection failed. Please check your credentials.',
      })
    } finally {
      setTesting(false)
    }
  }

  const handleSync = async () => {
    try {
      // This would call the sync API endpoint
      await new Promise((resolve) => setTimeout(resolve, 1000))
      alert('Sync completed successfully!')
    } catch {
      alert('Sync failed. Please try again.')
    }
  }

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.3s',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: theme.shadows[8],
        },
      }}
    >
      <CardHeader
        avatar={getProviderIcon()}
        title={
          <Typography variant="h6" component="div">
            {provider.name}
          </Typography>
        }
        subheader={provider.description}
        action={
          <Chip
            label={provider.status === 'connected' ? 'Connected' : provider.status === 'error' ? 'Error' : 'Disconnected'}
            color={getStatusColor()}
            size="small"
            icon={provider.status === 'connected' ? <CheckCircle fontSize="small" /> : provider.status === 'error' ? <ErrorIcon fontSize="small" /> : <LinkIcon fontSize="small" />}
          />
        }
      />
      <Divider />
      <CardContent sx={{ flexGrow: 1 }}>
        <Typography variant="body2" color="text.secondary" component="p">
          Configure this integration to connect with {provider.name} and enable automated test sync.
        </Typography>

        {testResult && (
          <Alert severity={testResult.success ? 'success' : 'error'} sx={{ mb: 2 }}>
            {testResult.message}
          </Alert>
        )}

        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Button
            variant="contained"
            size="small"
            startIcon={testing ? <CircularProgress size={16} color="inherit" /> : <CheckCircle fontSize="small" />}
            onClick={handleTestConnection}
            disabled={testing || !token}
          >
            Test Connection
          </Button>
          <Button
            variant="outlined"
            size="small"
            startIcon={<Bolt fontSize="small" />}
            onClick={handleSync}
            disabled={provider.status !== 'connected'}
          >
            Sync
          </Button>
        </Box>
      </CardContent>
      <CardActions sx={{ p: 2, pt: 0 }}>
        <Button
          variant="contained"
          color="primary"
          size="small"
          startIcon={<SettingsIcon />}
          onClick={handleOpenDialog}
          fullWidth
        >
          Configure
        </Button>
      </CardActions>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {getProviderIcon()}
            <Typography variant="h6">{provider.name} - Configuration</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 3 }}>
            Configure your {provider.name} integration settings.
          </DialogContentText>

          <TextField
            label="API Key"
            type="password"
            fullWidth
            value={config.api_key || ''}
            onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
            sx={{ mb: 2 }}
            helperText="Enter your API key for {provider.name}"
          />

          <TextField
            label="API URL"
            fullWidth
            value={config.api_url || ''}
            onChange={(e) => setConfig({ ...config, api_url: e.target.value })}
            sx={{ mb: 2 }}
            helperText="Enter your API URL (optional)"
          />

          <TextField
            label="Project ID"
            fullWidth
            value={config.project_id || ''}
            onChange={(e) => setConfig({ ...config, project_id: e.target.value })}
            sx={{ mb: 2 }}
            helperText="Enter your project ID (optional)"
          />

          <Box sx={{ mt: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
            <Typography variant="body2">Status:</Typography>
            <Chip
              label={config.enabled ? 'Enabled' : 'Disabled'}
              color={config.enabled ? 'success' : 'default'}
              size="small"
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2, pt: 0 }}>
          <Button onClick={handleCloseDialog} color="inherit">
            Cancel
          </Button>
          <Button onClick={handleSaveConfig} variant="contained" disabled={!token}>
            Save Configuration
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  )
}
