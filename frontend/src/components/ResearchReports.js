import React, { useCallback, useEffect, useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControl from '@mui/material/FormControl';
import InputAdornment from '@mui/material/InputAdornment';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DownloadIcon from '@mui/icons-material/Download';
import RefreshIcon from '@mui/icons-material/Refresh';
import ScienceIcon from '@mui/icons-material/Science';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { useAuth } from '../hooks/useAuth';
import { hasAnyRole, RESEARCH_APPROVAL_ROLES } from '../utils/roles';
import { apiErrorMessage, listFromResponse } from '../utils/apiData';
import './ResearchReports.css';

const emptyRequest = {
  title: '',
  report_type: 'cohort_summary',
  sex: '',
  sbp_min: '',
  hba1c_min: '',
};

const statusColor = {
  requested: 'warning',
  approved: 'success',
  rejected: 'error',
};

const statusLabel = {
  requested: '待審核',
  approved: '已核准',
  rejected: '已拒絕',
};

const reportTypeLabel = {
  cohort_summary: 'Cohort summary',
  cohort_measure_report: 'FHIR MeasureReport',
  patients_like_this: 'Patients like this',
};

const displayDate = (value) => (value ? new Date(value).toLocaleString() : '無資料');

function ResearchReports() {
  const { userInfo } = useAuth();
  const [reports, setReports] = useState([]);
  const [statusFilter, setStatusFilter] = useState('requested');
  const [requestForm, setRequestForm] = useState(emptyRequest);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);
  const [actionReport, setActionReport] = useState(null);
  const [actionType, setActionType] = useState('');
  const [approvalNote, setApprovalNote] = useState('');
  const [artifact, setArtifact] = useState(null);

  const canApprove = hasAnyRole(userInfo, RESEARCH_APPROVAL_ROLES);
  const counts = useMemo(() => reports.reduce((acc, report) => {
    acc[report.status] = (acc[report.status] || 0) + 1;
    return acc;
  }, {}), [reports]);

  const loadReports = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const suffix = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
      const response = await api.get(`${API_CONFIG.ENDPOINTS.RESEARCH_REPORTS}${suffix}`);
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, '研究報告清單讀取失敗'));
      setReports(listFromResponse(data));
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const updateRequest = (key, value) => {
    setRequestForm((current) => ({ ...current, [key]: value }));
  };

  const createRequest = async () => {
    if (!requestForm.title.trim()) {
      setMessage({ type: 'error', text: '請輸入研究報告標題' });
      return;
    }

    setSubmitting(true);
    setMessage(null);
    const queryParams = {};
    ['sex', 'sbp_min', 'hba1c_min'].forEach((key) => {
      if (requestForm[key] !== '') queryParams[key] = requestForm[key];
    });

    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.RESEARCH_REPORTS, {
        title: requestForm.title,
        report_type: requestForm.report_type,
        query_params: queryParams,
      });
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, '研究報告申請失敗'));
      setMessage({ type: 'success', text: '研究報告申請已建立' });
      setRequestForm(emptyRequest);
      setStatusFilter('requested');
      await loadReports();
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setSubmitting(false);
    }
  };

  const openAction = (report, type) => {
    setActionReport(report);
    setActionType(type);
    setApprovalNote('');
  };

  const submitAction = async () => {
    if (!actionReport || !actionType) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const response = await api.post(
        `${API_CONFIG.ENDPOINTS.RESEARCH_REPORTS}${actionReport.id}/${actionType}/`,
        { approval_note: approvalNote },
      );
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, '研究報告審核操作失敗'));
      setMessage({ type: 'success', text: actionType === 'approve' ? '研究報告已核准' : '研究報告已拒絕' });
      setActionReport(null);
      setActionType('');
      await loadReports();
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setSubmitting(false);
    }
  };

  const viewArtifact = async (report) => {
    setMessage(null);
    try {
      const response = await api.get(`${API_CONFIG.ENDPOINTS.RESEARCH_REPORTS}${report.id}/artifact/`);
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, '研究報告 artifact 尚不可讀取'));
      setArtifact({ report, data });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    }
  };

  return (
    <Box className="page-frame research-reports">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">研究治理</Typography>
          <Typography variant="h4">研究報告審核</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            申請、審核與讀取後端產生的 aggregate research artifact。
          </Typography>
        </Box>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Chip icon={<ScienceIcon />} label="僅 aggregate" color="success" variant="outlined" />
          <Chip icon={<AssignmentTurnedInIcon />} label={canApprove ? '可審核角色' : '申請角色'} color="primary" variant="outlined" />
        </Stack>
      </Box>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Box className="report-layout">
        <Paper className="work-panel report-request-panel">
          <Box className="panel-heading">
            <Typography variant="h6">申請 aggregate 輸出</Typography>
            <ScienceIcon color="primary" />
          </Box>
          <Box className="report-request-grid">
            <TextField
              size="small"
              label="標題"
              value={requestForm.title}
              onChange={(event) => updateRequest('title', event.target.value)}
            />
            <FormControl fullWidth size="small">
              <InputLabel id="report-type-label">報告類型</InputLabel>
              <Select
                labelId="report-type-label"
                label="報告類型"
                value={requestForm.report_type}
                onChange={(event) => updateRequest('report_type', event.target.value)}
              >
                {Object.entries(reportTypeLabel).map(([value, label]) => (
                  <MenuItem key={value} value={value}>{label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth size="small">
              <InputLabel id="report-sex-label">性別</InputLabel>
              <Select
                labelId="report-sex-label"
                label="性別"
                value={requestForm.sex}
                onChange={(event) => updateRequest('sex', event.target.value)}
              >
                <MenuItem value="">不限制</MenuItem>
                <MenuItem value="F">女性</MenuItem>
                <MenuItem value="M">男性</MenuItem>
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="SBP 下限"
              type="number"
              value={requestForm.sbp_min}
              onChange={(event) => updateRequest('sbp_min', event.target.value)}
              InputProps={{ endAdornment: <InputAdornment position="end">mmHg</InputAdornment> }}
            />
            <TextField
              size="small"
              label="HbA1c 下限"
              type="number"
              value={requestForm.hba1c_min}
              onChange={(event) => updateRequest('hba1c_min', event.target.value)}
              InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
            />
          </Box>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25} sx={{ mt: 2 }}>
            <Button variant="contained" startIcon={<AssignmentTurnedInIcon />} onClick={createRequest} disabled={submitting}>
              送出審核
            </Button>
            <Button variant="text" onClick={() => setRequestForm(emptyRequest)}>清除</Button>
          </Stack>
        </Paper>

        <Paper className="work-panel report-queue-panel">
          <Box className="panel-heading">
            <Typography variant="h6">審核佇列</Typography>
            <Stack direction="row" spacing={1}>
              <Chip size="small" label={`待審核 ${counts.requested || 0}`} color="warning" variant="outlined" />
              <Button size="small" startIcon={<RefreshIcon />} onClick={loadReports} disabled={loading}>
                重新整理
              </Button>
            </Stack>
          </Box>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.25} sx={{ mb: 2 }}>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="status-filter-label">狀態</InputLabel>
              <Select
                labelId="status-filter-label"
                label="狀態"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="requested">待審核</MenuItem>
                <MenuItem value="approved">已核准</MenuItem>
                <MenuItem value="rejected">已拒絕</MenuItem>
              </Select>
            </FormControl>
          </Stack>

          <TableContainer className="report-table">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>報告</TableCell>
                  <TableCell>類型</TableCell>
                  <TableCell>狀態</TableCell>
                  <TableCell>隱私</TableCell>
                  <TableCell>申請時間</TableCell>
                  <TableCell align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {reports.map((report) => (
                  <TableRow key={report.id}>
                    <TableCell>
                      <Typography variant="body2" fontWeight={900}>{report.title}</Typography>
                      <Typography variant="caption" color="text.secondary">{report.requested_by_username || '無資料'}</Typography>
                    </TableCell>
                    <TableCell>{reportTypeLabel[report.report_type] || report.report_type}</TableCell>
                    <TableCell>
                      <Chip size="small" label={statusLabel[report.status] || report.status} color={statusColor[report.status] || 'default'} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        Min cell {report.privacy_json?.minimum_cell_count ?? '無資料'} / {report.privacy_json?.suppressed ? '已遮蔽' : '可釋出'}
                      </Typography>
                    </TableCell>
                    <TableCell>{displayDate(report.requested_at)}</TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={0.75} justifyContent="flex-end">
                        <Button size="small" startIcon={<DownloadIcon />} disabled={!report.artifact_available} onClick={() => viewArtifact(report)}>
                          Artifact
                        </Button>
                        {canApprove && report.status === 'requested' && (
                          <>
                            <Button size="small" color="success" startIcon={<CheckCircleIcon />} onClick={() => openAction(report, 'approve')}>
                              核准
                            </Button>
                            <Button size="small" color="error" startIcon={<WarningAmberIcon />} onClick={() => openAction(report, 'reject')}>
                              拒絕
                            </Button>
                          </>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
                {!reports.length && (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
                        後端目前沒有回傳符合條件的研究報告。
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </Box>

      <Dialog open={Boolean(actionReport)} onClose={() => setActionReport(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{actionType === 'approve' ? '核准研究報告' : '拒絕研究報告'}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {actionReport?.title}
          </Typography>
          <TextField
            label="審核備註"
            multiline
            minRows={3}
            fullWidth
            value={approvalNote}
            onChange={(event) => setApprovalNote(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActionReport(null)}>取消</Button>
          <Button variant="contained" color={actionType === 'approve' ? 'success' : 'error'} onClick={submitAction} disabled={submitting}>
            {actionType === 'approve' ? '核准' : '拒絕'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(artifact)} onClose={() => setArtifact(null)} maxWidth="md" fullWidth>
        <DialogTitle>已核准 artifact</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {artifact?.report?.title}
          </Typography>
          <Box component="pre" className="artifact-preview">
            {artifact ? JSON.stringify(artifact.data, null, 2) : ''}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setArtifact(null)}>關閉</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ResearchReports;
