import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "react-query";
import {
  Box,
  Typography,
  Grid,
  CircularProgress,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from "@mui/material";
import {
  CreditCard as CreditCardIcon,
  Security as SecurityIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Star as StarIcon,
} from "@mui/icons-material";
import { billingAPI } from "../api/client";
import {
  PlanCard,
  InvoiceList,
  PaymentMethodForm,
  SubscriptionStatus,
} from "../components/billing";

interface Plan {
  id: string;
  name: string;
  price: number;
  interval: "month" | "year";
  features: { name: string; included: boolean }[];
  popular?: boolean;
}

interface PaymentMethod {
  id: string;
  type: string;
  last4: string;
  brand: string;
  exp_month: number;
  exp_year: number;
  is_default: boolean;
}

const defaultPlans: Plan[] = [
  {
    id: "free",
    name: "Free",
    price: 0,
    interval: "month",
    features: [
      { name: "3 Test Suites", included: true },
      { name: "50 Test Cases", included: true },
      { name: "Basic Reporting", included: true },
      { name: "Community Support", included: true },
      { name: "AI Self-Healing", included: false },
      { name: "Priority Support", included: false },
    ],
  },
  {
    id: "starter",
    name: "Starter",
    price: 99,
    interval: "month",
    popular: true,
    features: [
      { name: "10 Test Suites", included: true },
      { name: "500 Test Cases", included: true },
      { name: "Advanced Reporting", included: true },
      { name: "Email Support", included: true },
      { name: "AI Self-Healing", included: true },
      { name: "Priority Support", included: false },
    ],
  },
  {
    id: "pro",
    name: "Pro",
    price: 499,
    interval: "month",
    features: [
      { name: "Unlimited Test Suites", included: true },
      { name: "Unlimited Test Cases", included: true },
      { name: "Enterprise Reporting", included: true },
      { name: "Priority Support", included: true },
      { name: "AI Self-Healing", included: true },
      { name: "Custom Integrations", included: true },
    ],
  },
];

export default function Billing() {
  const queryClient = useQueryClient();
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({
    open: false,
    message: "",
    severity: "success",
  });
  const [paymentFormOpen, setPaymentFormOpen] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);

  // Queries
  const { data: plansData, isLoading: plansLoading } = useQuery(
    "billing-plans",
    () => billingAPI.getPlans(),
  );

  const { data: subscriptionData, isLoading: subscriptionLoading } = useQuery(
    "billing-subscription",
    () => billingAPI.getSubscription(),
  );

  const { data: invoicesData, isLoading: invoicesLoading } = useQuery(
    "billing-invoices",
    () => billingAPI.getInvoices(),
  );

  const { data: paymentMethodsData } = useQuery("billing-payment-methods", () =>
    billingAPI.getPaymentMethods(),
  );

  // Mutations
  const subscribeMutation = useMutation(
    ({
      planId,
      paymentMethodId,
    }: {
      planId: string;
      paymentMethodId?: string;
    }) => billingAPI.subscribe(planId, paymentMethodId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("billing-subscription");
        setSnackbar({
          open: true,
          message: "Subscription updated successfully!",
          severity: "success",
        });
        setUpgradeDialogOpen(false);
        setSelectedPlan(null);
      },
      onError: (error: any) => {
        setSnackbar({
          open: true,
          message:
            error.response?.data?.detail || "Failed to update subscription",
          severity: "error",
        });
      },
    },
  );

  const cancelMutation = useMutation(() => billingAPI.cancel(), {
    onSuccess: () => {
      queryClient.invalidateQueries("billing-subscription");
      setSnackbar({
        open: true,
        message: "Subscription canceled",
        severity: "success",
      });
      setCancelDialogOpen(false);
    },
    onError: (error: any) => {
      setSnackbar({
        open: true,
        message:
          error.response?.data?.detail || "Failed to cancel subscription",
        severity: "error",
      });
    },
  });

  const addPaymentMethodMutation = useMutation(
    (paymentMethodId: string) => billingAPI.addPaymentMethod(paymentMethodId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("billing-payment-methods");
        setSnackbar({
          open: true,
          message: "Payment method added!",
          severity: "success",
        });
      },
      onError: (error: any) => {
        setSnackbar({
          open: true,
          message:
            error.response?.data?.detail || "Failed to add payment method",
          severity: "error",
        });
      },
    },
  );

  const removePaymentMethodMutation = useMutation(
    (paymentMethodId: string) =>
      billingAPI.removePaymentMethod(paymentMethodId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("billing-payment-methods");
        setSnackbar({
          open: true,
          message: "Payment method removed",
          severity: "success",
        });
      },
      onError: (error: any) => {
        setSnackbar({
          open: true,
          message:
            error.response?.data?.detail || "Failed to remove payment method",
          severity: "error",
        });
      },
    },
  );

  const handlePlanSelect = (planId: string) => {
    setSelectedPlan(planId);
    if (planId === "free") {
      // Downgrade to free
      setUpgradeDialogOpen(true);
    } else {
      // Need payment method for paid plans
      setPaymentFormOpen(true);
    }
  };

  const handleAddPaymentMethod = async (paymentMethodId: string) => {
    await addPaymentMethodMutation.mutateAsync(paymentMethodId);
    if (selectedPlan) {
      await subscribeMutation.mutateAsync({
        planId: selectedPlan,
        paymentMethodId,
      });
    }
    setPaymentFormOpen(false);
  };

  const handleCancelSubscription = () => {
    cancelMutation.mutate();
  };

  const isLoading = plansLoading || subscriptionLoading;

  if (isLoading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "60vh",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  // Transform backend features object to frontend array format
  const transformFeatures = (
    features: any,
  ): { name: string; included: boolean }[] => {
    if (Array.isArray(features)) {
      return features;
    }
    // Convert object features to array
    return Object.entries(features || {}).map(([key, value]) => ({
      name: key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
      included: Boolean(value) || value === -1, // -1 means unlimited
    }));
  };

  const plans = (plansData?.data?.plans || defaultPlans).map((plan: any) => ({
    ...plan,
    features: transformFeatures(plan.features),
  }));
  const subscription = subscriptionData?.data;
  const invoices = invoicesData?.data || [];
  const paymentMethods = paymentMethodsData?.data || [];

  // Mark current plan
  const plansWithCurrent = plans.map((plan: Plan) => ({
    ...plan,
    current: subscription?.plan_id === plan.id,
  }));

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Billing & Subscription
      </Typography>

      {/* Subscription Status */}
      <Box sx={{ mb: 4 }}>
        <SubscriptionStatus
          subscription={subscription}
          onCancel={() => setCancelDialogOpen(true)}
          onUpgrade={() => setUpgradeDialogOpen(true)}
          isLoading={cancelMutation.isLoading || subscribeMutation.isLoading}
        />
      </Box>

      {/* Plans Grid */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Available Plans
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {plansWithCurrent.map((plan: Plan & { current: boolean }) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={plan.id}>
            <PlanCard
              plan={plan}
              onSelect={handlePlanSelect}
              isLoading={subscribeMutation.isLoading}
            />
          </Grid>
        ))}
      </Grid>

      {/* Payment Methods */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Payment Methods
      </Typography>
      <Card sx={{ mb: 4 }}>
        <CardContent>
          {paymentMethods.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                py: 4,
              }}
            >
              <CreditCardIcon
                sx={{ fontSize: 48, color: "text.disabled", mb: 2 }}
              />
              <Typography color="text.secondary" gutterBottom>
                No payment methods added
              </Typography>
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={() => setPaymentFormOpen(true)}
                sx={{ mt: 2 }}
              >
                Add Payment Method
              </Button>
            </Box>
          ) : (
            <>
              <List>
                {paymentMethods.map((method: PaymentMethod, index: number) => (
                  <Box key={method.id}>
                    {index > 0 && <Divider />}
                    <ListItem
                      secondaryAction={
                        <Box>
                          {!method.is_default && (
                            <Button
                              size="small"
                              onClick={() =>
                                billingAPI.setDefaultPaymentMethod(method.id)
                              }
                            >
                              Set Default
                            </Button>
                          )}
                          <Button
                            size="small"
                            color="error"
                            startIcon={<DeleteIcon />}
                            onClick={() =>
                              removePaymentMethodMutation.mutate(method.id)
                            }
                            sx={{ ml: 1 }}
                          >
                            Remove
                          </Button>
                        </Box>
                      }
                    >
                      <ListItemIcon>
                        <CreditCardIcon />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                            }}
                          >
                            <Typography>
                              {method.brand} ****{method.last4}
                            </Typography>
                            {method.is_default && (
                              <StarIcon color="primary" fontSize="small" />
                            )}
                          </Box>
                        }
                        secondary={`Expires ${method.exp_month}/${method.exp_year}`}
                      />
                    </ListItem>
                  </Box>
                ))}
              </List>
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={() => setPaymentFormOpen(true)}
                sx={{ mt: 2 }}
              >
                Add Another Card
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* Invoice History */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Invoice History
      </Typography>
      <InvoiceList invoices={invoices} isLoading={invoicesLoading} />

      {/* Security Notice */}
      <Alert severity="info" sx={{ mt: 4 }} icon={<SecurityIcon />}>
        <Typography variant="body2">
          Your payment information is securely handled by Stripe. We never store
          your full card details on our servers.
        </Typography>
      </Alert>

      {/* Payment Method Form Dialog */}
      <PaymentMethodForm
        open={paymentFormOpen}
        onClose={() => {
          setPaymentFormOpen(false);
          setSelectedPlan(null);
        }}
        onSubmit={handleAddPaymentMethod}
      />

      {/* Cancel Subscription Dialog */}
      <Dialog
        open={cancelDialogOpen}
        onClose={() => setCancelDialogOpen(false)}
      >
        <DialogTitle>Cancel Subscription</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to cancel your subscription? You will lose
            access to premium features at the end of your current billing
            period.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelDialogOpen(false)}>
            Keep Subscription
          </Button>
          <Button
            color="error"
            onClick={handleCancelSubscription}
            disabled={cancelMutation.isLoading}
          >
            Cancel Subscription
          </Button>
        </DialogActions>
      </Dialog>

      {/* Upgrade Dialog */}
      <Dialog
        open={upgradeDialogOpen}
        onClose={() => setUpgradeDialogOpen(false)}
      >
        <DialogTitle>Change Plan</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {selectedPlan === "free"
              ? "Are you sure you want to downgrade to the Free plan? You will lose access to premium features immediately."
              : "Are you sure you want to change your plan?"}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUpgradeDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => {
              if (selectedPlan) {
                subscribeMutation.mutate({ planId: selectedPlan });
              }
            }}
            disabled={subscribeMutation.isLoading}
          >
            Confirm Change
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: "100%" }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
