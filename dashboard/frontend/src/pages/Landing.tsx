import React from "react";
import {
  Container,
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Chip,
  useTheme,
  useMediaQuery,
} from "@mui/material";
import {
  AutoFixHigh as AutoFixIcon,
  Psychology as PsychologyIcon,
  BugReport as BugIcon,
  Devices as DevicesIcon,
  Check as CheckIcon,
  PlayArrow as PlayIcon,
} from "@mui/icons-material";
import DisclosureBanner from "../components/common/DisclosureBanner";

const Landing: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const features = [
    {
      icon: <AutoFixIcon sx={{ fontSize: 48, color: "primary.main" }} />,
      title: "AI Self-Healing Tests",
      description:
        "Automatically fix broken selectors with AI-powered healing. Reduce test maintenance by 70%.",
    },
    {
      icon: <PsychologyIcon sx={{ fontSize: 48, color: "primary.main" }} />,
      title: "AI Test Generation",
      description:
        "Generate comprehensive tests from requirements and UI. Create edge cases automatically.",
    },
    {
      icon: <BugIcon sx={{ fontSize: 48, color: "primary.main" }} />,
      title: "Flaky Test Detection",
      description:
        "Intelligent quarantine system detects and isolates flaky tests before they break your CI/CD.",
    },
    {
      icon: <DevicesIcon sx={{ fontSize: 48, color: "primary.main" }} />,
      title: "Multi-Framework Support",
      description:
        "Works with Playwright, Cypress, Selenium, and more. One platform, all your tests.",
    },
  ];

  const pricingPlans = [
    {
      name: "Free",
      price: "$0",
      period: "/month",
      description: "Perfect for small teams getting started",
      features: [
        "1,000 test executions/month",
        "Basic AI healing",
        "Community support",
        "5 team members",
      ],
      cta: "Start Free",
      popular: false,
    },
    {
      name: "Pro",
      price: "$99",
      period: "/month",
      description: "For growing teams with advanced needs",
      features: [
        "50,000 test executions/month",
        "Advanced AI healing & generation",
        "Priority support",
        "Unlimited team members",
        "Custom integrations",
        "Advanced analytics",
      ],
      cta: "Start Pro Trial",
      popular: true,
    },
    {
      name: "Enterprise",
      price: "$499",
      period: "/month",
      description: "For large organizations with custom requirements",
      features: [
        "Unlimited test executions",
        "Full AI suite",
        "24/7 dedicated support",
        "SSO & SAML",
        "Custom AI models",
        "On-premise deployment",
        "SLA guarantee",
      ],
      cta: "Contact Sales",
      popular: false,
    },
  ];

  const stats = [
    { value: "500+", label: "Teams Worldwide" },
    { value: "10M+", label: "Tests Executed" },
    { value: "99.5%", label: "Uptime SLA" },
    { value: "70%", label: "Maintenance Reduction" },
  ];

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      {/* EU AI Act Art. 50(1) — divulgacion de uso de IA en esta pagina publica */}
      <DisclosureBanner />

      {/* Hero Section */}
      <Box
        sx={{
          bgcolor: "primary.main",
          color: "white",
          py: { xs: 8, md: 12 },
          position: "relative",
          overflow: "hidden",
        }}
      >
        <Container maxWidth="lg">
          <Grid container spacing={4} sx={{ alignItems: "center" }}>
            <Grid size={{ xs: 12, md: 7 }}>
              <Typography
                variant={isMobile ? "h3" : "h2"}
                component="h1"
                gutterBottom
                sx={{ fontWeight: "bold", mb: 3 }}
              >
                AI-Powered Testing That Heals Itself
              </Typography>
              <Typography variant="h5" sx={{ mb: 4, opacity: 0.9 }}>
                Reduce test maintenance by 70% with intelligent self-healing
                tests, AI-generated test cases, and automatic flaky test
                detection.
              </Typography>
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Button
                  variant="contained"
                  size="large"
                  sx={{
                    bgcolor: "white",
                    color: "primary.main",
                    "&:hover": { bgcolor: "grey.100" },
                    px: 4,
                    py: 1.5,
                  }}
                  onClick={() => scrollToSection("pricing")}
                >
                  Start Free Trial
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  startIcon={<PlayIcon />}
                  sx={{
                    borderColor: "white",
                    color: "white",
                    "&:hover": {
                      borderColor: "grey.300",
                      bgcolor: "rgba(255,255,255,0.1)",
                    },
                    px: 4,
                    py: 1.5,
                  }}
                >
                  Watch Demo
                </Button>
              </Box>
            </Grid>
            <Grid size={{ xs: 12, md: 5 }}>
              {/* Placeholder for hero image/illustration */}
              <Box
                sx={{
                  bgcolor: "rgba(255,255,255,0.1)",
                  borderRadius: 2,
                  height: 300,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <PsychologyIcon sx={{ fontSize: 120, opacity: 0.5 }} />
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Stats Section */}
      <Box sx={{ py: 6, bgcolor: "grey.50" }}>
        <Container maxWidth="lg">
          <Grid container spacing={4}>
            {stats.map((stat, index) => (
              <Grid size={{ xs: 6, md: 3 }} key={index}>
                <Box sx={{ textAlign: "center" }}>
                  <Typography
                    variant="h3"
                    sx={{ fontWeight: "bold", color: "primary.main" }}
                  >
                    {stat.value}
                  </Typography>
                  <Typography variant="body1" color="text.secondary">
                    {stat.label}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 10 } }}>
        <Typography
          variant="h3"
          align="center"
          gutterBottom
          sx={{ fontWeight: "bold", mb: 6 }}
        >
          Powerful Features for Modern Teams
        </Typography>
        <Grid container spacing={4}>
          {features.map((feature, index) => (
            <Grid size={{ xs: 12, md: 6 }} key={index}>
              <Card
                sx={{
                  height: "100%",
                  p: 2,
                  transition: "transform 0.3s, box-shadow 0.3s",
                  "&:hover": {
                    transform: "translateY(-4px)",
                    boxShadow: 4,
                  },
                }}
              >
                <CardContent>
                  <Box sx={{ mb: 2 }}>{feature.icon}</Box>
                  <Typography
                    variant="h5"
                    gutterBottom
                    sx={{ fontWeight: "bold" }}
                  >
                    {feature.title}
                  </Typography>
                  <Typography variant="body1" color="text.secondary">
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* Pricing Section */}
      <Box id="pricing" sx={{ py: { xs: 6, md: 10 }, bgcolor: "grey.50" }}>
        <Container maxWidth="lg">
          <Typography
            variant="h3"
            align="center"
            gutterBottom
            sx={{ fontWeight: "bold", mb: 2 }}
          >
            Simple, Transparent Pricing
          </Typography>
          <Typography
            variant="h6"
            align="center"
            color="text.secondary"
            sx={{ mb: 6 }}
          >
            Start free, scale as you grow
          </Typography>
          <Grid container spacing={4} sx={{ justifyContent: "center" }}>
            {pricingPlans.map((plan, index) => (
              <Grid size={{ xs: 12, md: 4 }} key={index}>
                <Card
                  sx={{
                    height: "100%",
                    position: "relative",
                    border: plan.popular ? 2 : 0,
                    borderColor: "primary.main",
                    boxShadow: plan.popular ? 8 : 2,
                  }}
                >
                  {plan.popular && (
                    <Chip
                      label="Most Popular"
                      color="primary"
                      sx={{
                        position: "absolute",
                        top: -12,
                        left: "50%",
                        transform: "translateX(-50%)",
                        fontWeight: "bold",
                      }}
                    />
                  )}
                  <CardContent sx={{ p: 4 }}>
                    <Typography
                      variant="h4"
                      gutterBottom
                      sx={{ fontWeight: "bold" }}
                    >
                      {plan.name}
                    </Typography>
                    <Box
                      sx={{ display: "flex", alignItems: "baseline", mb: 2 }}
                    >
                      <Typography
                        variant="h3"
                        sx={{ fontWeight: "bold", color: "primary.main" }}
                      >
                        {plan.price}
                      </Typography>
                      <Typography variant="body1" color="text.secondary">
                        {plan.period}
                      </Typography>
                    </Box>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mb: 3 }}
                    >
                      {plan.description}
                    </Typography>
                    <Box sx={{ mb: 3 }}>
                      {plan.features.map((feature, featureIndex) => (
                        <Box
                          key={featureIndex}
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            mb: 1.5,
                          }}
                        >
                          <CheckIcon
                            sx={{ color: "success.main", mr: 1, fontSize: 20 }}
                          />
                          <Typography variant="body2">{feature}</Typography>
                        </Box>
                      ))}
                    </Box>
                    <Button
                      variant={plan.popular ? "contained" : "outlined"}
                      fullWidth
                      size="large"
                      sx={{ mt: 2 }}
                    >
                      {plan.cta}
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>

      {/* CTA Section */}
      <Box
        sx={{ py: { xs: 6, md: 10 }, bgcolor: "primary.main", color: "white" }}
      >
        <Container maxWidth="md">
          <Box sx={{ textAlign: "center" }}>
            <Typography variant="h3" gutterBottom sx={{ fontWeight: "bold" }}>
              Ready to Transform Your Testing?
            </Typography>
            <Typography variant="h6" sx={{ mb: 4, opacity: 0.9 }}>
              Join 500+ teams already using AI-powered testing to ship faster
              with confidence.
            </Typography>
            <Button
              variant="contained"
              size="large"
              sx={{
                bgcolor: "white",
                color: "primary.main",
                "&:hover": { bgcolor: "grey.100" },
                px: 6,
                py: 2,
                fontSize: "1.1rem",
              }}
            >
              Start Your Free Trial
            </Button>
          </Box>
        </Container>
      </Box>

      {/* Footer */}
      <Box sx={{ py: 4, bgcolor: "grey.900", color: "white" }}>
        <Container maxWidth="lg">
          <Grid container spacing={4}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: "bold" }}>
                QA-FRAMEWORK
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.7 }}>
                AI-powered testing platform for modern software teams.
              </Typography>
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <Typography
                variant="subtitle2"
                gutterBottom
                sx={{ fontWeight: "bold" }}
              >
                Product
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                Features
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                Pricing
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                Documentation
              </Typography>
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <Typography
                variant="subtitle2"
                gutterBottom
                sx={{ fontWeight: "bold" }}
              >
                Company
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                About
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                Blog
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                Careers
              </Typography>
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <Typography
                variant="subtitle2"
                gutterBottom
                sx={{ fontWeight: "bold" }}
              >
                Legal
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                Privacy
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                Terms
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                Security
              </Typography>
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <Typography
                variant="subtitle2"
                gutterBottom
                sx={{ fontWeight: "bold" }}
              >
                Connect
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                Twitter
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                GitHub
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  display: "block",
                  mb: 1,
                  opacity: 0.7,
                  cursor: "pointer",
                }}
              >
                Discord
              </Typography>
            </Grid>
          </Grid>
          <Box
            sx={{ mt: 4, pt: 2, borderTop: "1px solid rgba(255,255,255,0.1)" }}
          >
            <Typography variant="body2" align="center" sx={{ opacity: 0.7 }}>
              © 2026 QA-FRAMEWORK. All rights reserved.
            </Typography>
          </Box>
        </Container>
      </Box>
    </Box>
  );
};

export default Landing;
