import {
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material'
import {
  Check as CheckIcon,
  Close as CloseIcon,
  Star as StarIcon,
} from '@mui/icons-material'

interface PlanFeature {
  name: string
  included: boolean
}

interface Plan {
  id: string
  name: string
  price: number
  interval: 'month' | 'year'
  features: PlanFeature[]
  popular?: boolean
  current?: boolean
}

interface PlanCardProps {
  plan: Plan
  onSelect: (planId: string) => void
  isLoading?: boolean
}

export default function PlanCard({ plan, onSelect, isLoading }: PlanCardProps) {
  const formatPrice = (price: number) => {
    if (price === 0) return 'Free'
    return `$${price}/${plan.interval}`
  }

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        border: plan.popular ? 2 : 0,
        borderColor: 'primary.main',
        transform: plan.popular ? 'scale(1.02)' : 'none',
        transition: 'transform 0.2s',
        '&:hover': {
          boxShadow: 6,
        },
      }}
    >
      {plan.popular && (
        <Chip
          icon={<StarIcon />}
          label="Most Popular"
          color="primary"
          sx={{
            position: 'absolute',
            top: -12,
            right: 16,
          }}
        />
      )}

      <CardContent sx={{ flexGrow: 1 }}>
        <Typography variant="h5" component="h2" gutterBottom>
          {plan.name}
        </Typography>

        <Box sx={{ mb: 2 }}>
          <Typography variant="h3" component="span" color="primary">
            {formatPrice(plan.price)}
          </Typography>
          {plan.price > 0 && (
            <Typography variant="body2" color="text.secondary" component="span">
              /{plan.interval}
            </Typography>
          )}
        </Box>

        <List dense>
          {plan.features.map((feature, index) => (
            <ListItem key={index} disablePadding>
              <ListItemIcon sx={{ minWidth: 32 }}>
                {feature.included ? (
                  <CheckIcon color="success" fontSize="small" />
                ) : (
                  <CloseIcon color="disabled" fontSize="small" />
                )}
              </ListItemIcon>
              <ListItemText
                primary={feature.name}
                slotProps={{ primary: {
                  color: feature.included ? 'text.primary' : 'text.disabled',
                } }}
              />
            </ListItem>
          ))}
        </List>
      </CardContent>

      <Box sx={{ p: 2, pt: 0 }}>
        <Button
          variant={plan.current ? 'outlined' : 'contained'}
          fullWidth
          disabled={plan.current || isLoading}
          onClick={() => onSelect(plan.id)}
          sx={{ mt: 1 }}
        >
          {plan.current ? 'Current Plan' : plan.price === 0 ? 'Downgrade' : 'Select Plan'}
        </Button>
      </Box>
    </Card>
  )
}
