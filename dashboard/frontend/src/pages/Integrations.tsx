import { useState, useEffect } from "react";
import {
  Container,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Button,
  Chip,
  Stack,
  useTheme,
} from "@mui/material";
import {
  Extension as ExtensionIcon,
  Sync as SyncIcon,
  Info as InfoIcon,
} from "@mui/icons-material";
import IntegrationCard from "../components/integrations/IntegrationCard";
import { Provider, integrationsAPI } from "../api/integrations";
import useAuthStore from "../stores/authStore";
import EmptyState from "../components/common/EmptyState";

export default function Integrations() {
  const theme = useTheme();
  const { token } = useAuthStore();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [configuring, setConfiguring] = useState<string | null>(null);

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await integrationsAPI.getProviders();
      setProviders(response.data);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          "Failed to load providers. Please try again.",
      );
      console.error("Error fetching providers:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleConfigure = async (provider: Provider) => {
    try {
      setConfiguring(provider.id);
      // In a real implementation, this would call an API to save the configuration
      console.log("Configuring provider:", provider);
      // await integrationsAPI.configure(provider.id, config)
    } catch (err: any) {
      console.error("Failed to configure provider:", err);
      setError(err.response?.data?.detail || "Failed to configure provider");
    } finally {
      setConfiguring(null);
    }
  };

  const handleTest = async (providerId: string) => {
    try {
      await integrationsAPI.testConnection(providerId);
      // Refresh providers after successful test
      await fetchProviders();
    } catch (err: any) {
      console.error("Failed to test connection:", err);
      setError(err.response?.data?.detail || "Failed to test connection");
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box
        sx={{
          backgroundColor: theme.palette.background.paper,
          borderBottom: `1px solid ${theme.palette.divider}`,
          padding: { xs: 2, md: 4 },
          mb: 4,
        }}
      >
        <Stack
          direction="row"
          sx={{ alignItems: "center", justifyContent: "space-between" }}
          spacing={2}
        >
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              Integrations
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Manage and configure your test automation integrations
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<SyncIcon />}
            onClick={fetchProviders}
            disabled={loading}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* Info Banner */}
      <Box sx={{ mb: 4 }}>
        <Alert
          icon={<InfoIcon />}
          severity="info"
          sx={{
            "& .MuiAlert-icon": {
              fontSize: "1.5rem",
            },
          }}
        >
          Connect your test automation tools to automatically sync test cases
          and execution results.
        </Alert>
      </Box>

      {/* Loading State */}
      {loading && (
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            minHeight: "400px",
          }}
        >
          <CircularProgress size={60} />
        </Box>
      )}

      {/* Error State */}
      {error && (
        <Box sx={{ mb: 4 }}>
          <Alert severity="error">
            {error}
            <Button size="small" onClick={() => setError(null)} sx={{ ml: 2 }}>
              Dismiss
            </Button>
          </Alert>
        </Box>
      )}

      {/* No Providers State - Using EmptyState */}
      {!loading && providers.length === 0 && (
        <EmptyState
          illustration="/illustrations/empty-tests.svg"
          title="No Integrations Configured"
          description="Connect your test management tools to automatically sync test cases and execution results. Popular integrations include Jira, Azure DevOps, and TestRail."
          actionLabel="Configure Integration"
          onAction={() => {
            // In a real implementation, this would open a dialog to select an integration
            alert("Integration configuration wizard coming soon!");
          }}
        />
      )}

      {/* Providers Grid */}
      {!loading && providers.length > 0 && (
        <Container maxWidth="xl">
          <Grid container spacing={3}>
            {providers.map((provider) => (
              <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={provider.id}>
                <IntegrationCard
                  provider={provider}
                  onConfigure={handleConfigure}
                  onTest={handleTest}
                />
              </Grid>
            ))}
          </Grid>
        </Container>
      )}
    </Box>
  );
}
