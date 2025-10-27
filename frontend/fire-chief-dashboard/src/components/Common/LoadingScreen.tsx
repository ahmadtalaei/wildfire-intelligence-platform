import React from 'react';
import {
  Box,
  CircularProgress,
  Typography,
  Container,
} from '@mui/material';
import { LocalFireDepartment } from '@mui/icons-material';

interface LoadingScreenProps {
  message?: string;
}

const LoadingScreen: React.FC<LoadingScreenProps> = ({ 
  message = 'Loading Wildfire Intelligence Platform...' 
}) => {
  return (
    <Container maxWidth="sm">
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="100vh"
        textAlign="center"
      >
        <Box mb={3}>
          <LocalFireDepartment 
            color="primary" 
            sx={{ 
              fontSize: 80,
              animation: 'pulse 2s infinite',
              '@keyframes pulse': {
                '0%': {
                  opacity: 1,
                },
                '50%': {
                  opacity: 0.5,
                },
                '100%': {
                  opacity: 1,
                },
              },
            }}
          />
        </Box>
        
        <Box mb={3}>
          <CircularProgress 
            size={60}
            thickness={4}
            color="primary"
          />
        </Box>
        
        <Typography 
          variant="h6" 
          color="text.primary"
          gutterBottom
        >
          Fire Chief Dashboard
        </Typography>
        
        <Typography 
          variant="body1" 
          color="text.secondary"
        >
          {message}
        </Typography>
      </Box>
    </Container>
  );
};

export default LoadingScreen;