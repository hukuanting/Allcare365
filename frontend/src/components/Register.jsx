import React, { useEffect, useRef, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import PersonAddAltIcon from '@mui/icons-material/PersonAddAlt';
import AuthFrame from './AuthFrame';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage } from '../utils/apiData';

const initialForm = { username: '', email: '', first_name: '', last_name: '', password: '', password2: '' };

function Register() {
  const [formData, setFormData] = useState(initialForm); const [message, setMessage] = useState('');
  const [severity, setSeverity] = useState('error'); const [submitted, setSubmitted] = useState(false); const [submitting, setSubmitting] = useState(false);
  const errorNotice = useRef(null);
  const submissionLock = useRef(false);
  const confirmationHeading = useRef(null);
  useEffect(() => {
    if (submitted) confirmationHeading.current?.focus();
    else if (message && !submitting) errorNotice.current?.focus();
  }, [message, submitted, submitting]);
  const updateField = (field, value) => setFormData((current) => ({ ...current, [field]: value }));
  const submit = async (event) => {
    event.preventDefault(); if (submissionLock.current || submitted) return; setMessage('');
    if (formData.password !== formData.password2) { setSeverity('error'); setMessage('兩次輸入的密碼不一致。'); return; }
    submissionLock.current = true;
    setSubmitting(true);
    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.REGISTER, formData); const payload = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(payload, '帳號申請失敗。'));
      setSeverity('success'); setMessage(payload.detail || '帳號已建立，可使用 Viewer 權限登入。'); setFormData(initialForm); setSubmitted(true);
    } catch (requestError) { setSeverity('error'); setMessage(requestError.message); } finally { submissionLock.current = false; setSubmitting(false); }
  };
  return <AuthFrame mode="register" title="建立工作空間帳號" description="註冊後即可使用 Viewer 權限登入。研究、資料管理與帳號管理權限由管理員另行授予。">
    {message && <Alert ref={errorNotice} tabIndex={-1} role={severity === 'success' ? 'status' : 'alert'} severity={severity}>{message}</Alert>}
    {submitted ? <div className="auth-confirmation"><Typography ref={confirmationHeading} tabIndex={-1} component="h2" variant="h6">帳號已建立</Typography><Typography color="text.secondary">您可以使用剛建立的帳號與密碼登入。Viewer 只能查看獲得授權的資料。</Typography><Button component={RouterLink} to="/login" variant="contained">前往登入</Button></div> : <>
    <Box component="form" onSubmit={submit} aria-label="申請帳號" aria-busy={submitting}><fieldset className="auth-fieldset" disabled={submitting}><legend className="intake-visually-hidden">帳號申請資料</legend><Box className="form-grid">
      <TextField label="帳號" name="username" autoComplete="username" value={formData.username} onChange={(event) => updateField('username', event.target.value)} required />
      <TextField label="Email" name="email" autoComplete="email" type="email" value={formData.email} onChange={(event) => updateField('email', event.target.value)} required />
      <TextField label="姓氏" name="family_name" autoComplete="family-name" value={formData.last_name} onChange={(event) => updateField('last_name', event.target.value)} />
      <TextField label="名字" name="given_name" autoComplete="given-name" value={formData.first_name} onChange={(event) => updateField('first_name', event.target.value)} />
      <TextField label="密碼" name="password" autoComplete="new-password" type="password" helperText="至少 8 個字元，避免全數字或常見密碼。" value={formData.password} onChange={(event) => updateField('password', event.target.value)} required />
      <TextField label="確認密碼" name="password_confirmation" autoComplete="new-password" type="password" value={formData.password2} onChange={(event) => updateField('password2', event.target.value)} required />
    </Box><Stack spacing={1.5} sx={{ mt: 3 }}><Button type="submit" variant="contained" startIcon={<PersonAddAltIcon />} disabled={submitting}>{submitting ? '送出中' : '申請帳號'}</Button></Stack></fieldset></Box>
    <Typography variant="body2" color="text.secondary">已有帳號？<Link component={RouterLink} to="/login">登入</Link></Typography>
    </>}
  </AuthFrame>;
}
export default Register;
