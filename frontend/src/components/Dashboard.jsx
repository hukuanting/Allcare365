import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Skeleton from '@mui/material/Skeleton';
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
import { hasAnyRole, RESEARCH_ACCESS_ROLES, CLINICAL_WRITE_ROLES } from '../utils/roles';
import { apiErrorMessage, countFromResponse, displayValue, listFromResponse } from '../utils/apiData';

const datasetLabels = { h2u_cvd_csv: 'H2U 心血管健檢' };
const datasetLabel = value => datasetLabels[value] || value || '未提供';

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
  const canWrite = hasAnyRole(userInfo, CLINICAL_WRITE_ROLES);
  const researchAccess = hasAnyRole(userInfo, RESEARCH_ACCESS_ROLES);
  const requestRef = useRef(null);

  const displayName = useMemo(() => {
    if (userInfo?.first_name || userInfo?.last_name) {
      return `${userInfo?.last_name || ''}${userInfo?.first_name || ''}`.trim();
    }
    return userInfo?.username || '使用者';
  }, [userInfo]);

  const loadDashboard = async () => {
    requestRef.current?.abort();
    const controller = new AbortController(); requestRef.current = controller;
    setLoading(true); setMessage(null);
    setData({ patients: null, screenings: null, quality: null, requestedReports: null });
    const endpoints = [
      ['patients', API_CONFIG.ENDPOINTS.PATIENTS + '?page_size=1'],
      ['screenings', API_CONFIG.ENDPOINTS.HEALTH_SCREENINGS + '?page_size=1'],
      ...(researchAccess ? [['quality', API_CONFIG.ENDPOINTS.DATA_QUALITY_SUMMARY], ['requestedReports', API_CONFIG.ENDPOINTS.RESEARCH_REPORTS + '?status=requested']] : []),
    ];
    const requests = await Promise.allSettled(endpoints.map(async ([key, endpoint]) => {
      const response = await api.get(endpoint, { signal: controller.signal });
      const payload = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(payload, '資料讀取失敗'));
      if (key === 'quality') return [key, payload];
      if (key === 'requestedReports') {
        const hasTotal = !Array.isArray(payload) && Number.isFinite(payload?.count) && payload.count >= 0;
        const count = hasTotal ? payload.count : listFromResponse(payload).length;
        return [key, {
          count,
          note: hasTotal ? '符合條件的待審申請總數。'
            : Array.isArray(payload) && count === 100
              ? '本次載入已達 100 份上限，可能未包含更早申請。'
              : '本次載入的待審申請筆數。',
        }];
      }
      return [key, countFromResponse(payload)];
    }));
    if (controller.signal.aborted) return;
    const next = { patients: null, screenings: null, quality: null, requestedReports: null };
    const failedLabels = { patients: '病患', screenings: '健檢紀錄', quality: '資料品質', requestedReports: '研究報告' };
    const failures = [];
    requests.forEach((result, index) => {
      if (result.status === 'fulfilled') next[result.value[0]] = result.value[1];
      else failures.push(failedLabels[endpoints[index][0]]);
    });
    setData(next);
    if (failures.length) setMessage({ type: 'warning', text: failures.join('、') + '讀取失敗；未取得的資料顯示為缺值。請重新整理再試一次。' });
    setLoading(false);
  };

  useEffect(() => {
    loadDashboard();
    return () => requestRef.current?.abort();
  }, [researchAccess]);

  const metrics = [
    { label: '病患數', value: data.patients, icon: <PeopleIcon color="primary" /> },
    { label: '健檢紀錄', value: data.screenings, icon: <HistoryIcon color="secondary" /> },
    ...(researchAccess ? [
      { label: '待審研究報告', value: data.requestedReports?.count, note: data.requestedReports?.note, icon: <AssignmentTurnedInIcon color="primary" /> },
      { label: '資料狀態', note: data.quality?.dataset ? '評估範圍：' + datasetLabel(data.quality.dataset) : null, value: readinessText[data.quality?.readiness?.label] || data.quality?.readiness?.label || null, icon: <BiotechIcon color="primary" /> },
    ] : []),
  ];

  return (
    <Box className="page-frame atlas-dashboard">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">總覽</Typography>
          <Typography component="h1" variant="h4">臨床資料工作台</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            {displayName}，歡迎回到工作空間。從資料概況，開始今天的照護。
          </Typography>
        </Box>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadDashboard} disabled={loading}>{loading ? '整理中…' : '重新整理'}</Button>
          {canWrite && <Button variant="contained" startIcon={<UploadFileIcon />} component={RouterLink} to="/bulk-import">匯入資料</Button>}
        </Stack>
      </Box>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      {loading && <Typography role="status" color="text.secondary" sx={{ mb: 2 }}>讀取資料概況中…</Typography>}
      <Box className="dashboard-metrics" aria-label="資料概況" aria-busy={loading}>
        {metrics.map((metric) => <div key={metric.label} className="dashboard-metric"><div><Typography component="span">{metric.label}</Typography>{metric.icon}</div>{loading ? <Skeleton width="65%" height={46}/> : <><Typography component="p" className="dashboard-metric-value">{displayValue(metric.value)}</Typography>{metric.note && <Typography component="p" className="dashboard-metric-note">{metric.note}</Typography>}</>}</div>)}
      </Box>

      <Box className="dashboard-grid">
        {researchAccess && <Paper className="work-panel">
          <Box className="panel-heading">
            <Typography component="h2" variant="h6">資料品質摘要</Typography>
            <Chip size="small" label={datasetLabel(data.quality?.dataset)} variant="outlined" />
          </Box>
          <Box className="dashboard-quality" sx={{ mt: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">最早健檢日期</Typography>
              <Typography component="p" variant="h6">{displayValue(data.quality?.date_range?.first)}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">最新健檢日期</Typography>
              <Typography component="p" variant="h6">{displayValue(data.quality?.date_range?.last)}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">重複 Encounter</Typography>
              <Typography component="p" variant="h6">{displayValue(data.quality?.duplicates?.duplicate_encounter_identifiers)}</Typography>
            </Box>
          </Box>
        </Paper>}

        <Paper className="work-panel dashboard-actions">
          <Box className="panel-heading">
            <Typography component="h2" variant="h6">接下來的工作</Typography>
            <Chip size="small" label="工作捷徑" color="success" variant="outlined" />
          </Box>
          <Stack className="dashboard-action-list" sx={{ mt: 2 }}>
            <Button component={RouterLink} to="/patients">病患管理 <span aria-hidden="true">↗</span></Button>
            <Button component={RouterLink} to="/history">健檢紀錄 <span aria-hidden="true">↗</span></Button>
            {hasAnyRole(userInfo, RESEARCH_ACCESS_ROLES) && <>
              <Button component={RouterLink} to="/research-cohorts">研究族群 <span aria-hidden="true">↗</span></Button>
              <Button component={RouterLink} to="/research-reports">研究報告 <span aria-hidden="true">↗</span></Button>
            </>}
          </Stack>
        </Paper>
      </Box>
    </Box>
  );
}

export default Dashboard;
