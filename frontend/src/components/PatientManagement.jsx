import { useAuth } from '../hooks/useAuth';
import { hasAnyRole, CLINICAL_WRITE_ROLES } from '../utils/roles';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Skeleton from '@mui/material/Skeleton';
import LinearProgress from '@mui/material/LinearProgress';
import Link from '@mui/material/Link';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TextField from '@mui/material/TextField';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import useMediaQuery from '@mui/material/useMediaQuery';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import RefreshIcon from '@mui/icons-material/Refresh';
import SearchIcon from '@mui/icons-material/Search';
import CloseIcon from '@mui/icons-material/Close';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage, countFromResponse, displayValue, listFromResponse } from '../utils/apiData';

const emptyPatient = {
  first_name: '',
  last_name: '',
  middle_name: '',
  date_of_birth: '',
  sex: '',
  medical_record_number: '',
  phone_number: '',
  email_address: '',
  current_address_line1: '',
  city: '',
  state: '',
  status: 'active',
};

const patientName = (patient) => patient.full_name || [patient.last_name, patient.first_name].filter(Boolean).join(' ') || '無姓名';

function PatientManagement() {
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
  const location = useLocation();
  const navigate = useNavigate();
  const initialList = useRef(location.state?.patientList);
  const { userInfo } = useAuth();
  const canWrite = hasAnyRole(userInfo, CLINICAL_WRITE_ROLES);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [searchTerm, setSearchTerm] = useState(typeof initialList.current?.searchTerm === 'string' ? initialList.current.searchTerm : '');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState(emptyPatient);
  const [page, setPage] = useState(Number.isSafeInteger(initialList.current?.page) && initialList.current.page > 0 ? initialList.current.page : 1);
  const [resultCount, setResultCount] = useState(null);
  const [hasNext, setHasNext] = useState(false);
  const [formError, setFormError] = useState('');
  const [createNotice, setCreateNotice] = useState(null);
  const saveLock = useRef(false);
  const firstNameInput = useRef(null);
  const searchInput = useRef(null);
  const requestRef = useRef({ sequence: 0, controller: null });

  // Keep navigation context in history state, without adding patient searches to URLs.
  useEffect(() => {
    navigate('.', { replace: true, state: { patientList: { searchTerm, page } } });
  }, [navigate, searchTerm, page]);

  const fetchPatients = useCallback(async (search = '', requestedPage = 1) => {
    const request = requestRef.current;
    request.controller?.abort();
    const controller = new AbortController();
    request.controller = controller;
    const sequence = ++request.sequence;
    setLoading(true);
    setPatients([]);
    setResultCount(null);
    setHasNext(false);
    setMessage(null);
    try {
      const params = new URLSearchParams({ page: String(requestedPage) });
      if (search.trim()) params.set('search', search.trim());
      const response = await api.get(API_CONFIG.ENDPOINTS.PATIENTS + '?' + params, { signal: controller.signal });
      const payload = await parseApiResponse(response);
      if (sequence !== request.sequence || controller.signal.aborted) return;
      if (!response.ok) throw new Error(apiErrorMessage(payload, '無法讀取病患清單，請稍後重試。'));
      setPatients(listFromResponse(payload));
      setResultCount(countFromResponse(payload));
      setHasNext(Boolean(payload?.next));
    } catch (error) {
      if (sequence === request.sequence && !controller.signal.aborted) setMessage({ type: 'error', text: error.message });
    } finally {
      if (sequence === request.sequence && !controller.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Invalidate immediately, including the debounce window.
    requestRef.current.controller?.abort();
    requestRef.current.sequence += 1;
    setLoading(true);
    setPatients([]);
    setResultCount(null);
    setHasNext(false);
    const timer = setTimeout(() => fetchPatients(searchTerm, page), 300);
    return () => {
      clearTimeout(timer);
      requestRef.current.controller?.abort();
      requestRef.current.sequence += 1;
    };
  }, [fetchPatients, searchTerm, page]);

  const clearSearch = () => {
    setSearchTerm('');
    setPage(1);
    searchInput.current?.focus();
  };

  const updateField = (field, value) => {
    setFormData((current) => ({ ...current, [field]: value }));
  };

  const savePatient = async (event) => {
    event.preventDefault();
    if (saveLock.current) return;
    saveLock.current = true;
    setSaving(true);
    setCreateNotice(null);
    setFormError('');
    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.PATIENTS, formData);
      const payload = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(payload, '新增病患失敗'));
      setDialogOpen(false);
      setFormData(emptyPatient);
      setCreateNotice('病患已新增');
      if (page !== 1) setPage(1);
      else void fetchPatients(searchTerm, 1);
    } catch (error) {
      setFormError(error.message);
    } finally {
      saveLock.current = false;
      setSaving(false);
    }
  };

  return (
    <Box className="page-frame atlas-registry atlas-patients">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">病患</Typography>
          <Typography component="h1" variant="h4">病患管理</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            找到照護對象，從完整紀錄開始。
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', rowGap: 1 }}>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => fetchPatients(searchTerm, page)} disabled={loading}>
            重新整理
          </Button>
          {canWrite && <Button variant="contained" startIcon={<AddCircleOutlineIcon />} onClick={() => { setFormError(''); setDialogOpen(true); }}>
            新增病患
          </Button>}
        </Stack>
      </Box>

      {createNotice && <Alert severity="success" role="status" onClose={() => setCreateNotice(null)} sx={{ mb: 2 }}>{createNotice}</Alert>}
      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Paper className="registry-toolbar">
        <TextField
          inputRef={searchInput}
          label="搜尋姓名或 MRN"
          value={searchTerm}
          onChange={(event) => { setSearchTerm(event.target.value); setPage(1); }}
          size="small"
          fullWidth
          InputProps={{
            endAdornment: searchTerm ? (
              <InputAdornment position="end">
                <IconButton aria-label="清除搜尋條件" onClick={clearSearch} edge="end" sx={{ width: 44, height: 44 }}>
                  <CloseIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ) : null,
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        <Typography className="registry-count" role="status" aria-live="polite">{loading ? '搜尋中…' : resultCount === null ? '尚未載入' : '共 ' + resultCount.toLocaleString() + ' 位病患'}</Typography>
      </Paper>

      {loading && <LinearProgress aria-label="載入病患清單" sx={{ height: 2 }} />}
      <TableContainer component={Paper} className="data-table">
        <Table role="table" size="small" aria-label="病患清單" aria-busy={loading}>
          <TableHead role="rowgroup">
            <TableRow role="row">
              <TableCell role="columnheader">病患</TableCell>
              <TableCell role="columnheader">MRN</TableCell>
              <TableCell role="columnheader">出生日期</TableCell>
              <TableCell role="columnheader">性別</TableCell>
              <TableCell role="columnheader">電話</TableCell>
              <TableCell role="columnheader">狀態</TableCell>
              <TableCell role="columnheader" align="right">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody role="rowgroup">
            {!loading && patients.map((patient) => (
              <TableRow role="row" key={patient.id} className="patient-record" hover>
                <TableCell role="cell" className="patient-name">
                  <Link component={RouterLink} to={'/patients/' + patient.id} state={{ patientList: { searchTerm, page } }} className="registry-patient-link" underline="hover">{patientName(patient)}</Link>
                  {patient.email_address && <Typography variant="caption" color="text.secondary">{patient.email_address}</Typography>}
                </TableCell>
                <TableCell role="cell" className="registry-mrn patient-mrn">{displayValue(patient.medical_record_number)}</TableCell>
                <TableCell role="cell" className="patient-birth">
                  {displayValue(patient.date_of_birth)}
                  {patient.age !== null && patient.age !== undefined && (
                    <Typography variant="caption" color="text.secondary" display="block">{patient.age} 歲</Typography>
                  )}
                </TableCell>
                <TableCell role="cell" className="patient-sex">{({ M: '男', F: '女', O: '其他', U: '未提供' })[patient.sex] || displayValue(patient.sex)}</TableCell>
                <TableCell role="cell" className="patient-phone">{displayValue(patient.phone_number)}</TableCell>
                <TableCell role="cell" className="patient-status"><Chip size="small" label={({ active: '使用中', inactive: '已停用', deceased: '已故', research: '研究個案' })[patient.status] || patient.status || '未提供'} color={patient.status === 'active' ? 'success' : 'default'} variant="outlined" /></TableCell>
                <TableCell role="cell" className="patient-action" align="right">
                  <Tooltip title="開啟病患">
                    <IconButton component={RouterLink} to={'/patients/' + patient.id} state={{ patientList: { searchTerm, page } }} size="small" sx={{ width: 44, height: 44 }} aria-label={'開啟 ' + patientName(patient) + ' 的病歷'}>
                      <ChevronRightIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {loading && Array.from({ length: 5 }, (_, index) => <TableRow role="row" className="registry-loading-row" key={'loading-' + index}>{Array.from({ length: 7 }, (_, cell) => <TableCell key={cell}><Skeleton animation={false} width={cell === 0 ? '80%' : '65%'} /></TableCell>)}</TableRow>)}
            {!loading && message?.type !== 'error' && patients.length === 0 && (
              <TableRow role="row" className="registry-empty-row">
                <TableCell colSpan={7}>
                  <Box sx={{ py: 6, textAlign: 'center' }}>
                    <Typography fontWeight={600}>{searchTerm.trim() ? '找不到符合的病患' : '從第一位病患開始'}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{searchTerm.trim() ? '試試其他姓名或病歷號碼，或清除搜尋條件。' : canWrite ? '新增病患資料，或透過資料匯入整理既有健檢紀錄。' : '目前沒有可查看的授權病患資料。'}</Typography>
                    {searchTerm.trim() && <Button onClick={clearSearch} sx={{ mt: 2 }}>清除搜尋</Button>}
                  </Box>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <div className="registry-pagination"><Typography variant="caption" color="text.secondary">{resultCount !== null ? '第 ' + page + ' 頁 · 本頁 ' + patients.length + ' 位' : '以授權範圍內的病患資料為準'}</Typography><Stack direction="row" spacing={1}><Button size="small" disabled={loading || page === 1} onClick={() => setPage(current => current - 1)}>上一頁</Button><Button size="small" disabled={loading || !hasNext} onClick={() => setPage(current => current + 1)}>下一頁</Button></Stack></div>
      {message?.type === 'error' && <Button variant="outlined" onClick={() => fetchPatients(searchTerm, page)}>重新載入清單</Button>}
      <Dialog open={dialogOpen} onClose={() => { if (!saving) setDialogOpen(false); }} fullWidth maxWidth="md" transitionDuration={reducedMotion ? 0 : undefined} aria-labelledby="new-patient-title" aria-describedby="new-patient-description" slotProps={{ paper: { sx: { overflow: 'hidden' } }, transition: { onEntered: () => firstNameInput.current?.focus() } }}>
        <Box component="form" onSubmit={savePatient} aria-busy={saving} sx={{ display: 'flex', flexDirection: 'column', flex: '1 1 auto', minHeight: 0, overflow: 'hidden' }}>
        <DialogTitle id="new-patient-title">新增病患</DialogTitle>
        <DialogContent dividers>
          <Typography id="new-patient-description" variant="body2" color="text.secondary" sx={{ mb: 3 }}>建立基本資料，開始累積照護紀錄。標示 * 的欄位為必填。</Typography>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
          <Box className="form-grid">
            <TextField autoFocus inputRef={firstNameInput} disabled={saving} label="名" value={formData.first_name} onChange={(event) => updateField('first_name', event.target.value)} required />
            <TextField disabled={saving} label="姓" value={formData.last_name} onChange={(event) => updateField('last_name', event.target.value)} required />
            <TextField disabled={saving} label="中間名" value={formData.middle_name} onChange={(event) => updateField('middle_name', event.target.value)} />
            <TextField disabled={saving} label="出生日期" type="date" value={formData.date_of_birth} onChange={(event) => updateField('date_of_birth', event.target.value)} InputLabelProps={{ shrink: true }} required />
            <TextField disabled={saving} label="性別" select value={formData.sex} onChange={(event) => updateField('sex', event.target.value)}>
              <MenuItem value="">未填寫</MenuItem>
              <MenuItem value="F">女</MenuItem>
              <MenuItem value="M">男</MenuItem>
              <MenuItem value="O">其他</MenuItem>
              <MenuItem value="U">未知</MenuItem>
            </TextField>
            <TextField disabled={saving} label="MRN" value={formData.medical_record_number} onChange={(event) => updateField('medical_record_number', event.target.value)} />
            <TextField disabled={saving} label="電話" value={formData.phone_number} onChange={(event) => updateField('phone_number', event.target.value)} />
            <TextField disabled={saving} label="Email" type="email" value={formData.email_address} onChange={(event) => updateField('email_address', event.target.value)} />
            <TextField disabled={saving} className="full-span" label="地址" value={formData.current_address_line1} onChange={(event) => updateField('current_address_line1', event.target.value)} />
            <TextField disabled={saving} label="城市" value={formData.city} onChange={(event) => updateField('city', event.target.value)} />
            <TextField disabled={saving} label="州/縣市" value={formData.state} onChange={(event) => updateField('state', event.target.value)} />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={saving}>取消</Button>
          <Button variant="contained" type="submit" disabled={saving || !formData.first_name || !formData.last_name || !formData.date_of_birth}>
            {saving ? '儲存中' : '儲存'}
          </Button>
        </DialogActions>
        </Box>
      </Dialog>
    </Box>
  );
}

export default PatientManagement;
