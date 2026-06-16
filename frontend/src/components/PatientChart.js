import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Typography from '@mui/material/Typography';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import EditNoteIcon from '@mui/icons-material/EditNote';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage } from '../utils/apiData';

const sectionCount = (value) => (Array.isArray(value) ? value.length : 0);
const display = (value) => (value === null || value === undefined || value === '' ? '無資料' : value);

function DetailRow({ label, value }) {
  return (
    <Box className="detail-row">
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography fontWeight={800}>{display(value)}</Typography>
    </Box>
  );
}

function PatientChart() {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('summary');

  useEffect(() => {
    let mounted = true;

    const loadPatient = async () => {
      setLoading(true);
      setError('');

      try {
        const response = await api.get(`${API_CONFIG.ENDPOINTS.PATIENTS}${patientId}/`);
        const payload = await parseApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(payload, `病患讀取失敗：${response.status}`));
        if (mounted) setPatient(payload);
      } catch (requestError) {
        if (mounted) setError(requestError.message);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    loadPatient();
    return () => {
      mounted = false;
    };
  }, [patientId]);

  const chartCounts = useMemo(() => ({
    allergies: sectionCount(patient?.allergies),
    medications: sectionCount(patient?.medications),
    careTeam: sectionCount(patient?.care_team),
    documents: sectionCount(patient?.clinical_notes),
    orders: sectionCount(patient?.medical_orders),
  }), [patient]);

  if (loading) {
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 360 }}>
        <CircularProgress size={28} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box className="page-frame">
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!patient) return null;

  const fullName = patient.full_name || [patient.last_name, patient.first_name].filter(Boolean).join(' ') || `Patient ${patient.id}`;
  const address = [patient.current_address_line1, patient.city, patient.state].filter(Boolean).join(', ');

  return (
    <Box className="page-frame">
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/patients')} sx={{ mb: 2 }}>
        返回病患清單
      </Button>

      <Paper className="chart-header">
        <Box>
          <Typography variant="overline" color="primary">病患圖表</Typography>
          <Typography variant="h4">{fullName}</Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
            <Chip label={`MRN ${patient.medical_record_number || '無資料'}`} variant="outlined" />
            <Chip label={`${patient.age ?? '無資料'} 歲`} variant="outlined" />
            <Chip label={patient.sex || '性別無資料'} variant="outlined" />
            <Chip label={patient.status || '狀態無資料'} color="success" variant="outlined" />
          </Stack>
        </Box>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Button variant="outlined" startIcon={<EditNoteIcon />} onClick={() => navigate('/health-data-input')}>新增健檢</Button>
          <Button variant="contained" startIcon={<AnalyticsIcon />} onClick={() => navigate('/risk-analysis')}>風險分析</Button>
        </Stack>
      </Paper>

      <Paper className="chart-tabs">
        <Tabs value={tab} onChange={(_event, next) => setTab(next)} variant="scrollable" scrollButtons="auto">
          <Tab value="summary" label="摘要" />
          <Tab value="orders" label={`醫囑 ${chartCounts.orders}`} />
          <Tab value="medications" label={`用藥 ${chartCounts.medications}`} />
          <Tab value="care-team" label={`照護團隊 ${chartCounts.careTeam}`} />
          <Tab value="documents" label={`文件 ${chartCounts.documents}`} />
        </Tabs>
      </Paper>

      {tab === 'summary' && (
        <Box className="chart-grid">
          <Paper className="work-panel">
            <Typography variant="h6">基本資料</Typography>
            <Divider sx={{ my: 2 }} />
            <Box className="detail-grid">
              <DetailRow label="出生日期" value={patient.date_of_birth} />
              <DetailRow label="電話" value={patient.phone_number} />
              <DetailRow label="Email" value={patient.email_address} />
              <DetailRow label="地址" value={address} />
            </Box>
          </Paper>
          <Paper className="work-panel">
            <Typography variant="h6">圖表資料量</Typography>
            <Divider sx={{ my: 2 }} />
            <Box className="metric-grid">
              <Box className="mini-metric"><Typography variant="h5">{chartCounts.allergies}</Typography><Typography variant="caption">過敏</Typography></Box>
              <Box className="mini-metric"><Typography variant="h5">{chartCounts.medications}</Typography><Typography variant="caption">用藥</Typography></Box>
              <Box className="mini-metric"><Typography variant="h5">{chartCounts.careTeam}</Typography><Typography variant="caption">照護團隊</Typography></Box>
              <Box className="mini-metric"><Typography variant="h5">{chartCounts.documents}</Typography><Typography variant="caption">文件</Typography></Box>
            </Box>
          </Paper>
        </Box>
      )}

      {tab === 'orders' && (
        <Paper className="work-panel">
          <Typography variant="h6">醫囑</Typography>
          <Divider sx={{ my: 2 }} />
          {(patient.medical_orders || []).map((order) => (
            <Box key={order.id} className="list-row">
              <Typography fontWeight={900}>{display(order.order_type)}</Typography>
              <Typography color="text.secondary">{display(order.order_detail)}</Typography>
            </Box>
          ))}
          {!chartCounts.orders && <Typography color="text.secondary">後端目前沒有回傳醫囑資料。</Typography>}
        </Paper>
      )}

      {tab === 'medications' && (
        <Paper className="work-panel">
          <Typography variant="h6">用藥</Typography>
          <Divider sx={{ my: 2 }} />
          {(patient.medications || []).map((medication) => (
            <Box key={medication.id} className="list-row">
              <Typography fontWeight={900}>{display(medication.medication)}</Typography>
              <Typography color="text.secondary">{display(medication.medication_instructions || medication.indication)}</Typography>
            </Box>
          ))}
          {!chartCounts.medications && <Typography color="text.secondary">後端目前沒有回傳用藥資料。</Typography>}
        </Paper>
      )}

      {tab === 'care-team' && (
        <Paper className="work-panel">
          <Typography variant="h6">照護團隊</Typography>
          <Divider sx={{ my: 2 }} />
          {(patient.care_team || []).map((member) => (
            <Box key={member.id} className="list-row">
              <Typography fontWeight={900}>{display(member.name)}</Typography>
              <Typography color="text.secondary">{display(member.role)} {member.telecom ? `- ${member.telecom}` : ''}</Typography>
            </Box>
          ))}
          {!chartCounts.careTeam && <Typography color="text.secondary">後端目前沒有回傳照護團隊資料。</Typography>}
        </Paper>
      )}

      {tab === 'documents' && (
        <Paper className="work-panel">
          <Typography variant="h6">文件</Typography>
          <Divider sx={{ my: 2 }} />
          {(patient.clinical_notes || []).map((note) => (
            <Box key={note.id} className="list-row">
              <Typography fontWeight={900}>{display(note.note_type)}</Typography>
              <Typography color="text.secondary">{display(note.document_date)}</Typography>
            </Box>
          ))}
          {!chartCounts.documents && <Typography color="text.secondary">後端目前沒有回傳文件資料。</Typography>}
        </Paper>
      )}
    </Box>
  );
}

export default PatientChart;
