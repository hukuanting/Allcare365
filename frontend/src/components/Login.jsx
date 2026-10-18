import React, { useEffect, useRef, useState } from 'react';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import LoginIcon from '@mui/icons-material/Login';
import AuthFrame from './AuthFrame';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { checkAuthStatus, setAuthState } from '../utils/auth';
import { apiErrorMessage } from '../utils/apiData';

const sessionMessages = {
  idle_timeout: '已超過 15 分鐘未操作，系統已自動登出。重新登入後可返回原本的頁面。',
  signed_out_elsewhere: '此帳號已在另一個分頁登出。請重新登入。',
  unauthorized: '登入狀態已失效。請重新登入以繼續工作。',
  token_expired: '登入期限已到。請重新登入以繼續工作。',
  refresh_failed: '無法延續登入狀態。請重新登入以繼續工作。',
};

function Login() {
  const [credentials, setCredentials] = useState({ username: '', password: '', otp_token: '' });
  const otpInput = useRef(null);
  const submissionLock = useRef(false);
  const errorNotice = useRef(null);
  const [enrollment, setEnrollment] = useState(null);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [messageSeverity, setMessageSeverity] = useState('error');
  const updateIdentity = (key, value) => { setCredentials(current => ({ ...current, [key]: value, otp_token: '' })); setEnrollment(null); setMfaRequired(false); setMessage(''); };
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (checkAuthStatus().isAuthenticated) navigate('/dashboard', { replace: true });
  }, [navigate]);

  useEffect(() => {
    if (!submitting && (mfaRequired || enrollment?.provisioningUri)) otpInput.current?.focus();
  }, [mfaRequired, enrollment?.provisioningUri, submitting]);

  useEffect(() => {
    if (message && messageSeverity === 'error' && !submitting) errorNotice.current?.focus();
  }, [message, messageSeverity, submitting]);

  const finishLogin = (payload) => {
    setAuthState(payload);
    const from = location.state?.from;
    navigate(from?.pathname ? from.pathname + (from.search || '') + (from.hash || '') : '/dashboard', { replace: true });
  };

  const submit = async (event) => {
    event.preventDefault();
    if (submissionLock.current) return;
    submissionLock.current = true;
    setSubmitting(true);
    setMessage(''); setMessageSeverity('error');
    try {
      const payloadBody = { ...credentials, otp_token: credentials.otp_token.trim() || undefined };
      const response = await api.post(API_CONFIG.ENDPOINTS.LOGIN, payloadBody);
      const payload = await parseApiResponse(response);
      if (!response.ok) {
        if (payload?.code === 'mfa_enrollment_required') {
          setEnrollment({ required: true, provisioningUri: '' });
          setMessageSeverity('info');
          setMessage('此帳號必須先設定多因素驗證。請選擇「開始設定 MFA」。');
          return;
        }
        if (payload?.code === 'mfa_required') {
          setMfaRequired(true);
          setMessageSeverity('info');
          setMessage('此帳號需要多因素驗證。請輸入驗證器 App 顯示的六位數代碼。');
          return;
        }
        throw new Error(apiErrorMessage(payload, '登入失敗，請確認帳號與密碼。'));
      }
      finishLogin(payload);
    } catch (requestError) {
      setMessage(requestError.message);
    } finally {
      submissionLock.current = false;
      setSubmitting(false);
    }
  };

  const startEnrollment = async () => {
    if (submissionLock.current) return;
    submissionLock.current = true;
    setSubmitting(true);
    setMessage(''); setMessageSeverity('error');
    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.MFA_ENROLL, {
        username: credentials.username,
        password: credentials.password,
      });
      const payload = await parseApiResponse(response);
      if (!response.ok || !payload?.provisioning_uri) {
        throw new Error(apiErrorMessage(payload, '無法開始 MFA 設定。'));
      }
      setEnrollment({ required: true, provisioningUri: payload.provisioning_uri });
      setMessageSeverity('info');
      setMessage('請在驗證器 App 中新增此帳號，然後輸入 App 顯示的六位數代碼。');
    } catch (requestError) {
      setMessage(requestError.message);
    } finally {
      submissionLock.current = false;
      setSubmitting(false);
    }
  };

  const verifyEnrollment = async () => {
    if (submissionLock.current) return;
    submissionLock.current = true;
    setSubmitting(true);
    setMessage(''); setMessageSeverity('error');
    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.MFA_VERIFY, {
        username: credentials.username,
        password: credentials.password,
        otp_token: credentials.otp_token.trim(),
      });
      const payload = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(payload, '驗證器代碼無效。'));
      finishLogin(payload);
    } catch (requestError) {
      setMessage(requestError.message);
    } finally {
      submissionLock.current = false;
      setSubmitting(false);
    }
  };

  const copyProvisioningUri = async () => {
    try {
      await navigator.clipboard.writeText(enrollment.provisioningUri);
      setMessageSeverity('success');
      setMessage('設定資訊已複製。請只貼到您的驗證器 App。');
    } catch (_error) {
      setMessageSeverity('warning');
      setMessage('無法自動複製；請手動複製設定資訊。');
    }
  };

  return (
    <AuthFrame title="登入工作空間" description="使用您的帳號與密碼登入工作空間。">
        {sessionMessages[location.state?.reason] && <Alert severity="info">{sessionMessages[location.state.reason]}</Alert>}
        {message && <Alert ref={errorNotice} tabIndex={-1} severity={messageSeverity}>{message}</Alert>}

        <Box component="form" aria-label="登入" aria-busy={submitting} onSubmit={enrollment?.required ? (event) => { event.preventDefault(); enrollment.provisioningUri ? verifyEnrollment() : startEnrollment(); } : submit}>
          <fieldset className="auth-fieldset" disabled={submitting}><legend className="intake-visually-hidden">帳號與身分驗證</legend>
          <Stack spacing={2}>
            <TextField label="帳號" value={credentials.username} onChange={(event) => updateIdentity('username', event.target.value)} name="username" autoComplete="username" required fullWidth />
            <TextField label="密碼" type="password" value={credentials.password} onChange={(event) => updateIdentity('password', event.target.value)} name="password" autoComplete="current-password" required fullWidth />
            {(mfaRequired || enrollment?.provisioningUri) && <TextField inputRef={otpInput} label="驗證器代碼" value={credentials.otp_token} onChange={(event) => setCredentials((current) => ({ ...current, otp_token: event.target.value.replace(/\s/g, '') }))} inputProps={{ inputMode: 'numeric', pattern: '[0-9]{6}', maxLength: 6 }} name="otp_token" required={mfaRequired || Boolean(enrollment?.provisioningUri)} autoComplete="one-time-code" fullWidth />}
            {enrollment?.provisioningUri && <TextField label="驗證器設定資訊" value={enrollment.provisioningUri} InputProps={{ readOnly: true }} helperText="將設定資訊加入驗證器 App，再輸入六位數代碼並選擇「驗證並登入」。" fullWidth />}
            {enrollment?.provisioningUri && <Button type="button" variant="outlined" onClick={copyProvisioningUri}>複製設定資訊</Button>}
            {enrollment?.required ? <>
              {!enrollment.provisioningUri && <Button type="submit" variant="contained" disabled={submitting}>{submitting ? '設定中…' : '開始設定 MFA'}</Button>}
              {enrollment.provisioningUri && <Button type="submit" variant="contained" disabled={submitting || !/^[0-9]{6}$/.test(credentials.otp_token)}>{submitting ? '驗證中…' : '驗證並登入'}</Button>}
            </> : <Button type="submit" variant="contained" size="large" startIcon={<LoginIcon />} disabled={submitting}>{submitting ? '登入中' : '登入'}</Button>}
          </Stack>
          </fieldset>
        </Box>

        <Typography variant="body2" color="text.secondary">尚未有帳號？<Link component={RouterLink} to="/register">申請帳號</Link></Typography>
    </AuthFrame>
  );
}

export default Login;
