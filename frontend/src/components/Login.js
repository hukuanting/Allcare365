import React, { useEffect, useState } from 'react';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import LoginIcon from '@mui/icons-material/Login';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { checkAuthStatus, setAuthState } from '../utils/auth';
import { apiErrorMessage } from '../utils/apiData';

function Login() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (checkAuthStatus().isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [navigate]);

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage('');

    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.LOGIN, credentials);
      const payload = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(payload, '登入失敗，請確認帳號與密碼'));
      setAuthState(payload);
      navigate(location.state?.from?.pathname || '/dashboard', { replace: true });
    } catch (requestError) {
      setMessage(requestError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box className="auth-page">
      <Paper className="auth-card">
        <Box>
          <Stack direction="row" spacing={1.25} alignItems="center" sx={{ mb: 2 }}>
            <MonitorHeartIcon color="primary" />
            <Typography fontWeight={900}>AllCare365</Typography>
          </Stack>
          <Typography variant="h4">登入</Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            使用後端帳號登入臨床資料與研究治理系統。
          </Typography>
        </Box>

        {message && <Alert severity="error">{message}</Alert>}

        <Box component="form" onSubmit={submit}>
          <Stack spacing={2}>
            <TextField
              label="帳號"
              value={credentials.username}
              onChange={(event) => setCredentials((current) => ({ ...current, username: event.target.value }))}
              autoComplete="username"
              required
              fullWidth
            />
            <TextField
              label="密碼"
              type="password"
              value={credentials.password}
              onChange={(event) => setCredentials((current) => ({ ...current, password: event.target.value }))}
              autoComplete="current-password"
              required
              fullWidth
            />
            <Button type="submit" variant="contained" size="large" startIcon={<LoginIcon />} disabled={submitting}>
              {submitting ? '登入中' : '登入'}
            </Button>
          </Stack>
        </Box>

        <Typography variant="body2" color="text.secondary">
          尚未建立帳號？ <Link component={RouterLink} to="/register">前往註冊</Link>
        </Typography>
      </Paper>
    </Box>
  );
}

export default Login;
