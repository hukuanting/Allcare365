import React, { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import PersonAddAltIcon from '@mui/icons-material/PersonAddAlt';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage } from '../utils/apiData';

const initialForm = {
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  password2: '',
};

function Register() {
  const [formData, setFormData] = useState(initialForm);
  const [message, setMessage] = useState('');
  const [severity, setSeverity] = useState('error');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const updateField = (field, value) => {
    setFormData((current) => ({ ...current, [field]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setMessage('');

    if (formData.password !== formData.password2) {
      setSeverity('error');
      setMessage('兩次輸入的密碼不一致');
      return;
    }

    setSubmitting(true);

    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.REGISTER, formData);
      const payload = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(payload, '註冊失敗'));
      setSeverity('success');
      setMessage('帳號已建立，請登入');
      setTimeout(() => navigate('/login'), 900);
    } catch (requestError) {
      setSeverity('error');
      setMessage(requestError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box className="auth-page">
      <Paper className="auth-card wide">
        <Box>
          <Typography variant="overline" color="primary">AllCare365</Typography>
          <Typography variant="h4">註冊帳號</Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            建立可連到後端認證系統的使用者帳號。
          </Typography>
        </Box>

        {message && <Alert severity={severity}>{message}</Alert>}

        <Box component="form" onSubmit={submit}>
          <Box className="form-grid">
            <TextField label="帳號" value={formData.username} onChange={(event) => updateField('username', event.target.value)} required />
            <TextField label="Email" type="email" value={formData.email} onChange={(event) => updateField('email', event.target.value)} required />
            <TextField label="名" value={formData.first_name} onChange={(event) => updateField('first_name', event.target.value)} />
            <TextField label="姓" value={formData.last_name} onChange={(event) => updateField('last_name', event.target.value)} />
            <TextField label="密碼" type="password" value={formData.password} onChange={(event) => updateField('password', event.target.value)} required />
            <TextField label="確認密碼" type="password" value={formData.password2} onChange={(event) => updateField('password2', event.target.value)} required />
          </Box>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mt: 3 }}>
            <Button type="submit" variant="contained" startIcon={<PersonAddAltIcon />} disabled={submitting}>
              {submitting ? '建立中' : '建立帳號'}
            </Button>
            <Button component={RouterLink} to="/login">返回登入</Button>
          </Stack>
        </Box>

        <Typography variant="body2" color="text.secondary">
          已有帳號？ <Link component={RouterLink} to="/login">登入</Link>
        </Typography>
      </Paper>
    </Box>
  );
}

export default Register;
