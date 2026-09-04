import { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  CircularProgress,
  TextField,
  Grid,
} from "@mui/material";
import {
  CreditCard as CreditCardIcon,
  Add as AddIcon,
} from "@mui/icons-material";

interface PaymentMethodFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (paymentMethodId: string) => Promise<void>;
}

// Note: In production, you would use Stripe Elements for secure card input
// This is a simplified version for demonstration
export default function PaymentMethodForm({
  open,
  onClose,
  onSubmit,
}: PaymentMethodFormProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cardNumber, setCardNumber] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvc, setCvc] = useState("");

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      // In production, you would:
      // 1. Use Stripe.js to create a payment method
      // 2. Send only the payment method ID to your server
      // This is a placeholder implementation
      const mockPaymentMethodId = `pm_${Date.now()}`;
      await onSubmit(mockPaymentMethodId);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to add payment method");
    } finally {
      setLoading(false);
    }
  };

  const formatCardNumber = (value: string) => {
    const v = value.replace(/\s+/g, "").replace(/[^0-9]/gi, "");
    const matches = v.match(/\d{4,16}/g);
    const match = (matches && matches[0]) || "";
    const parts = [];
    for (let i = 0, len = match.length; i < len; i += 4) {
      parts.push(match.substring(i, i + 4));
    }
    return parts.length ? parts.join(" ") : value;
  };

  const formatExpiry = (value: string) => {
    const v = value.replace(/\s+/g, "").replace(/[^0-9]/gi, "");
    if (v.length >= 2) {
      return v.slice(0, 2) + "/" + v.slice(2, 4);
    }
    return v;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <CreditCardIcon />
          Add Payment Method
        </Box>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="body2">
            For production, this form would use Stripe Elements for secure card
            input. This is a demonstration version.
          </Typography>
        </Alert>

        <Box sx={{ pt: 1 }}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12 }}>
              <TextField
                fullWidth
                label="Card Number"
                placeholder="1234 5678 9012 3456"
                value={cardNumber}
                onChange={(e) =>
                  setCardNumber(formatCardNumber(e.target.value))
                }
                slotProps={{
                  htmlInput: { maxLength: 19 },
                  input: {
                    startAdornment: (
                      <CreditCardIcon color="action" sx={{ mr: 1 }} />
                    ),
                  },
                }}
              />
            </Grid>

            <Grid size={{ xs: 6 }}>
              <TextField
                fullWidth
                label="Expiry"
                placeholder="MM/YY"
                value={expiry}
                onChange={(e) => setExpiry(formatExpiry(e.target.value))}
                slotProps={{ htmlInput: { maxLength: 5 } }}
              />
            </Grid>

            <Grid size={{ xs: 6 }}>
              <TextField
                fullWidth
                label="CVC"
                placeholder="123"
                value={cvc}
                onChange={(e) =>
                  setCvc(e.target.value.replace(/\D/g, "").slice(0, 4))
                }
                slotProps={{ htmlInput: { maxLength: 4 } }}
              />
            </Grid>
          </Grid>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={loading || !cardNumber || !expiry || !cvc}
          startIcon={loading ? <CircularProgress size={20} /> : <AddIcon />}
        >
          Add Card
        </Button>
      </DialogActions>
    </Dialog>
  );
}
