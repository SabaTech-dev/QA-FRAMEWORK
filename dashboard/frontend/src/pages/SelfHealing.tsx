import React, { useState, useEffect, useCallback } from 'react';
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
  Chip,
  Paper,
  Grid,
  LinearProgress,
  Alert,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  AutoFixHigh as AutoFixHighIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  History as HistoryIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import EmptyState from '../components/common/EmptyState';
import {
  healingAPI,
  type HealingSelector,
  type HealingSession,
  type HealingResult,
} from '../api/client';

const SelfHealingDashboard: React.FC = () => {
  const [selectors, setSelectors] = useState<HealingSelector[]>([]);
  const [sessions, setSessions] = useState<HealingSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [healDialogOpen, setHealDialogOpen] = useState(false);
  const [selectedSelector, setSelectedSelector] = useState<HealingSelector | null>(null);
  const [healing, setHealing] = useState(false);
  const [healResult, setHealResult] = useState<HealingResult | null>(null);
  const [healError, setHealError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [selectorsRes, sessionsRes] = await Promise.all([
        healingAPI.getSelectors(),
        healingAPI.getSessions(),
      ]);
      setSelectors(selectorsRes.data ?? []);
      setSessions(sessionsRes.data ?? []);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to load self-healing data';
      setError(typeof msg === 'string' ? msg : 'Failed to load self-healing data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleHealSelector = useCallback(async (selector: HealingSelector) => {
    setSelectedSelector(selector);
    setHealResult(null);
    setHealError(null);
    setHealing(true);
    setHealDialogOpen(true);
    try {
      const { data } = await healingAPI.healSelector(selector.id);
      setHealResult(data);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Healing request failed';
      setHealError(typeof msg === 'string' ? msg : 'Healing request failed');
    } finally {
      setHealing(false);
    }
  }, []);

  // Derived stats computed from live data.
  const stats = React.useMemo(() => {
    const total = selectors.length;
    const lowConf = selectors.filter((s) => s.confidence_score < 0.5).length;
    const avgConf =
      total > 0
        ? selectors.reduce((sum, s) => sum + (s.confidence_score || 0), 0) / total
        : 0;
    const healSuccessRate =
      sessions.length > 0
        ? sessions.reduce((sum, s) => sum + (s.success_rate || 0), 0) / sessions.length
        : 0;
    return { total, lowConf, avgConf, healSuccessRate };
  }, [selectors, sessions]);

  const getConfidenceColor = (level: string) => {
    switch (level) {
      case 'high':
        return 'success';
      case 'medium':
        return 'warning';
      case 'low':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon color="success" />;
      case 'failed':
        return <WarningIcon color="error" />;
      case 'partial':
        return <TrendingUpIcon color="warning" />;
      default:
        return <HistoryIcon color="action" />;
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
      </Box>
    );
  }

  // Show empty state if no selectors and no error.
  if (selectors.length === 0 && !error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          <AutoFixHighIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Self-Healing Dashboard
        </Typography>
        <EmptyState
          illustration="/illustrations/empty-selectors.svg"
          title="No Selectors Found"
          description="Self-healing selectors will appear here after your tests run. The system automatically detects and heals flaky selectors to improve test stability."
          actionLabel="Refresh"
          onAction={fetchData}
        />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        <AutoFixHighIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Self-Healing Dashboard
      </Typography>

      {error && (
        <Alert
          severity="error"
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small" onClick={fetchData}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Selectors
              </Typography>
              <Typography variant="h4">{stats.total}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Low Confidence
              </Typography>
              <Typography variant="h4" color="error.main">
                {stats.lowConf}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Avg Confidence
              </Typography>
              <Typography variant="h4">
                {(stats.avgConf * 100).toFixed(1)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={stats.avgConf * 100}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Heal Success Rate
              </Typography>
              <Typography variant="h4" color="success.main">
                {(stats.healSuccessRate * 100).toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Low Confidence Alert */}
      {stats.lowConf > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {stats.lowConf} selector(s) have low confidence and may need healing
        </Alert>
      )}

      {/* Selectors Table */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              mb: 2,
            }}
          >
            <Typography variant="h6">Selectors</Typography>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={fetchData}
            >
              Refresh
            </Button>
          </Box>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Selector</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Confidence</TableCell>
                  <TableCell>Usage</TableCell>
                  <TableCell>Success Rate</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {selectors.map((selector) => (
                  <TableRow key={selector.id}>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {selector.value}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={selector.selector_type} size="small" />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={selector.confidence_score * 100}
                          sx={{ width: 60 }}
                          color={getConfidenceColor(selector.confidence_level) as any}
                        />
                        <Typography variant="body2">
                          {(selector.confidence_score * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>{selector.usage_count}</TableCell>
                    <TableCell>
                      {(selector.success_rate * 100).toFixed(1)}%
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Heal Selector">
                        <IconButton
                          size="small"
                          onClick={() => handleHealSelector(selector)}
                          color="primary"
                        >
                          <AutoFixHighIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Healing Sessions */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Healing Sessions
          </Typography>
          {sessions.length === 0 ? (
            <Typography variant="body2" color="textSecondary" sx={{ py: 2 }}>
              No healing sessions yet. Run a heal action to see results here.
            </Typography>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Session ID</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Selectors</TableCell>
                    <TableCell>Healed</TableCell>
                    <TableCell>Failed</TableCell>
                    <TableCell>Success Rate</TableCell>
                    <TableCell>Avg Confidence</TableCell>
                    <TableCell>Started</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sessions.map((session) => (
                    <TableRow key={session.id}>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          #{session.id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getStatusIcon(session.status)}
                          <Typography
                            variant="body2"
                            sx={{ textTransform: 'capitalize' }}
                          >
                            {session.status}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>{session.total_selectors}</TableCell>
                      <TableCell>{session.successful_heals}</TableCell>
                      <TableCell>{session.failed_heals}</TableCell>
                      <TableCell>{(session.success_rate * 100).toFixed(1)}%</TableCell>
                      <TableCell>
                        {(session.average_confidence * 100).toFixed(1)}%
                      </TableCell>
                      <TableCell>
                        {session.started_at
                          ? new Date(session.started_at).toLocaleString()
                          : '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Heal Dialog */}
      <Dialog
        open={healDialogOpen}
        onClose={() => setHealDialogOpen(false)}
        maxWidth="md"
      >
        <DialogTitle>Heal Selector</DialogTitle>
        <DialogContent>
          {selectedSelector && (
            <Box sx={{ pt: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Original Selector:
              </Typography>
              <Typography variant="body1" sx={{ fontFamily: 'monospace', mb: 2 }}>
                {selectedSelector.value}
              </Typography>

              {healing && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <LinearProgress sx={{ flex: 1 }} />
                  <Typography>Analyzing selector...</Typography>
                </Box>
              )}

              {healError && !healing && (
                <Alert severity="error" sx={{ mb: 2 }} icon={<ErrorIcon />}>
                  {healError}
                </Alert>
              )}

              {healResult && !healing && (
                <Box>
                  <Alert
                    severity={healResult.status === 'success' ? 'success' : 'info'}
                    sx={{ mb: 2 }}
                  >
                    Healing{' '}
                    {healResult.status === 'success'
                      ? 'completed successfully'
                      : 'skipped (confidence OK)'}
                  </Alert>

                  {healResult.healed_selector_value && (
                    <Box>
                      <Typography variant="body2" color="textSecondary">
                        Healed Selector:
                      </Typography>
                      <Typography
                        variant="body1"
                        sx={{ fontFamily: 'monospace', color: 'success.main' }}
                      >
                        {healResult.healed_selector_value}
                      </Typography>
                    </Box>
                  )}

                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2">
                      Confidence: {(healResult.confidence_score * 100).toFixed(1)}%
                    </Typography>
                    <Typography variant="body2">
                      Healing Time: {healResult.healing_time_ms}ms
                    </Typography>
                    <Typography variant="body2">
                      Attempts: {healResult.attempts}
                    </Typography>
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHealDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SelfHealingDashboard;
