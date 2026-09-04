import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Button,
  Grid,
  Divider,
  LinearProgress,
} from "@mui/material";
import {
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Cancel as CancelIcon,
} from "@mui/icons-material";
import { format } from "date-fns";

interface Subscription {
  id: string;
  plan_id: string;
  plan_name: string;
  status: "active" | "past_due" | "canceled" | "incomplete" | "trialing";
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  features: {
    max_suites: number;
    max_cases: number;
    ai_healing: boolean;
    priority_support: boolean;
  };
  usage?: {
    suites_used: number;
    cases_used: number;
  };
}

interface SubscriptionStatusProps {
  subscription: Subscription | null;
  onCancel: () => void;
  onUpgrade: () => void;
  isLoading?: boolean;
}

const statusConfig: Record<
  string,
  { icon: typeof CheckCircleIcon; color: string; label: string }
> = {
  active: { icon: CheckCircleIcon, color: "success", label: "Active" },
  past_due: { icon: WarningIcon, color: "warning", label: "Past Due" },
  canceled: { icon: CancelIcon, color: "error", label: "Canceled" },
  incomplete: { icon: ErrorIcon, color: "error", label: "Incomplete" },
  trialing: { icon: CheckCircleIcon, color: "info", label: "Trialing" },
};

export default function SubscriptionStatus({
  subscription,
  onCancel,
  onUpgrade,
  isLoading,
}: SubscriptionStatusProps) {
  if (!subscription) {
    return (
      <Card>
        <CardContent>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Box>
              <Typography variant="h6">No Active Subscription</Typography>
              <Typography variant="body2" color="text.secondary">
                You are currently on the Free plan
              </Typography>
            </Box>
            <Button
              variant="contained"
              onClick={onUpgrade}
              disabled={isLoading}
            >
              Upgrade Plan
            </Button>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const StatusIcon = statusConfig[subscription.status]?.icon || ErrorIcon;
  const statusColor = statusConfig[subscription.status]?.color || "error";
  const statusLabel = statusConfig[subscription.status]?.label || "Unknown";

  const periodProgress = () => {
    if (!subscription.current_period_start || !subscription.current_period_end)
      return 0;
    const start = new Date(subscription.current_period_start).getTime();
    const end = new Date(subscription.current_period_end).getTime();
    const now = Date.now();
    return Math.min(100, Math.max(0, ((now - start) / (end - start)) * 100));
  };

  return (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 8 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
              <StatusIcon color={statusColor as any} sx={{ fontSize: 40 }} />
              <Box>
                <Typography variant="h5">{subscription.plan_name}</Typography>
                <Chip
                  label={statusLabel}
                  color={statusColor as any}
                  size="small"
                  sx={{ mt: 0.5 }}
                />
              </Box>
            </Box>

            <Typography variant="body2" color="text.secondary" gutterBottom>
              Current billing period
            </Typography>
            <Typography variant="body1">
              {format(
                new Date(subscription.current_period_start),
                "MMM d, yyyy",
              )}{" "}
              -{" "}
              {format(new Date(subscription.current_period_end), "MMM d, yyyy")}
            </Typography>

            <Box sx={{ mt: 2, mb: 1 }}>
              <LinearProgress
                variant="determinate"
                value={periodProgress()}
                sx={{ height: 6, borderRadius: 3 }}
              />
            </Box>

            {subscription.cancel_at_period_end && (
              <Box
                sx={{
                  mt: 2,
                  p: 2,
                  bgcolor: "warning.lighter",
                  borderRadius: 1,
                }}
              >
                <Typography variant="body2" color="warning.main">
                  Your subscription will be canceled at the end of the current
                  billing period
                </Typography>
              </Box>
            )}
          </Grid>

          <Grid size={{ xs: 12, md: 4 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Usage This Period
            </Typography>

            {subscription.usage && (
              <Box sx={{ mb: 2 }}>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 0.5,
                  }}
                >
                  <Typography variant="body2">Test Suites</Typography>
                  <Typography variant="body2">
                    {subscription.usage.suites_used}/
                    {subscription.features.max_suites}
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={
                    (subscription.usage.suites_used /
                      subscription.features.max_suites) *
                    100
                  }
                  sx={{ height: 6, borderRadius: 3, mb: 1 }}
                />

                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 0.5,
                  }}
                >
                  <Typography variant="body2">Test Cases</Typography>
                  <Typography variant="body2">
                    {subscription.usage.cases_used}/
                    {subscription.features.max_cases}
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={
                    (subscription.usage.cases_used /
                      subscription.features.max_cases) *
                    100
                  }
                  sx={{ height: 6, borderRadius: 3 }}
                />
              </Box>
            )}

            <Divider sx={{ my: 2 }} />

            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              <Button
                variant="outlined"
                size="small"
                onClick={onUpgrade}
                disabled={isLoading}
                fullWidth
              >
                Change Plan
              </Button>
              {!subscription.cancel_at_period_end && (
                <Button
                  variant="text"
                  size="small"
                  color="error"
                  onClick={onCancel}
                  disabled={isLoading}
                  fullWidth
                >
                  Cancel Subscription
                </Button>
              )}
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}
