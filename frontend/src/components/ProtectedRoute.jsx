import React, { useEffect, useState } from 'react';
import { Link as RouterLink, Navigate, useLocation } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
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
        reason: result.reason,
      });
    };

    evaluate();

    const handleAuthChange = (event) => {
      const result = checkAuthStatus();
      setAuthState({
        loading: false,
        authenticated: Boolean(event.detail?.isAuthenticated),
        userInfo: event.detail?.userInfo || result.userInfo || null,
        reason: event.detail?.reason || result.reason,
      });
    };

    const handleSessionLogout = (event) => {
      setAuthState({ loading: false, authenticated: false, userInfo: null, reason: event.detail?.reason });
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
      <Box role="status" sx={{ display: 'grid', placeItems: 'center', minHeight: 320 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <CircularProgress size={24} />
          <Typography color="text.secondary">正在確認登入狀態…</Typography>
        </Box>
      </Box>
    );
  }

  if (!authState.authenticated) {
    return <Navigate to="/login" replace state={{ from: location, reason: authState.reason }} />;
  }

  if (!hasAnyRole(authState.userInfo, allowedRoles)) {
    return (
      <section className="atlas-route-state"><span className="atlas-eyebrow">WORKSPACE ACCESS</span><Typography component="h1" variant="h4">目前帳號無法開啟此頁</Typography><Typography color="text.secondary" sx={{ mt: 2, mb: 3 }}>此工作區需要核准的臨床或研究角色。若工作需要使用此功能，請聯絡管理員確認帳號權限。</Typography><Button component={RouterLink} to="/dashboard" variant="contained">回到總覽</Button></section>
    );
  }

  return children;
}

export default ProtectedRoute;
