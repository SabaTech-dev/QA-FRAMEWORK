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
import { healingAPI } from '../api/client';

interface Selector {
  id: number | string;
  value: string;
  selector_type: string;
  description?: string;
  confidence_score: number;
  confidence_level: string;
  is_active: boolean;
  usage_count: number;
  success_rate: number;
}

interface HealingSession {
  id: number | string;
  status: string;
  total_selectors: number;
  successful_heals: number;
  failed_heals: number;
  success_rate: number;
  average_confidence: number;
  started_at: string;
  completed_at?: string;
}

interface HealingResult {
  id: number | string;
  original_selector_value: string;
  healed_selector_value?: string;
  status: string;
  confidence_score: number;
  confidence_level: string;
  healing_time_ms: number;
  attempts: number;
  created_at: string;
}

const SelfHealingDashboard: React.FC = () => {
  const [selectors, setSelectors] = useState<Selector[]>([]);
  const [sessions, setSessions] = useState<HealingSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [healDialogOpen, setHealDialogOpen] = useState(false);
  const [healing, setHealing] = useState(false);
  const [selectedSelector, setSelectedSelector] = useState<Selector | null>(null);
  const [healResults, setHealResults] = useState<HealingResult[]>([]);
  const [stats, setStats] = useState({
    totalSelectors: 0,
    lowConfidence: 0,
    avgConfidence: 0,
    healSuccessRate: 0,
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [selectorsRes, sessionsRes] = await Promise.all([
        healingAPI.getSelectors(),
        healingAPI.getSessions(),
      ]);

      const selectorsData: Selector[] = selectorsRes.data || [];
      const sessionsData: HealingSession[] = sessionsRes.data || [];

      setSelectors(selectorsData);
      setSessions(sessionsData);

      const lowConf = selectorsData.filter(s => s.confidence_score < 0.5).length;
      const avgConf = selectorsData.length > 0
        ? selectorsData.reduce((sum, s) => sum + s.confidence_score, 0) / selectorsData.length
        : 0;

      setStats({
        totalSelectors: selectorsData.length,
        lowConfidence: lowConf,
        avgConfidence: avgConf,
        healSuccessRate: sessionsData.length > 0
          ? sessionsData.reduce((sum, s) => sum + s.success_rate, 0) / sessionsData.length
          : 0,
      });
    } catch (err: any) {
      console.error('Error fetching healing data:', err);
      setError(err.response?.data?.detail || 'Failed to load healing data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleHealSelector = async (selector: Selector) => {
    setSelectedSelector(selector);
    setHealDialogOpen(true);
    setHealing(true);
    setHealResults([]);

    try {
      const response = await healingAPI.healSelector(Number(selector.id));
      const result: HealingResult = response.data;
      setHealResults([result]);
    } catch (err: any) {
      console.error('Healing failed:', err);
      setError(err.response?.data?.detail || 'Healing failed. Please try again.');
    } finally {
      setHealing(false);
    }
  };

  const getConfidenceColor = (level: string) => {
    switch (level) {
      case 'high': return 'success';
      case 'medium': return 'warning';
      case 'low': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircleIcon color="success" />;
      case 'failed': return <WarningIcon color="error" />;
      case 'partial': return <TrendingUpIcon color="warning" />;
      default: return <HistoryIcon color="action" />;
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
      </Box>
    );
  }

  // Show empty state if no selectors
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
          actionLabel="Learn More"
          onAction={() => {
            window.open('https://docs.example.com/self-healing', '_blank');
          }}
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
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
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
              <Typography variant="h4">{stats.totalSelectors}</Typography>
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
                {stats.lowConfidence}
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
                {(stats.avgConfidence * 100).toFixed(1)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={stats.avgConfidence * 100}
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
      {stats.lowConfidence > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {stats.lowConfidence} selector(s) have low confidence and may need healing
        </Alert>
      )}

      {/* Selectors Table */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
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
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <HistoryIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
              <Typography color="textSecondary">
                No healing sessions yet. Run a heal operation to see results here.
              </Typography>
            </Box>
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
                          {session.id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getStatusIcon(session.status)}
                          <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                            {session.status}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>{session.total_selectors}</TableCell>
                      <TableCell>{session.successful_heals}</TableCell>
                      <TableCell>{session.failed_heals}</TableCell>
                      <TableCell>
                        {(session.success_rate * 100).toFixed(1)}%
                      </TableCell>
                      <TableCell>
                        {(session.average_confidence * 100).toFixed(1)}%
                      </TableCell>
                      <TableCell>
                        {new Date(session.started_at).toLocaleString()}
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
      <Dialog open={healDialogOpen} onClose={() => setHealDialogOpen(false)} maxWidth="md">
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

              {healing ? (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <LinearProgress sx={{ flex: 1 }} />
                  <Typography>Analyzing selector...</Typography>
                </Box>
              ) : healResults.length > 0 ? (
                <Box>
                  <Alert severity={healResults[0].status === 'success' ? 'success' : 'info'} sx={{ mb: 2 }}>
                    Healing {healResults[0].status === 'success' ? 'completed successfully' : 'skipped (confidence OK)'}
                  </Alert>

                  {healResults[0].healed_selector_value && (
                    <Box>
                      <Typography variant="body2" color="textSecondary">
                        Healed Selector:
                      </Typography>
                      <Typography variant="body1" sx={{ fontFamily: 'monospace', color: 'success.main' }}>
                        {healResults[0].healed_selector_value}
                      </Typography>
                    </Box>
                  )}

                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2">
                      Confidence: {(healResults[0].confidence_score * 100).toFixed(1)}%
                    </Typography>
                    <Typography variant="body2">
                      Healing Time: {healResults[0].healing_time_ms}ms
                    </Typography>
                    <Typography variant="body2">
                      Attempts: {healResults[0].attempts}
                    </Typography>
                  </Box>
                </Box>
              ) : (
                <Typography color="textSecondary">No results available.</Typography>
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
