import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
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
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import RefreshIcon from '@mui/icons-material/Refresh';
import SearchIcon from '@mui/icons-material/Search';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage, displayValue, listFromResponse } from '../utils/apiData';

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
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState(emptyPatient);
  const navigate = useNavigate();

  const fetchPatients = useCallback(async (search = '') => {
    setLoading(true);
    setMessage(null);
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      const endpoint = `${API_CONFIG.ENDPOINTS.PATIENTS}${params.toString() ? `?${params.toString()}` : ''}`;
      const response = await api.get(endpoint);
      const payload = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(payload, '病患清單讀取失敗'));
      setPatients(listFromResponse(payload));
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPatients('');
  }, [fetchPatients]);

  useEffect(() => {
    const timer = setTimeout(() => fetchPatients(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [fetchPatients, searchTerm]);

  const patientCount = useMemo(() => patients.length, [patients]);

  const updateField = (field, value) => {
    setFormData((current) => ({ ...current, [field]: value }));
  };

  const savePatient = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.PATIENTS, formData);
      const payload = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(payload, '新增病患失敗'));
      setDialogOpen(false);
      setFormData(emptyPatient);
      await fetchPatients(searchTerm);
      setMessage({ type: 'success', text: '病患已新增' });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box className="page-frame">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">病患</Typography>
          <Typography variant="h4">病患管理</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            查詢與新增後端 Patient API 的病患資料。
          </Typography>
        </Box>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => fetchPatients(searchTerm)} disabled={loading}>
            重新整理
          </Button>
          <Button variant="contained" startIcon={<AddCircleOutlineIcon />} onClick={() => setDialogOpen(true)}>
            新增病患
          </Button>
        </Stack>
      </Box>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Paper className="registry-toolbar">
        <TextField
          label="搜尋姓名或 MRN"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          size="small"
          fullWidth
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        <Chip label={`${patientCount} 筆`} variant="outlined" />
      </Paper>

      <TableContainer component={Paper} className="data-table">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>病患</TableCell>
              <TableCell>MRN</TableCell>
              <TableCell>出生日期</TableCell>
              <TableCell>性別</TableCell>
              <TableCell>電話</TableCell>
              <TableCell>狀態</TableCell>
              <TableCell align="right">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {patients.map((patient) => (
              <TableRow key={patient.id} hover onClick={() => navigate(`/patients/${patient.id}`)} sx={{ cursor: 'pointer' }}>
                <TableCell>
                  <Typography fontWeight={900}>{patientName(patient)}</Typography>
                  <Typography variant="caption" color="text.secondary">{displayValue(patient.email_address)}</Typography>
                </TableCell>
                <TableCell>{displayValue(patient.medical_record_number)}</TableCell>
                <TableCell>
                  {displayValue(patient.date_of_birth)}
                  {patient.age !== null && patient.age !== undefined && (
                    <Typography variant="caption" color="text.secondary" display="block">{patient.age} 歲</Typography>
                  )}
                </TableCell>
                <TableCell>{displayValue(patient.sex)}</TableCell>
                <TableCell>{displayValue(patient.phone_number)}</TableCell>
                <TableCell><Chip size="small" label={patient.status || '無資料'} color="success" variant="outlined" /></TableCell>
                <TableCell align="right">
                  <Tooltip title="開啟病患">
                    <IconButton size="small" onClick={(event) => { event.stopPropagation(); navigate(`/patients/${patient.id}`); }}>
                      <ChevronRightIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {!loading && patients.length === 0 && (
              <TableRow>
                <TableCell colSpan={7}>
                  <Box sx={{ py: 6, textAlign: 'center' }}>
                    <Typography fontWeight={900}>後端目前沒有回傳病患資料</Typography>
                    <Typography variant="body2" color="text.secondary">請新增病患或先匯入 H2U CVD 檔案。</Typography>
                  </Box>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>新增病患</DialogTitle>
        <DialogContent dividers>
          <Box className="form-grid">
            <TextField label="名" value={formData.first_name} onChange={(event) => updateField('first_name', event.target.value)} required />
            <TextField label="姓" value={formData.last_name} onChange={(event) => updateField('last_name', event.target.value)} required />
            <TextField label="中間名" value={formData.middle_name} onChange={(event) => updateField('middle_name', event.target.value)} />
            <TextField label="出生日期" type="date" value={formData.date_of_birth} onChange={(event) => updateField('date_of_birth', event.target.value)} InputLabelProps={{ shrink: true }} required />
            <TextField label="性別" select value={formData.sex} onChange={(event) => updateField('sex', event.target.value)}>
              <MenuItem value="">未填寫</MenuItem>
              <MenuItem value="F">F</MenuItem>
              <MenuItem value="M">M</MenuItem>
              <MenuItem value="U">U</MenuItem>
            </TextField>
            <TextField label="MRN" value={formData.medical_record_number} onChange={(event) => updateField('medical_record_number', event.target.value)} />
            <TextField label="電話" value={formData.phone_number} onChange={(event) => updateField('phone_number', event.target.value)} />
            <TextField label="Email" type="email" value={formData.email_address} onChange={(event) => updateField('email_address', event.target.value)} />
            <TextField className="full-span" label="地址" value={formData.current_address_line1} onChange={(event) => updateField('current_address_line1', event.target.value)} />
            <TextField label="城市" value={formData.city} onChange={(event) => updateField('city', event.target.value)} />
            <TextField label="州/縣市" value={formData.state} onChange={(event) => updateField('state', event.target.value)} />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>取消</Button>
          <Button variant="contained" onClick={savePatient} disabled={saving || !formData.first_name || !formData.last_name || !formData.date_of_birth}>
            {saving ? '儲存中' : '儲存'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default PatientManagement;
