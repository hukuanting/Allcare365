import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import Alert from '@mui/material/Alert';
import useMediaQuery from '@mui/material/useMediaQuery';
import Skeleton from '@mui/material/Skeleton';
import LinearProgress from '@mui/material/LinearProgress';
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
import VisibilityIcon from '@mui/icons-material/Visibility';
import RefreshIcon from '@mui/icons-material/Refresh';
import ScienceIcon from '@mui/icons-material/Science';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { useAuth } from '../hooks/useAuth';
import { hasAnyRole, RESEARCH_APPROVAL_ROLES } from '../utils/roles';
import { apiErrorMessage, listFromResponse } from '../utils/apiData';
import './ResearchReports.css';
import FhirReportSummary from './FhirReportSummary';

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
  cohort_summary: '族群摘要',
  cohort_measure_report: 'FHIR MeasureReport',
  patients_like_this: '相似個案摘要',
};

const displayDate = (value) => {
  if (!value) return '未提供';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '未提供';
  return date.toLocaleString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
};

function ResearchReports() {
  const { userInfo } = useAuth();
  const reportTitlePrefix = useId();
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
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
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(null);
  const [hasNext, setHasNext] = useState(false);
  const [listError, setListError] = useState('');
  const [listLoaded, setListLoaded] = useState(false);
  const [snapshotAtLimit, setSnapshotAtLimit] = useState(false);
  const mutationLock = useRef(false);
  const requestFeedback = useRef(null);
  const actionFeedback = useRef(null);
  const [actionError, setActionError] = useState('');
  const [artifactLoading, setArtifactLoading] = useState(false);
  const listRequest = useRef(null);
  const artifactRequest = useRef(null);
  const artifactTrigger = useRef(null);
  const [artifactError, setArtifactError] = useState('');
  useEffect(() => () => artifactRequest.current?.abort(), []);

  useEffect(() => {
    if (!submitting && message) requestFeedback.current?.focus();
  }, [message, submitting]);
  useEffect(() => {
    if (!submitting && actionError) actionFeedback.current?.focus();
  }, [actionError, submitting]);

  const canApprove = hasAnyRole(userInfo, RESEARCH_APPROVAL_ROLES);
  const counts = useMemo(() => reports.reduce((acc, report) => {
    acc[report.status] = (acc[report.status] || 0) + 1;
    return acc;
  }, {}), [reports]);

  const loadReports = useCallback(async (filter = statusFilter, requestedPage = page) => {
    listRequest.current?.abort();
    const controller = new AbortController();
    listRequest.current = controller;
    setLoading(true); setListError(''); setReports([]); setTotalCount(null); setHasNext(false); setListLoaded(false); setSnapshotAtLimit(false);
    try {
      const params = new URLSearchParams({ page: String(requestedPage) });
      if (filter) params.set('status', filter);
      const response = await api.get(API_CONFIG.ENDPOINTS.RESEARCH_REPORTS + '?' + params, { signal: controller.signal });
      const data = await parseApiResponse(response);
      if (controller.signal.aborted) return;
      if (!response.ok) throw new Error(apiErrorMessage(data, '研究報告清單讀取失敗'));
      setReports(listFromResponse(data));
      setTotalCount(!Array.isArray(data) && typeof data?.count === 'number' ? data.count : null);
      setHasNext(Boolean(data?.next));
      setSnapshotAtLimit(Array.isArray(data) && data.length === 100);
      setListLoaded(true);
    } catch (error) { if (!controller.signal.aborted) setListError(error.message); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [statusFilter, page]);
  useEffect(() => { loadReports(); return () => listRequest.current?.abort(); }, [loadReports]);

  const updateRequest = (key, value) => {
    setRequestForm((current) => ({ ...current, [key]: value }));
  };

  const createRequest = async (event) => {
    event.preventDefault();
    if (mutationLock.current) return;
    if (!requestForm.title.trim()) {
      setMessage({ type: 'error', text: '請輸入研究報告標題' });
      return;
    }

    mutationLock.current = true;
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
      setPage(1);
      if (statusFilter === 'requested' && page === 1) void loadReports('requested', 1);
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      mutationLock.current = false;
      setSubmitting(false);
    }
  };

  const openAction = (report, type) => {
    if (mutationLock.current) return;
    setActionReport(report);
    setActionType(type);
    setApprovalNote('');
    setActionError('');
  };

  const submitAction = async () => {
    if (!actionReport || !actionType || mutationLock.current) return;
    mutationLock.current = true;
    setActionError('');
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
      void loadReports();
    } catch (error) {
      setActionError(error.message);
    } finally {
      mutationLock.current = false;
      setSubmitting(false);
    }
  };

  const closeArtifact = () => {
    artifactRequest.current?.abort();
    artifactRequest.current = null;
    setArtifact(null);
    setArtifactError('');
    setArtifactLoading(false);
  };

  const viewArtifact = async (report) => {
    if (artifactRequest.current) return;
    const controller = new AbortController();
    artifactRequest.current = controller;
    setArtifact({ report, data: null });
    setArtifactLoading(true);
    setArtifactError('');
    try {
      const response = await api.get(`${API_CONFIG.ENDPOINTS.RESEARCH_REPORTS}${report.id}/artifact/`, { signal: controller.signal });
      const data = await parseApiResponse(response);
      if (controller.signal.aborted) return;
      if (!response.ok) throw new Error(apiErrorMessage(data, '無法讀取研究報告，請確認存取權限或稍後重試。'));
      setArtifact({ report, data });
    } catch (error) {
      if (!controller.signal.aborted) setArtifactError(error.message);
    } finally {
      if (!controller.signal.aborted && artifactRequest.current === controller) {
        artifactRequest.current = null;
        setArtifactLoading(false);
      }
    }
  };

  return (
    <Box className="page-frame research-reports">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">研究治理</Typography>
          <Typography component="h1" variant="h4">研究報告審核</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            讓研究輸出有清楚的申請、審核與讀取脈絡。
          </Typography>
        </Box>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Chip icon={<ScienceIcon />} label="群體摘要輸出" color="success" variant="outlined" />
          <Chip icon={<AssignmentTurnedInIcon />} label={canApprove ? '可審核角色' : '申請角色'} color="primary" variant="outlined" />
        </Stack>
      </Box>

      {message && <Alert ref={requestFeedback} tabIndex={-1} role={message.type === 'success' ? 'status' : 'alert'} severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Box className="report-layout">
        <Paper component="form" aria-label="申請研究報告" onSubmit={createRequest} aria-busy={submitting} className="work-panel report-request-panel">
          <Box className="panel-heading">
            <Typography component="h2" variant="h6">申請研究報告</Typography>
            <ScienceIcon color="primary" />
          </Box>
          <Box className="report-request-grid">
            <TextField
              disabled={submitting}
              size="small"
              label="標題"
              required
              value={requestForm.title}
              onChange={(event) => updateRequest('title', event.target.value)}
            />
            <FormControl fullWidth size="small">
              <InputLabel id="report-type-label">報告類型</InputLabel>
              <Select
                disabled={submitting}
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
                disabled={submitting}
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
              disabled={submitting}
              size="small"
              label="SBP 下限"
              type="number"
              value={requestForm.sbp_min}
              onChange={(event) => updateRequest('sbp_min', event.target.value)}
              inputProps={{ 'aria-describedby': 'report-sbp-unit' }}
              InputProps={{ endAdornment: <InputAdornment position="end"><span id="report-sbp-unit">mmHg</span></InputAdornment> }}
            />
            <TextField
              disabled={submitting}
              size="small"
              label="HbA1c 下限"
              type="number"
              inputProps={{ step: 'any', 'aria-describedby': 'report-hba1c-unit' }}
              value={requestForm.hba1c_min}
              onChange={(event) => updateRequest('hba1c_min', event.target.value)}
              InputProps={{ endAdornment: <InputAdornment position="end"><span id="report-hba1c-unit">%</span></InputAdornment> }}
            />
          </Box>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25} sx={{ mt: 2 }}>
            <Button variant="contained" startIcon={<AssignmentTurnedInIcon />} type="submit" disabled={submitting}>
              {submitting ? '處理中…' : '送出審核'}
            </Button>
            <Button variant="text" onClick={() => setRequestForm(emptyRequest)} disabled={submitting}>清除</Button>
          </Stack>
        </Paper>

        <Paper className="work-panel report-queue-panel">
          <Box className="panel-heading">
            <Typography component="h2" variant="h6">審核佇列</Typography>
            <Stack direction="row" spacing={1}>
              <Chip size="small" label={loading ? '讀取待審核筆數…' : !listLoaded ? '待審核筆數未載入' : `${totalCount === null ? '本次' : '本頁'}待審核 ${counts.requested || 0}`} color="warning" variant="outlined" />
              <Button size="small" startIcon={<RefreshIcon />} onClick={() => loadReports()} disabled={loading}>
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
                onChange={(event) => { setStatusFilter(event.target.value); setPage(1); }}
              >
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="requested">待審核</MenuItem>
                <MenuItem value="approved">已核准</MenuItem>
                <MenuItem value="rejected">已拒絕</MenuItem>
              </Select>
            </FormControl>
          </Stack>

          {listError && <Alert severity="error" sx={{ mb: 2 }}>{listError}</Alert>}
          <Typography variant="caption" role="status" color="text.secondary">{loading ? '讀取報告清單中…' : totalCount !== null ? '符合條件共 ' + totalCount + ' 份報告' : listLoaded ? '本次載入 ' + reports.length + ' 份報告' : '尚未載入'}</Typography>
          {snapshotAtLimit && <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2 }}>本次清單已達 100 份上限，更早的報告可能未包含；可依狀態縮小範圍。</Typography>}
          <TableContainer className="report-table">
            <Table role="table" size="small" aria-label="研究報告清單" aria-busy={loading}>
              <TableHead role="rowgroup">
                <TableRow>
                  <TableCell role="columnheader">報告</TableCell>
                  <TableCell>類型</TableCell>
                  <TableCell>狀態</TableCell>
                  <TableCell>隱私</TableCell>
                  <TableCell>申請時間</TableCell>
                  <TableCell role="columnheader" align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody role="rowgroup">
                {!loading && reports.map((report) => (
                  <TableRow role="row" className="report-record" key={report.id}>
                    <TableCell>
                      <Typography id={reportTitlePrefix + '-' + report.id} variant="body2" fontWeight={900}>{report.title}</Typography>
                      <Typography variant="caption" color="text.secondary">{report.requested_by_username || '無資料'}</Typography>
                    </TableCell>
                    <TableCell>{reportTypeLabel[report.report_type] || report.report_type}</TableCell>
                    <TableCell>
                      <Chip size="small" label={statusLabel[report.status] || report.status} color={statusColor[report.status] || 'default'} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        Min cell {report.privacy_json?.minimum_cell_count ?? '無資料'} / {report.privacy_json?.suppressed === true ? '已遮蔽' : report.privacy_json?.suppressed === false ? '未遮蔽' : '未提供遮蔽狀態'}
                      </Typography>
                    </TableCell>
                    <TableCell>{displayDate(report.requested_at)}</TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={0.75} justifyContent="flex-end">
                        <Button aria-describedby={reportTitlePrefix + '-' + report.id} size="small" startIcon={<VisibilityIcon />} disabled={!report.artifact_available || artifactLoading} onClick={event => { artifactTrigger.current = event.currentTarget; viewArtifact(report); }}>
                          檢視報告
                        </Button>
                        {canApprove && report.status === 'requested' && (
                          <>
                            <Button aria-describedby={reportTitlePrefix + '-' + report.id} size="small" color="success" startIcon={<CheckCircleIcon />} disabled={submitting} onClick={() => openAction(report, 'approve')}>
                              核准
                            </Button>
                            <Button aria-describedby={reportTitlePrefix + '-' + report.id} size="small" color="error" startIcon={<WarningAmberIcon />} disabled={submitting} onClick={() => openAction(report, 'reject')}>
                              拒絕
                            </Button>
                          </>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
                {loading && Array.from({ length: 3 }, (_, index) => <TableRow key={index}>{Array.from({ length: 6 }, (_, cell) => <TableCell key={cell}><Skeleton animation={false} /></TableCell>)}</TableRow>)}
                {!loading && !listError && !reports.length && (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
                        目前沒有符合條件的研究報告。
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
          <div className="registry-pagination"><Typography variant="caption" color="text.secondary">{totalCount !== null || page > 1 ? '第 ' + page + ' 頁 · 本頁 ' + reports.length + ' 份' : '本次清單 · ' + reports.length + ' 份'}</Typography><Stack direction="row" spacing={1}><Button disabled={loading || page === 1} onClick={() => setPage(value => value - 1)}>上一頁</Button><Button disabled={loading || !hasNext} onClick={() => setPage(value => value + 1)}>下一頁</Button></Stack></div>
        </Paper>
      </Box>

      <Dialog transitionDuration={reducedMotion ? 0 : undefined} open={Boolean(actionReport)} aria-labelledby="report-action-title" aria-describedby={reportTitlePrefix + '-review-context'} onClose={() => { if (!submitting) setActionReport(null); }} maxWidth="sm" fullWidth>
        <DialogTitle id="report-action-title">{actionType === 'approve' ? '核准研究報告' : '拒絕研究報告'}</DialogTitle>
        <DialogContent>
          {actionError && <Alert ref={actionFeedback} tabIndex={-1} severity="error" sx={{ mb: 2 }}>{actionError}</Alert>}
          <Typography id={reportTitlePrefix + '-review-context'} variant="body2" color="text.secondary" sx={{ mb: 2, overflowWrap: 'anywhere' }}>
            {actionReport?.title}
          </Typography>
          <TextField
            disabled={submitting}
            label="審核備註"
            multiline
            minRows={3}
            fullWidth
            value={approvalNote}
            onChange={(event) => setApprovalNote(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button disabled={submitting} onClick={() => setActionReport(null)}>取消</Button>
          <Button variant="contained" color={actionType === 'approve' ? 'success' : 'error'} onClick={submitAction} disabled={submitting}>
            {actionType === 'approve' ? '核准' : '拒絕'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog transitionDuration={reducedMotion ? 0 : undefined} aria-labelledby="report-artifact-title" aria-describedby="report-artifact-context" open={Boolean(artifact)} onClose={closeArtifact} disableRestoreFocus TransitionProps={{ onExited: () => { if (artifactTrigger.current?.isConnected) artifactTrigger.current.focus(); } }} maxWidth="md" fullWidth>
        <DialogTitle id="report-artifact-title">研究報告預覽</DialogTitle>
        <DialogContent>
          <div id="report-artifact-context" className="artifact-context">
            <Typography component="p" variant="subtitle1">{artifact?.report?.title}</Typography>
            <Typography variant="body2" color="text.secondary">{reportTypeLabel[artifact?.report?.report_type] || artifact?.report?.report_type} · 申請時間 {displayDate(artifact?.report?.requested_at)}</Typography>
          </div>
          {artifactLoading && <div className="artifact-loading" role="status"><Typography variant="body2">正在讀取所選報告…</Typography><LinearProgress aria-label="讀取研究輸出" /></div>}
          {artifactError && <Alert severity="error" action={<Button onClick={() => viewArtifact(artifact.report)}>重新讀取</Button>}>{artifactError}</Alert>}
          {artifact && !artifactLoading && !artifactError && <><FhirReportSummary data={artifact.data} />{artifact.data?.resourceType === "MeasureReport" ? <details className="artifact-source"><summary>檢視 FHIR 原始資料</summary><Box component="pre" className="artifact-preview" tabIndex={0} aria-label="報告原始輸出">{JSON.stringify(artifact.data, null, 2)}</Box></details> : <Box component="pre" className="artifact-preview" tabIndex={0} aria-label="報告原始輸出">{JSON.stringify(artifact.data, null, 2)}</Box>}</>}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeArtifact}>{artifactLoading ? '取消讀取' : '關閉'}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ResearchReports;
