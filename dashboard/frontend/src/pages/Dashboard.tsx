import { useQuery } from "react-query";
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  CircularProgress,
  Avatar,
  LinearProgress,
  Paper,
  Fade,
  Skeleton,
  IconButton,
  Tooltip as MuiTooltip,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  Folder,
  PlayArrow,
  CheckCircle,
  Error,
  Speed,
  Assessment,
  AutoGraph,
  Refresh,
  Schedule,
} from "@mui/icons-material";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler,
} from "chart.js";
import { Line, Bar, Doughnut } from "react-chartjs-2";
import { dashboardAPI } from "../api/client";
import { useState } from "react";
import TimeSavedCard from "../components/dashboard/TimeSavedCard";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler,
);

// Custom styled components
const StatCard = ({ title, value, icon, color, trend, trendValue }: any) => (
  <Card
    sx={{
      height: "100%",
      background: `linear-gradient(135deg, ${color}.light 0%, ${color}.main 100%)`,
      color: "white",
      position: "relative",
      overflow: "hidden",
      transition: "all 0.3s ease",
      "&:hover": {
        transform: "translateY(-4px)",
        boxShadow: "0 12px 20px -10px rgba(0,0,0,0.3)",
      },
      "&::before": {
        content: '""',
        position: "absolute",
        top: 0,
        right: 0,
        width: "100px",
        height: "100%",
        background:
          "linear-gradient(90deg, transparent, rgba(255,255,255,0.1))",
      },
    }}
  >
    <CardContent>
      <Box
        sx={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
        <Box>
          <Typography
            variant="overline"
            sx={{ opacity: 0.9, letterSpacing: 1 }}
          >
            {title}
          </Typography>
          <Typography variant="h3" sx={{ mt: 1, fontWeight: "bold" }}>
            {value}
          </Typography>
          {trend && (
            <Box sx={{ display: "flex", alignItems: "center", mt: 1 }}>
              {trend === "up" ? (
                <TrendingUp sx={{ fontSize: 16, mr: 0.5 }} />
              ) : (
                <TrendingDown sx={{ fontSize: 16, mr: 0.5 }} />
              )}
              <Typography variant="caption">{trendValue}</Typography>
            </Box>
          )}
        </Box>
        <Avatar
          sx={{
            bgcolor: "rgba(255,255,255,0.2)",
            width: 56,
            height: 56,
          }}
        >
          {icon}
        </Avatar>
      </Box>
    </CardContent>
  </Card>
);

const LoadingSkeleton = () => (
  <Box>
    <Grid container spacing={3} sx={{ mb: 3 }}>
      {[1, 2, 3, 4].map((i) => (
        <Grid size={{ xs: 12, sm: 6, md: 3 }} key={i}>
          <Skeleton
            variant="rectangular"
            height={140}
            sx={{ borderRadius: 2 }}
          />
        </Grid>
      ))}
    </Grid>
    <Skeleton
      variant="rectangular"
      height={400}
      sx={{ borderRadius: 2, mb: 3 }}
    />
  </Box>
);

export default function Dashboard() {
  const [refreshKey, setRefreshKey] = useState(0);

  const {
    data: stats,
    isLoading: statsLoading,
    refetch: refetchStats,
  } = useQuery(["dashboard-stats", refreshKey], () => dashboardAPI.getStats(), {
    refetchInterval: 30000,
  });

  const {
    data: trends,
    isLoading: trendsLoading,
    refetch: refetchTrends,
  } = useQuery(["dashboard-trends", refreshKey], () =>
    dashboardAPI.getTrends(30),
  );

  const {
    data: recent,
    isLoading: recentLoading,
    refetch: refetchRecent,
  } = useQuery(["dashboard-recent", refreshKey], () =>
    dashboardAPI.getRecentExecutions(10),
  );

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  if (statsLoading || trendsLoading || recentLoading) {
    return <LoadingSkeleton />;
  }

  const statsData = stats?.data;
  const trendsData = trends?.data || [];
  const recentData = recent?.data || [];

  // Enhanced chart options
  const lineChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        labels: {
          usePointStyle: true,
          padding: 20,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: {
          color: "rgba(0, 0, 0, 0.05)",
        },
      },
      x: {
        grid: {
          display: false,
        },
      },
    },
    interaction: {
      intersect: false,
      mode: "index" as const,
    },
  };

  const lineChartData = {
    labels: trendsData.map((t: any) => t.date),
    datasets: [
      {
        label: "Total Executions",
        data: trendsData.map((t: any) => t.total),
        borderColor: "rgb(99, 102, 241)",
        backgroundColor: "rgba(99, 102, 241, 0.1)",
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
      {
        label: "Passed",
        data: trendsData.map((t: any) => t.passed),
        borderColor: "rgb(34, 197, 94)",
        backgroundColor: "rgba(34, 197, 94, 0.1)",
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
      {
        label: "Failed",
        data: trendsData.map((t: any) => t.failed),
        borderColor: "rgb(239, 68, 68)",
        backgroundColor: "rgba(239, 68, 68, 0.1)",
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "bottom" as const,
        labels: {
          usePointStyle: true,
          padding: 15,
        },
      },
    },
    cutout: "65%",
  };

  const testTypeData = {
    labels: ["API Tests", "UI Tests", "Database", "Security", "Performance"],
    datasets: [
      {
        data: [12, 19, 3, 5, 2],
        backgroundColor: [
          "rgba(99, 102, 241, 0.9)",
          "rgba(34, 197, 94, 0.9)",
          "rgba(251, 146, 60, 0.9)",
          "rgba(239, 68, 68, 0.9)",
          "rgba(139, 92, 246, 0.9)",
        ],
        borderWidth: 0,
        hoverOffset: 10,
      },
    ],
  };

  const successRate = statsData?.success_rate || 0;

  return (
    <Fade in timeout={500}>
      <Box>
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 3,
          }}
        >
          <Box>
            <Typography variant="h4" sx={{ fontWeight: "bold" }} gutterBottom>
              Dashboard
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Welcome back! Here's your testing overview.
            </Typography>
          </Box>
          <MuiTooltip title="Refresh Data">
            <IconButton onClick={handleRefresh} color="primary">
              <Refresh />
            </IconButton>
          </MuiTooltip>
        </Box>

        {/* Stats Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard
              title="Total Executions"
              value={statsData?.total_executions || 0}
              icon={<PlayArrow sx={{ fontSize: 28 }} />}
              color="primary"
              trend="up"
              trendValue="+12% from last week"
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard
              title="Test Suites"
              value={statsData?.total_test_suites || 0}
              icon={<Folder sx={{ fontSize: 28 }} />}
              color="secondary"
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard
              title="Success Rate"
              value={`${successRate}%`}
              icon={
                successRate >= 80 ? (
                  <CheckCircle sx={{ fontSize: 28 }} />
                ) : (
                  <Error sx={{ fontSize: 28 }} />
                )
              }
              color={successRate >= 80 ? "success" : "warning"}
              trend={successRate >= 80 ? "up" : "down"}
              trendValue={successRate >= 80 ? "Great!" : "Needs attention"}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <TimeSavedCard
              executions={recentData}
              totalTests={statsData?.total_tests}
            />
          </Grid>
        </Grid>

        {/* Charts Row */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid size={{ xs: 12, md: 8 }}>
            <Card sx={{ height: "100%", boxShadow: 3 }}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                  <AutoGraph sx={{ mr: 1, color: "primary.main" }} />
                  <Typography variant="h6" sx={{ fontWeight: "medium" }}>
                    Execution Trends
                  </Typography>
                </Box>
                <Box sx={{ height: 300 }}>
                  <Line data={lineChartData} options={lineChartOptions} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, md: 4 }}>
            <Card sx={{ height: "100%", boxShadow: 3 }}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                  <Assessment sx={{ mr: 1, color: "secondary.main" }} />
                  <Typography variant="h6" sx={{ fontWeight: "medium" }}>
                    Test Types
                  </Typography>
                </Box>
                <Box
                  sx={{
                    height: 300,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Doughnut data={testTypeData} options={doughnutOptions} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Recent Executions */}
        <Card sx={{ boxShadow: 3 }}>
          <CardContent>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                mb: 3,
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <Schedule sx={{ mr: 1, color: "info.main" }} />
                <Typography variant="h6" sx={{ fontWeight: "medium" }}>
                  Recent Executions
                </Typography>
              </Box>
              <Chip label={`${recentData.length} total`} size="small" />
            </Box>

            {recentData.length === 0 ? (
              <Box sx={{ py: 4, textAlign: "center" }}>
                <Typography color="textSecondary">
                  No recent executions. Run some tests to see them here!
                </Typography>
              </Box>
            ) : (
              recentData.map((execution: any, index: number) => (
                <Fade in timeout={300 * (index + 1)} key={execution.id}>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      mb: 1,
                      bgcolor: "grey.50",
                      borderRadius: 2,
                      transition: "all 0.2s",
                      "&:hover": {
                        bgcolor: "grey.100",
                        transform: "translateX(4px)",
                      },
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <Box>
                        <Typography
                          variant="subtitle1"
                          sx={{ fontWeight: "medium" }}
                        >
                          {execution.suite_name || `Execution #${execution.id}`}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          {execution.environment || "production"} •{" "}
                          {execution.started_at || "Recently"}
                        </Typography>
                      </Box>
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        {execution.total_tests > 0 && (
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                              mr: 1,
                            }}
                          >
                            <LinearProgress
                              variant="determinate"
                              value={
                                (execution.passed / execution.total_tests) * 100
                              }
                              sx={{ width: 60, height: 6, borderRadius: 3 }}
                              color="success"
                            />
                            <Typography
                              variant="caption"
                              sx={{ fontWeight: "medium" }}
                            >
                              {execution.passed}/{execution.total_tests}
                            </Typography>
                          </Box>
                        )}
                        <Chip
                          size="small"
                          label={execution.status || "completed"}
                          color={
                            execution.status === "completed"
                              ? "success"
                              : execution.status === "running"
                                ? "primary"
                                : "error"
                          }
                          sx={{ fontWeight: "medium" }}
                        />
                      </Box>
                    </Box>
                  </Paper>
                </Fade>
              ))
            )}
          </CardContent>
        </Card>
      </Box>
    </Fade>
  );
}
