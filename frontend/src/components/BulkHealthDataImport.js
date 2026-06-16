import React, { useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TextField from '@mui/material/TextField';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Typography from '@mui/material/Typography';
import DownloadIcon from '@mui/icons-material/Download';
import FileUploadIcon from '@mui/icons-material/FileUpload';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import VisibilityIcon from '@mui/icons-material/Visibility';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage } from '../utils/apiData';

const csvHeaderTemplate = [
  'ID,BirthDate,SEX,CheckDate,Height,Weight,SBP,DBP,PulseRate,FPG,HbA1C,TC,HDL,LDL,TG,Creatinine,HQ_SMOKE,HQ_Diabetes,HQ_BP_Treat,HQ_Exercise',
].join('\n');

const parseFhirSummary = (raw) => {
  const parsed = JSON.parse(raw);
  const resources = parsed.resourceType === 'Bundle'
    ? (parsed.entry || []).map((entry) => entry.resource).filter(Boolean)
    : [parsed];
  return {
    totalResources: resources.length,
    byType: resources.reduce((acc, resource) => {
      acc[resource.resourceType || 'Unknown'] = (acc[resource.resourceType || 'Unknown'] || 0) + 1;
      return acc;
    }, {}),
  };
};

function BulkHealthDataImport() {
  const [mode, setMode] = useState('file');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [fhirText, setFhirText] = useState('');
  const [fhirPreview, setFhirPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);

  const previewRows = useMemo(() => preview?.sample_data || [], [preview]);

  const reset = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setFhirText('');
    setFhirPreview(null);
    setMessage(null);
  };

  const downloadTemplate = () => {
    const blob = new Blob([csvHeaderTemplate], { type: 'text/csv;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'h2u_cvd_columns_template.csv';
    link.click();
    window.URL.revokeObjectURL(url);
  };

  const handleFile = (selectedFile) => {
    setFile(selectedFile);
    setPreview(null);
    setResult(null);
    setMessage(null);
  };

  const previewFile = async () => {
    if (!file) return;
    setBusy(true);
    setMessage(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await api.upload(API_CONFIG.ENDPOINTS.PARSE_FILE, formData);
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, '檔案預覽失敗'));
      setPreview(data);
      setMessage({ type: 'success', text: `後端已解析 ${data.row_count ?? 0} 筆資料` });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setBusy(false);
    }
  };

  const importFile = async () => {
    if (!file) return;
    setBusy(true);
    setMessage(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await api.upload(API_CONFIG.ENDPOINTS.BULK_IMPORT, formData);
      const data = await parseApiResponse(response);
      if (!response.ok && response.status !== 207) throw new Error(apiErrorMessage(data, '檔案匯入失敗'));
      setResult(data);
      setMessage({ type: data.error_count ? 'warning' : 'success', text: '匯入流程已完成' });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setBusy(false);
    }
  };

  const previewFhir = () => {
    setMessage(null);
    try {
      setFhirPreview(parseFhirSummary(fhirText));
    } catch (error) {
      setFhirPreview(null);
      setMessage({ type: 'error', text: `FHIR JSON 格式錯誤：${error.message}` });
    }
  };

  const importFhir = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const parsed = JSON.parse(fhirText);
      const response = await api.post(API_CONFIG.ENDPOINTS.FHIR_IMPORT, { fhir_data: parsed, format: 'json' });
      const data = await parseApiResponse(response);
      if (!response.ok && response.status !== 207) throw new Error(apiErrorMessage(data, 'FHIR 匯入失敗'));
      setResult(data);
      setMessage({ type: data.error_count ? 'warning' : 'success', text: 'FHIR 匯入流程已完成' });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box className="page-frame">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">資料匯入</Typography>
          <Typography variant="h4">臨床資料匯入</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            將 CSV、Excel 或 FHIR JSON 送至後端解析與寫入；畫面只顯示後端回傳的結果。
          </Typography>
        </Box>
        <Button variant="outlined" startIcon={<DownloadIcon />} onClick={downloadTemplate}>
          下載欄位表頭
        </Button>
      </Box>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Paper className="work-panel">
        <Stack spacing={3}>
          <ToggleButtonGroup
            value={mode}
            exclusive
            onChange={(_event, value) => {
              if (value) {
                setMode(value);
                reset();
              }
            }}
            size="small"
          >
            <ToggleButton value="file">CSV / Excel</ToggleButton>
            <ToggleButton value="fhir">FHIR JSON</ToggleButton>
          </ToggleButtonGroup>

          <Divider />

          {mode === 'file' && (
            <Stack spacing={3}>
              <Box>
                <Typography variant="h6">檔案匯入</Typography>
                <Typography variant="body2" color="text.secondary">
                  選擇本機檔案後，可先交給後端預覽欄位與列數，再正式寫入資料庫。
                </Typography>
              </Box>
              <Button component="label" variant="outlined" startIcon={<FileUploadIcon />} sx={{ alignSelf: 'flex-start' }}>
                選擇檔案
                <input hidden type="file" accept=".csv,.xlsx,.xls" onChange={(event) => handleFile(event.target.files?.[0] || null)} />
              </Button>
              {file && <Alert severity="info" variant="outlined">{file.name} ({(file.size / 1024).toFixed(1)} KB)</Alert>}
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <Button variant="contained" startIcon={<VisibilityIcon />} onClick={previewFile} disabled={!file || busy}>預覽</Button>
                <Button variant="outlined" startIcon={<FileUploadIcon />} onClick={importFile} disabled={!file || busy}>匯入</Button>
                <Button startIcon={<RestartAltIcon />} onClick={reset} disabled={busy}>清除</Button>
              </Stack>
            </Stack>
          )}

          {mode === 'fhir' && (
            <Stack spacing={3}>
              <Box>
                <Typography variant="h6">FHIR 匯入</Typography>
                <Typography variant="body2" color="text.secondary">
                  貼上真實的 FHIR JSON resource 或 Bundle，前端只做 JSON 格式檢查，寫入由後端處理。
                </Typography>
              </Box>
              <TextField
                value={fhirText}
                onChange={(event) => {
                  setFhirText(event.target.value);
                  setFhirPreview(null);
                  setResult(null);
                }}
                minRows={12}
                multiline
                fullWidth
              />
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <Button variant="contained" startIcon={<VisibilityIcon />} onClick={previewFhir} disabled={!fhirText.trim() || busy}>預覽</Button>
                <Button variant="outlined" startIcon={<FileUploadIcon />} onClick={importFhir} disabled={!fhirText.trim() || busy}>匯入</Button>
                <Button startIcon={<RestartAltIcon />} onClick={reset} disabled={busy}>清除</Button>
              </Stack>
            </Stack>
          )}
        </Stack>
      </Paper>

      {preview && (
        <Paper className="work-panel" sx={{ mt: 2 }}>
          <Typography variant="h6">後端檔案預覽</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {preview.row_count ?? 0} 筆資料，{preview.headers?.length ?? 0} 個欄位
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {(preview.headers || []).map((header) => <TableCell key={header}>{header}</TableCell>)}
                </TableRow>
              </TableHead>
              <TableBody>
                {previewRows.map((row, index) => (
                  <TableRow key={`${index}-${row.ID || row.patient_id || 'row'}`}>
                    {(preview.headers || []).map((header) => <TableCell key={header}>{row[header] ?? ''}</TableCell>)}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {fhirPreview && (
        <Paper className="work-panel" sx={{ mt: 2 }}>
          <Typography variant="h6">FHIR 預覽</Typography>
          <Typography variant="body2" color="text.secondary">{fhirPreview.totalResources} 個 resource</Typography>
          <Box className="surface-grid" sx={{ mt: 2 }}>
            {Object.entries(fhirPreview.byType).map(([resourceType, count]) => (
              <Paper key={resourceType} variant="outlined" sx={{ p: 2 }}>
                <Typography variant="caption" color="text.secondary">{resourceType}</Typography>
                <Typography variant="h5">{count}</Typography>
              </Paper>
            ))}
          </Box>
        </Paper>
      )}

      {result && (
        <Paper className="work-panel" sx={{ mt: 2 }}>
          <Stack spacing={2}>
            <Typography variant="h6">後端匯入結果</Typography>
            <Box className="surface-grid">
              <Paper variant="outlined" sx={{ p: 2 }}><Typography variant="caption">成功</Typography><Typography variant="h5">{result.success_count ?? 0}</Typography></Paper>
              <Paper variant="outlined" sx={{ p: 2 }}><Typography variant="caption">錯誤</Typography><Typography variant="h5">{result.error_count ?? 0}</Typography></Paper>
              <Paper variant="outlined" sx={{ p: 2 }}><Typography variant="caption">總數</Typography><Typography variant="h5">{result.total_count ?? 0}</Typography></Paper>
            </Box>
            {Array.isArray(result.errors) && result.errors.length > 0 && (
              <Alert severity="warning">
                {result.errors.slice(0, 5).map((error, index) => (
                  <Box key={`${index}-${error.row || 'error'}`}>Row {error.row || index + 1}: {error.error || error}</Box>
                ))}
              </Alert>
            )}
          </Stack>
        </Paper>
      )}
    </Box>
  );
}

export default BulkHealthDataImport;
