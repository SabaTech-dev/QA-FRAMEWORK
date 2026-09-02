import React from 'react'
import { Box, Typography, Button, Container, Paper } from '@mui/material'
import { Error as ErrorIcon, Home as HomeIcon } from '@mui/icons-material'

const NotFound: React.FC = () => {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        p: 2,
      }}
    >
      <Container sx={{ maxWidth: "md" }}>
        <Paper
          elevation={24}
          sx={{
            p: 6,
            textAlign: 'center',
            borderRadius: 4,
          }}
        >
          <ErrorIcon sx={{ fontSize: 120, color: 'error.main', mb: 3 }} />
          
          <Typography variant="h1" sx={{ fontSize: '8rem', fontWeight: 'bold', mb: 2 }}>
            404
          </Typography>
          
          <Typography variant="h4" gutterBottom sx={{ fontWeight: "bold" }}>
            Page Not Found
          </Typography>
          
          <Typography variant="body1" color="textSecondary" component="p" sx={{ mb: 4 }}>
            Oops! The page you're looking for doesn't exist or has been moved.
          </Typography>
          
          <Button
            variant="contained"
            size="large"
            startIcon={<HomeIcon />}
            href="/"
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              px: 4,
              py: 1.5,
            }}
          >
            Go Home
          </Button>
        </Paper>
      </Container>
    </Box>
  )
}

export default NotFound
