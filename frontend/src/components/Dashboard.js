import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import BiotechIcon from '@mui/icons-material/Biotech';
import HistoryIcon from '@mui/icons-material/History';
import PeopleIcon from '@mui/icons-material/People';
import RefreshIcon from '@mui/icons-material/Refresh';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { useAuth } from '../hooks/useAuth';
import { apiErrorMessage, countFromResponse, displayValue } from '../utils/apiData';

const readinessText = {
  research_ready: '可供研究',
  needs_review: '需要檢查',
  insufficient_data: '資料不足',
};

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [data, setData] = useState({
    patients: null,
    screenings: null,
    quality: null,
    requestedReports: null,
  });
  const { userInfo } = useAuth();
  const navigate = useNavigate();

  const displayName = useMemo(() => {
    if (userInfo?.first_name || userInfo?.last_name) {
      return `${userInfo?.last_name || ''}${userInfo?.first_name || ''}`.trim();
    }
    return userInfo?.username || '使用者';
  }, [userInfo]);

  const loadDashboard = async () => {
    setLoading(true);
    setMessage(null);
    const requests = await Promise.allSettled([
      api.get(`${API_CONFIG.ENDPOINTS.PATIENTS}?page_size=1`),
      api.get(`${API_CONFIG.ENDPOINTS.HEALTH_SCREENINGS}?page_size=1`),
      api.get(API_CONFIG.ENDPOINTS.DATA_QUALITY_SUMMARY),
      api.get(`${API_CONFIG.ENDPOINTS.RESEARCH_REPORTS}?status=requested`),
    ]);

    const next = { patients: null, screenings: null, quality: null, requestedReports: null };
    const errors = [];

    for (const [index, result] of requests.entries()) {
      if (result.status !== 'fulfilled') {
        errors.push('後端請求未完成');
        continue;
      }
      const payload = await parseApiResponse(result.value);
      if (!result.value.ok) {
        errors.push(apiErrorMessage(payload));
        continue;
      }
      if (index === 0) next.patients = countFromResponse(payload);
      if (index === 1) next.screenings = countFromResponse(payload);
      if (index === 2) next.quality = payload;
      if (index === 3) next.requestedReports = countFromResponse(payload);
    }

    setData(next);
    if (errors.length) setMessage({ type: 'warning', text: `部分資料讀取失敗：${errors.join('；')}` });
    setLoading(false);
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 360 }}>
        <Stack alignItems="center" spacing={2}>
          <CircularProgress size={28} />
          <Typography color="text.secondary">讀取後端資料中</Typography>
        </Stack>
      </Box>
    );
  }

  const metrics = [
    { label: '病患數', value: data.patients, icon: <PeopleIcon color="primary" /> },
    { label: '健檢紀錄', value: data.screenings, icon: <HistoryIcon color="secondary" /> },
    { label: '待審研究報告', value: data.requestedReports, icon: <AssignmentTurnedInIcon color="warning" /> },
    { label: '資料狀態', value: readinessText[data.quality?.readiness?.label] || data.quality?.readiness?.label || null, icon: <BiotechIcon color="success" /> },
  ];

  return (
    <Box className="page-frame">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">總覽</Typography>
          <Typography variant="h4">臨床資料工作台</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            {displayName}，以下統計皆直接來自後端 API。
          </Typography>
        </Box>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadDashboard}>重新整理</Button>
          <Button variant="contained" startIcon={<UploadFileIcon />} onClick={() => navigate('/bulk-import')}>匯入資料</Button>
        </Stack>
      </Box>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Box className="metric-grid">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="text.secondary" fontWeight={800}>{metric.label}</Typography>
                {metric.icon}
              </Box>
              <Typography variant="h4">{displayValue(metric.value)}</Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Box className="dashboard-grid">
        <Paper className="work-panel">
          <Box className="panel-heading">
            <Typography variant="h6">資料品質摘要</Typography>
            <Chip size="small" label={data.quality?.dataset || '無資料'} variant="outlined" />
          </Box>
          <Box className="surface-grid" sx={{ mt: 2 }}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">最早健檢日期</Typography>
              <Typography variant="h6">{displayValue(data.quality?.date_range?.first)}</Typography>
            </Paper>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">最新健檢日期</Typography>
              <Typography variant="h6">{displayValue(data.quality?.date_range?.last)}</Typography>
            </Paper>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">重複 Encounter</Typography>
              <Typography variant="h6">{displayValue(data.quality?.duplicates?.duplicate_encounter_identifiers)}</Typography>
            </Paper>
          </Box>
        </Paper>

        <Paper className="work-panel">
          <Box className="panel-heading">
            <Typography variant="h6">目前可用流程</Typography>
            <Chip size="small" label="已掛接後端" color="success" variant="outlined" />
          </Box>
          <Stack spacing={1.25} sx={{ mt: 2 }}>
            <Button variant="outlined" onClick={() => navigate('/patients')}>病患管理</Button>
            <Button variant="outlined" onClick={() => navigate('/history')}>健檢紀錄</Button>
            <Button variant="outlined" onClick={() => navigate('/research-cohorts')}>研究 Cohort</Button>
            <Button variant="outlined" onClick={() => navigate('/research-reports')}>研究報告審核</Button>
          </Stack>
        </Paper>
      </Box>
    </Box>
  );
}

export default Dashboard;
