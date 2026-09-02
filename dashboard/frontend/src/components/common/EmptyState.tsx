import { Box, Typography, Button, keyframes } from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { ReactNode } from 'react';

// Animation keyframes
const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const slideUp = keyframes`
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const scaleIn = keyframes`
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
`;

interface EmptyStateProps {
  illustration: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  customIcon?: ReactNode;
  variant?: 'default' | 'compact';
}

export default function EmptyState({
  illustration,
  title,
  description,
  actionLabel,
  onAction,
  customIcon,
  variant = 'default',
}: EmptyStateProps) {
  const isCompact = variant === 'compact';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: isCompact ? '300px' : '400px',
        textAlign: 'center',
        p: isCompact ? 2 : 4,
        animation: `${fadeIn} 0.5s ease-out`,
      }}
    >
      {/* Illustration */}
      <Box
        component="img"
        src={illustration}
        alt={title}
        sx={{
          width: '100%',
          maxWidth: isCompact ? '200px' : '300px',
          height: 'auto',
          mb: isCompact ? 2 : 3,
          opacity: 0.9,
          animation: `${scaleIn} 0.6s ease-out`,
          filter: 'drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1))',
          transition: 'transform 0.3s ease',
          '&:hover': {
            transform: 'scale(1.05)',
          },
        }}
        onError={(e) => {
          // Fallback if image doesn't load
          e.currentTarget.style.display = 'none';
        }}
      />

      {/* Custom Icon (alternative to illustration) */}
      {customIcon && (
        <Box
          sx={{
            mb: 3,
            color: 'primary.main',
            animation: `${scaleIn} 0.6s ease-out`,
            '& svg': {
              fontSize: 80,
              opacity: 0.7,
            },
          }}
        >
          {customIcon}
        </Box>
      )}

      {/* Title */}
      <Typography
        variant={isCompact ? 'h6' : 'h5'}
        gutterBottom
        
        sx={{ animation: `${slideUp} 0.5s ease-out 0.1s both`, fontWeight: "bold" }}
      >
        {title}
      </Typography>

      {/* Description */}
      <Typography
        variant="body1"
        color="textSecondary"
        sx={{
          maxWidth: '500px',
          mb: isCompact ? 2 : 3,
          animation: `${slideUp} 0.5s ease-out 0.2s both`,
        }}
      >
        {description}
      </Typography>

      {/* Action Button */}
      {actionLabel && onAction && (
        <Button
          variant="contained"
          color="primary"
          size="large"
          startIcon={<AddIcon />}
          onClick={onAction}
          sx={{
            mt: 2,
            px: 4,
            py: 1.5,
            fontSize: '1rem',
            fontWeight: 'bold',
            boxShadow: 3,
            animation: `${slideUp} 0.5s ease-out 0.3s both`,
            transition: 'all 0.3s ease',
            '&:hover': {
              transform: 'translateY(-2px)',
              boxShadow: 6,
            },
            '&:active': {
              transform: 'translateY(0)',
            },
          }}
        >
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}
