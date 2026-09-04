import { useQuery } from "react-query";
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  useTheme,
  alpha,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  People,
  AttachMoney,
  Assessment,
  Speed,
} from "@mui/icons-material";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  ArcElement,
  Filler,
} from "chart.js";
import { Line, Bar, Doughnut } from "react-chartjs-2";
import { analyticsAPI } from "../api/client";
import {
  CardSkeleton,
  ChartSkeleton,
} from "../components/common/SkeletonLoader";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  ChartTooltip,
  Legend,
  ArcElement,
  Filler,
);

interface KPICardProps {
  title: string;
  value: string | number;
  trend?: number;
  icon: React.ReactNode;
  color: string;
}

function KPICard({ title, value, trend, icon, color }: KPICardProps) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <Box>
            <Typography color="textSecondary" variant="body2" gutterBottom>
              {title}
            </Typography>
            <Typography
              variant="h4"
              component="div"
              sx={{ fontWeight: "bold", color }}
            >
              {value}
            </Typography>
            {trend !== undefined && (
              <Box sx={{ display: "flex", alignItems: "center", mt: 1 }}>
                {trend >= 0 ? (
                  <>
                    <TrendingUp sx={{ color: "success.main", fontSize: 20 }} />
                    <Typography
                      variant="body2"
                      color="success.main"
                      sx={{ ml: 0.5 }}
                    >
                      +{trend}%
                    </Typography>
                  </>
                ) : (
                  <>
                    <TrendingDown sx={{ color: "error.main", fontSize: 20 }} />
                    <Typography
                      variant="body2"
                      color="error.main"
                      sx={{ ml: 0.5 }}
                    >
                      {trend}%
                    </Typography>
                  </>
                )}
              </Box>
            )}
          </Box>
          <Box
            sx={{
              backgroundColor: alpha(color, 0.1),
              borderRadius: "50%",
              padding: 1.5,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function Analytics() {
  const theme = useTheme();

  const { isLoading: dashboardLoading } = useQuery("analytics-dashboard", () =>
    analyticsAPI.getDashboard(),
  );

  const { data: users, isLoading: usersLoading } = useQuery(
    "analytics-users",
    () => analyticsAPI.getUsers(),
  );

  const { data: tests, isLoading: testsLoading } = useQuery(
    "analytics-tests",
    () => analyticsAPI.getTests(),
  );

  const { data: revenue, isLoading: revenueLoading } = useQuery(
    "analytics-revenue",
    () => analyticsAPI.getRevenue(),
  );

  const { data: features, isLoading: featuresLoading } = useQuery(
    "analytics-features",
    () => analyticsAPI.getFeatures(),
  );

  if (
    dashboardLoading ||
    usersLoading ||
    testsLoading ||
    revenueLoading ||
    featuresLoading
  ) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          Analytics Dashboard
        </Typography>
        <Grid container spacing={3} sx={{ mb: 3 }}>
          {[1, 2, 3, 4].map((i) => (
            <Grid size={{ xs: 12, sm: 6, md: 3 }} key={i}>
              <CardSkeleton />
            </Grid>
          ))}
        </Grid>
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 8 }}>
            <ChartSkeleton height={350} />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <ChartSkeleton height={350} />
          </Grid>
        </Grid>
      </Box>
    );
  }

  const usersData = users?.data?.data || {};
  const testsData = tests?.data?.data || {};
  const revenueData = revenue?.data?.data || {};
  const featuresData: Record<string, { usage_count?: number }> =
    features?.data?.data || {};

  // KPI Metrics
  const totalTests = testsData.total_executions || 0;
  const successRate = testsData.success_rate || 0;
  const activeUsers = usersData.active_users || 0;
  const mrr = revenueData.mrr || 0;
  const userTrend =
    usersData.signup_trend?.length > 0
      ? ((usersData.signup_trend[usersData.signup_trend.length - 1]?.count ||
          0) /
          (usersData.signup_trend[0]?.count || 1)) *
          100 -
        100
      : 0;

  // Line Chart - Tests Trend
  const testsTrendData = {
    labels: testsData.trend?.map((t: any) => t.date) || [],
    datasets: [
      {
        label: "Tests Executed",
        data: testsData.trend?.map((t: any) => t.total) || [],
        borderColor: theme.palette.primary.main,
        backgroundColor: alpha(theme.palette.primary.main, 0.1),
        tension: 0.4,
        fill: true,
      },
    ],
  };

  // Pie Chart - Feature Usage
  const featureUsageData = {
    labels: ["Self-Healing", "AI Generation", "Flaky Detection", "Basic"],
    datasets: [
      {
        data: [
          featuresData.self_healing?.usage_count || 0,
          featuresData.ai_generation?.usage_count || 0,
          featuresData.flaky_detection?.usage_count || 0,
          featuresData.basic?.usage_count || 0,
        ],
        backgroundColor: [
          theme.palette.primary.main,
          theme.palette.secondary.main,
          theme.palette.success.main,
          theme.palette.grey[400],
        ],
      },
    ],
  };

  // Bar Chart - Signups by Day
  const signupsData = {
    labels: usersData.signup_trend?.map((t: any) => t.date) || [],
    datasets: [
      {
        label: "New Signups",
        data: usersData.signup_trend?.map((t: any) => t.count) || [],
        backgroundColor: theme.palette.primary.main,
      },
    ],
  };

  // Area Chart - Revenue Trend
  const revenueTrendData = {
    labels: revenueData.trend?.map((t: any) => t.month) || [],
    datasets: [
      {
        label: "Revenue ($)",
        data: revenueData.trend?.map((t: any) => t.revenue) || [],
        borderColor: theme.palette.success.main,
        backgroundColor: alpha(theme.palette.success.main, 0.1),
        tension: 0.4,
        fill: true,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: "top" as const,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 3, fontWeight: "bold" }}>
        Business Analytics
      </Typography>

      {/* KPI Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Total Tests"
            value={totalTests.toLocaleString()}
            trend={12}
            icon={
              <Assessment
                sx={{ color: theme.palette.primary.main, fontSize: 30 }}
              />
            }
            color={theme.palette.primary.main}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Success Rate"
            value={`${successRate.toFixed(1)}%`}
            trend={5.2}
            icon={
              <Speed sx={{ color: theme.palette.success.main, fontSize: 30 }} />
            }
            color={theme.palette.success.main}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Active Users"
            value={activeUsers.toLocaleString()}
            trend={userTrend}
            icon={
              <People
                sx={{ color: theme.palette.secondary.main, fontSize: 30 }}
              />
            }
            color={theme.palette.secondary.main}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="MRR"
            value={`$${mrr.toLocaleString()}`}
            trend={8.5}
            icon={
              <AttachMoney
                sx={{ color: theme.palette.warning.main, fontSize: 30 }}
              />
            }
            color={theme.palette.warning.main}
          />
        </Grid>
      </Grid>

      {/* Charts Row 1 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 8 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Tests Executed (Last 30 Days)
              </Typography>
              <Box sx={{ height: 300 }}>
                <Line data={testsTrendData} options={chartOptions} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Feature Usage Distribution
              </Typography>
              <Box
                sx={{
                  height: 300,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Doughnut
                  data={featureUsageData}
                  options={{ responsive: true, maintainAspectRatio: false }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts Row 2 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                User Signups (Last 30 Days)
              </Typography>
              <Box sx={{ height: 300 }}>
                <Bar data={signupsData} options={chartOptions} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Revenue Trend (Last 12 Months)
              </Typography>
              <Box sx={{ height: 300 }}>
                <Line data={revenueTrendData} options={chartOptions} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tables */}
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Top Features by Usage
              </Typography>
              <TableContainer component={Paper} elevation={0}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Feature</TableCell>
                      <TableCell align="right">Uses</TableCell>
                      <TableCell align="right">% of Total</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(featuresData)
                      .filter(([_, value]: [string, any]) => value.usage_count)
                      .sort(
                        (a: any, b: any) => b[1].usage_count - a[1].usage_count,
                      )
                      .slice(0, 5)
                      .map(([feature, data]: [string, any]) => {
                        const total = Object.values(featuresData).reduce(
                          (sum: number, val: any) =>
                            sum + ((val.usage_count || 0) as number),
                          0,
                        );
                        return (
                          <TableRow key={feature}>
                            <TableCell component="th" scope="row">
                              {feature
                                .replace(/_/g, " ")
                                .replace(/\b\w/g, (l) => l.toUpperCase())}
                            </TableCell>
                            <TableCell align="right">
                              {(data.usage_count as number).toLocaleString()}
                            </TableCell>
                            <TableCell align="right">
                              {total > 0
                                ? (
                                    ((data.usage_count as number) / total) *
                                    100
                                  ).toFixed(1)
                                : "0"}
                              %
                            </TableCell>
                          </TableRow>
                        );
                      })}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Signups
              </Typography>
              <TableContainer component={Paper} elevation={0}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Email</TableCell>
                      <TableCell>Date</TableCell>
                      <TableCell>Plan</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(usersData.recent_signups || [])
                      .slice(0, 5)
                      .map((user: any, index: number) => (
                        <TableRow key={index}>
                          <TableCell component="th" scope="row">
                            {user.email}
                          </TableCell>
                          <TableCell>
                            {new Date(user.date).toLocaleDateString()}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={user.plan || "Free"}
                              size="small"
                              color={
                                user.plan === "Enterprise"
                                  ? "primary"
                                  : "default"
                              }
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={user.status || "Active"}
                              size="small"
                              color={
                                user.status === "Active" ? "success" : "default"
                              }
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
