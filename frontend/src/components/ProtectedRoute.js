import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import LockIcon from '@mui/icons-material/Lock';
import { checkAuthStatus } from '../utils/auth';
import { hasAnyRole } from '../utils/roles';

function ProtectedRoute({ children, allowedRoles = [] }) {
  const location = useLocation();
  const [authState, setAuthState] = useState({
    loading: true,
    authenticated: false,
    userInfo: null,
  });

  useEffect(() => {
    const evaluate = () => {
      const result = checkAuthStatus();
      setAuthState({
        loading: false,
        authenticated: result.isAuthenticated,
        userInfo: result.userInfo || null,
      });
    };

    evaluate();

    const handleAuthChange = (event) => {
      const result = checkAuthStatus();
      setAuthState({
        loading: false,
        authenticated: Boolean(event.detail?.isAuthenticated),
        userInfo: event.detail?.userInfo || result.userInfo || null,
      });
    };

    const handleSessionLogout = () => {
      setAuthState({ loading: false, authenticated: false, userInfo: null });
    };

    window.addEventListener('auth-change', handleAuthChange);
    window.addEventListener('session-logout', handleSessionLogout);

    return () => {
      window.removeEventListener('auth-change', handleAuthChange);
      window.removeEventListener('session-logout', handleSessionLogout);
    };
  }, []);

  if (authState.loading) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 320 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <CircularProgress size={24} />
          <Typography color="text.secondary">Checking session</Typography>
        </Box>
      </Box>
    );
  }

  if (!authState.authenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (!hasAnyRole(authState.userInfo, allowedRoles)) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 420, px: 2 }}>
        <Paper
          sx={{
            maxWidth: 520,
            width: '100%',
            p: 3,
            border: '1px solid #e3ebf4',
            textAlign: 'center',
          }}
        >
          <Box
            sx={{
              width: 48,
              height: 48,
              mx: 'auto',
              mb: 2,
              borderRadius: 2,
              display: 'grid',
              placeItems: 'center',
              color: 'primary.main',
              bgcolor: 'rgba(25,118,210,0.08)',
            }}
          >
            <LockIcon />
          </Box>
          <Typography variant="h5">Access restricted</Typography>
          <Typography color="text.secondary" sx={{ mt: 1, mb: 2 }}>
            This workspace is limited to approved clinical and research roles.
          </Typography>
          <Button variant="contained" onClick={() => window.history.back()}>
            Go back
          </Button>
        </Paper>
      </Box>
    );
  }

  return children;
}

export default ProtectedRoute;
