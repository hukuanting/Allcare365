import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
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
import AnalyticsIcon from '@mui/icons-material/Analytics';
import { Link as RouterLink } from 'react-router-dom';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage, displayValue } from '../utils/apiData';

const csvHeaderTemplate = [
  'ID,BirthDate,SEX,CheckDate,Height,Weight,SBP,DBP,PulseRate,FPG,HbA1C,TC,HDL,LDL,TG,Creatinine,HQ_SMOKE,HQ_Diabetes,HQ_BP_Treat,HQ_Exercise',
].join('\n');

const resourceLabels = { Patient: '病患資料', Encounter: '就診紀錄', Observation: '檢驗與量測', Condition: '診斷與病史', QuestionnaireResponse: '問卷作答', AllergyIntolerance: '過敏紀錄', MedicationRequest: '用藥處方', DiagnosticReport: '檢查報告', DocumentReference: '文件索引', Provenance: '資料來源' };

const fhirUrlError = value => {
  if (!value.trim()) return '';
  try {
    const url = new URL(value.trim());
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname) return '請輸入以 https:// 或 http:// 開頭的完整 FHIR URL。';
    if (url.username || url.password || url.hash) return '請移除網址中的帳密與 # 片段；授權資訊請填在 Access token 欄位。';
    return '';
  } catch { return '請輸入以 https:// 或 http:// 開頭的完整 FHIR URL。'; }
};

const importErrorText = error => typeof error === 'string' ? error : error?.error || error?.detail || '匯入失敗，請檢查來源資料。';

function BulkHealthDataImport() {
  const csvPreviewHeading = useRef(null);
  const fhirPreviewHeading = useRef(null);
  const resultHeading = useRef(null);
  const errorNotice = useRef(null);
  const [mode, setMode] = useState('fhir');
  const formatPanelId = useId();
  const importErrorsId = useId();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [fhirText, setFhirText] = useState('');
  const [fhirSource, setFhirSource] = useState('paste');
  const [fhirFiles, setFhirFiles] = useState([]);
  const [fhirUrl, setFhirUrl] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const fhirFileInput = useRef(null);
  const fhirFilePicker = useRef(null);
  const restoreFilePickerFocus = useRef(false);
  const operationLock = useRef(false);
  const [fhirPreview, setFhirPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [processingText, setProcessingText] = useState('');
  const [message, setMessage] = useState(null);
  const fileInput = useRef(null);
  const [showAllErrors, setShowAllErrors] = useState(false);

  const previewPatients = useMemo(() => {
    const data = fhirPreview?.fhir_data;
    const resources = data?.resourceType === 'Bundle' ? (data.entry || []).map(entry => entry.resource) : [data];
    return resources.filter(resource => resource?.resourceType === 'Patient');
  }, [fhirPreview]);

  const previewRows = useMemo(() => preview?.sample_data || [], [preview]);
  const analysisPatientId = result?.primary_patient_id
    || (result?.patient_ids?.length === 1 ? result.patient_ids[0] : '');

  useEffect(() => {
    const heading = result ? resultHeading.current : fhirPreview ? fhirPreviewHeading.current : preview ? csvPreviewHeading.current : null;
    if (heading) {
      heading.focus({ preventScroll: true });
      heading.scrollIntoView?.({ block: 'start', behavior: 'instant' });
    }
  }, [preview, fhirPreview, result]);

  useEffect(() => {
    if (restoreFilePickerFocus.current) {
      restoreFilePickerFocus.current = false;
      fhirFilePicker.current?.focus();
    }
  }, [fhirFiles]);

  useEffect(() => {
    if (message?.type === 'error' && errorNotice.current) {
      errorNotice.current.focus({ preventScroll: true });
      errorNotice.current.scrollIntoView?.({ block: 'start', behavior: 'instant' });
    }
  }, [message]);

  const reset = () => {
    if (busy || operationLock.current) return;
    if (fileInput.current) fileInput.current.value = '';
    setShowAllErrors(false);
    setFile(null);
    setPreview(null);
    setResult(null);
    setFhirText('');
    setFhirFiles([]);
    setFhirUrl('');
    setAccessToken('');
    if (fhirFileInput.current) fhirFileInput.current.value = '';
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
    if (busy || operationLock.current) return;
    setFile(selectedFile);
    setPreview(null);
    setResult(null);
    setMessage(null);
  };

  const previewFile = async () => {
    if (!file || busy || operationLock.current) return;
    setPreview(null);
    setResult(null);
    setShowAllErrors(false);
    operationLock.current = true;
    setProcessingText('正在讀取檔案並建立預覽…');
    setBusy(true);
    setMessage(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await api.upload(API_CONFIG.ENDPOINTS.PARSE_FILE, formData);
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, '檔案預覽失敗'));
      setPreview(data);
      setMessage({ type: 'success', text: `已解析 ${data.row_count ?? 0} 筆資料` });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      operationLock.current = false;
      setBusy(false);
    }
  };

  const importFile = async () => {
    if (!file || !preview || busy || operationLock.current || result) return;
    operationLock.current = true;
    setProcessingText('正在將資料寫入系統…');
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
      operationLock.current = false;
      setBusy(false);
    }
  };

  const invalidateFhir = () => {
    setMessage(null);
    setFhirPreview(null);
    setResult(null);
    setShowAllErrors(false);
  };

  const removeFhirFile = index => {
    if (busy || operationLock.current) return;
    restoreFilePickerFocus.current = true;
    invalidateFhir();
    setFhirFiles(current => current.filter((_, position) => position !== index));
    if (fhirFileInput.current) fhirFileInput.current.value = '';
  };

  const urlError = fhirUrlError(fhirUrl);
  const fhirReady = fhirSource === 'files' ? fhirFiles.length > 0
    : fhirSource === 'api' ? Boolean(fhirUrl.trim()) && !urlError : Boolean(fhirText.trim());

  const previewFhir = async () => {
    if (busy || operationLock.current || !fhirReady) return;
    setResult(null);
    setShowAllErrors(false);
    operationLock.current = true;
    setProcessingText('正在讀取 FHIR 資料並建立預覽…');
    setBusy(true);
    setMessage(null);
    setFhirPreview(null);
    try {
      let response;
      if (fhirSource === 'files') {
        if (fhirFiles.length > 20 || fhirFiles.reduce((sum, item) => sum + item.size, 0) > 10 * 1024 * 1024) {
          throw new Error('單次最多 20 個檔案，總大小不得超過 10 MB。');
        }
        const formData = new FormData();
        fhirFiles.forEach(item => formData.append('files', item));
        response = await api.upload(API_CONFIG.ENDPOINTS.FHIR_PREVIEW, formData);
      } else {
        response = await api.post(API_CONFIG.ENDPOINTS.FHIR_PREVIEW, fhirSource === 'api'
          ? { url: fhirUrl.trim(), access_token: accessToken }
          : { fhir_data: fhirText, format: 'auto' });
      }
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, 'FHIR 預覽失敗'));
      if (!data.fhir_data || !data.totalResources) throw new Error('來源未提供可匯入的 FHIR 資源。');
      setFhirPreview(data);
    } catch (error) {
      let text = error.message;
      if (/衝突的 fullUrl/.test(text)) text += ' 請檢查是否選取同一份資料的不同格式版本；保留其中一份，或修正資源網址衝突後重新預覽。';
      if (fhirSource === 'api' && /HTTP 401/.test(text)) text += ' 請在 Access token 欄位提供來源 API 的有效 token，再重新預覽。';
      if (fhirSource === 'api' && /HTTP 403/.test(text)) text += ' 請確認來源 API 帳號具有讀取這份資料的權限，再重新預覽。';
      setMessage({ type: 'error', text });
    } finally {
      setAccessToken('');
      operationLock.current = false;
      setBusy(false);
    }
  };

  const importFhir = async () => {
    if (busy || operationLock.current || !fhirPreview || result) return;
    operationLock.current = true;
    setProcessingText('正在將 FHIR 資料寫入系統…');
    setBusy(true);
    setMessage(null);
    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.FHIR_IMPORT, { fhir_data: fhirPreview.fhir_data, format: 'json' });
      const data = await parseApiResponse(response);
      if (!response.ok && response.status !== 207) throw new Error(apiErrorMessage(data, 'FHIR 匯入失敗'));
      setResult(data);
      setMessage({
        type: data.error_count ? 'warning' : 'success',
        text: data.error_count ? 'FHIR 匯入完成，部分資源未成功寫入。請檢查下方錯誤。' : 'FHIR 匯入完成，請檢視資料與分析所需欄位。',
      });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      operationLock.current = false;
      setBusy(false);
    }
  };

  return (
    <Box className="page-frame atlas-import" sx={{ '& .MuiToggleButtonGroup-root': { flexWrap: 'wrap' } }}>
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">資料匯入</Typography>
          <Typography component="h1" variant="h4">臨床資料匯入</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            以 FHIR 帶入臨床紀錄：貼上 JSON／XML、上傳多個檔案，或從 FHIR API 讀取。CSV／Excel 可作為補充來源。
          </Typography>
        </Box>
        {mode === 'file' && <Button variant="outlined" startIcon={<DownloadIcon />} onClick={downloadTemplate}>
          下載 CSV 欄位表頭
        </Button>}
      </Box>

      {message && <Alert ref={errorNotice} tabIndex={-1} role={message.type === 'success' ? 'status' : 'alert'} severity={message.type} sx={{ mb: 2, scrollMarginTop: 88 }}>{message.text}</Alert>}

      <ol className="import-steps" aria-label="匯入進度">{['選擇資料', '檢查預覽', '確認匯入'].map((label, index) => <li key={label} aria-current={(result ? 2 : preview || fhirPreview ? 1 : 0) === index ? 'step' : undefined}><span>{'0' + (index + 1)}</span>{label}</li>)}</ol>
      <Paper className="work-panel">
        <Stack spacing={3}>
          <ToggleButtonGroup
            value={mode}
            exclusive
            onChange={(_event, value) => {
              if (value && !busy && !operationLock.current && value !== mode) {
                setMode(value);
                reset();
              }
            }}
            size="small"
            disabled={busy}
            aria-label="匯入格式"
          >
            <ToggleButton aria-controls={formatPanelId} value="fhir">FHIR（主要）</ToggleButton>
            <ToggleButton aria-controls={formatPanelId} value="file">CSV / Excel</ToggleButton>
          </ToggleButtonGroup>

          <Divider />

          {mode === 'file' && (
            <Stack component="section" id={formatPanelId} aria-label="CSV 或 Excel 資料匯入" spacing={3}>
              <Box>
                <Typography component="h2" variant="h6">檔案匯入</Typography>
                <Typography variant="body2" color="text.secondary">
                  選擇 CSV 或 Excel，檢查前 10 筆資料與欄位，再確認寫入。
                </Typography>
              </Box>
              <Button type="button" onClick={() => { if (!operationLock.current) fileInput.current?.click(); }} disabled={busy} variant="outlined" startIcon={<FileUploadIcon />} sx={{ alignSelf: 'flex-start' }}>
                選擇檔案
              </Button>
                <input ref={fileInput} aria-label="選擇匯入檔案" disabled={busy} hidden type="file" accept=".csv,.xlsx,.xls" onChange={(event) => handleFile(event.target.files?.[0] || null)} />
              {file && <Box role="group" aria-label="已選 CSV 或 Excel 檔案" sx={{ display: 'flex', alignItems: 'baseline', flexWrap: 'wrap', gap: 1, py: 1, borderBottom: 1, borderColor: 'divider' }}><Typography variant="body2" sx={{ minWidth: 0, overflowWrap: 'anywhere', flex: '1 1 160px' }}>{file.name}</Typography><Typography variant="caption" color="text.secondary">{(file.size / 1024).toFixed(1)} KB</Typography></Box>}
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <Button variant="contained" startIcon={<VisibilityIcon />} onClick={previewFile} disabled={!file || busy}>預覽</Button>
                {!preview && <Button variant="outlined" startIcon={<FileUploadIcon />} disabled>確認匯入</Button>}
                <Button startIcon={<RestartAltIcon />} onClick={reset} disabled={busy}>清除</Button>
              </Stack>
            </Stack>
          )}

          {mode === 'fhir' && (
            <Stack component="section" id={formatPanelId} aria-label="FHIR 資料匯入" spacing={3}>
              <Box>
                <Typography component="h2" variant="h6">FHIR R4 匯入</Typography>
                <Typography variant="body2" color="text.secondary">
                  支援 JSON 與 XML 資源或 Bundle。先預覽資源摘要，再確認寫入；完整欄位與病人映射由匯入服務檢查。
                </Typography>
              </Box>
              <ToggleButtonGroup value={fhirSource} exclusive size="small" disabled={busy} aria-label="FHIR 資料來源"
                onChange={(_event, value) => { if (value && value !== fhirSource && !busy && !operationLock.current) { reset(); setFhirSource(value); } }}>
                <ToggleButton value="paste">貼上資料</ToggleButton>
                <ToggleButton value="files">上傳多個檔案</ToggleButton>
                <ToggleButton value="api">FHIR REST API</ToggleButton>
              </ToggleButtonGroup>
              {fhirSource === 'paste' && <TextField
                label="FHIR JSON / XML 資料" disabled={busy} value={fhirText}
                onChange={event => { invalidateFhir(); setFhirText(event.target.value); }}
                helperText="自動辨識 JSON 或 XML；XML 請使用 UTF-8 與 FHIR namespace。"
                minRows={12} multiline fullWidth
              />}
              {fhirSource === 'files' && <Stack spacing={2}>
                <Typography variant="body2" color="text.secondary">可同時選取 JSON、XML 或其他副檔名的 FHIR 檔案；依內容辨識。最多 20 個檔案，總大小 10 MB。</Typography>
                <Button ref={fhirFilePicker} type="button" onClick={() => { if (!operationLock.current) fhirFileInput.current?.click(); }} disabled={busy} variant="outlined" startIcon={<FileUploadIcon />} sx={{ alignSelf: 'flex-start' }}>
                  選擇 FHIR 檔案
                </Button>
                  <input ref={fhirFileInput} aria-label="選擇多個 FHIR 檔案" disabled={busy} hidden type="file" multiple
                    onChange={event => { invalidateFhir(); setFhirFiles(Array.from(event.target.files || [])); }} />
                <Typography variant="caption" color="text.secondary" role="status">{fhirFiles.length ? '已選 ' + fhirFiles.length + ' 個 FHIR 檔案' : '尚未選擇 FHIR 檔案'}</Typography>
                {fhirFiles.length > 0 && <Box component="ul" aria-label="已選 FHIR 檔案" sx={{ m: 0, pl: 3 }}>
                  {fhirFiles.map((item, index) => <Box component="li" key={item.name + index} sx={{ display: 'flex', alignItems: 'center', gap: 2, justifyContent: 'space-between' }}><span style={{ minWidth: 0, overflowWrap: 'anywhere' }}>{item.name} · {(item.size / 1024).toFixed(1)} KB</span><Button disabled={busy} onClick={() => removeFhirFile(index)} aria-label={'移除 ' + item.name} sx={{ minHeight: 44, flexShrink: 0 }}>移除</Button></Box>)}
                </Box>}
              </Stack>}
              {fhirSource === 'api' && <Stack spacing={2}>
                <TextField label="FHIR API URL" error={Boolean(urlError)} type="url" disabled={busy} value={fhirUrl} fullWidth
                  onChange={event => { invalidateFhir(); setFhirUrl(event.target.value); }}
                  helperText={urlError || "輸入資源、搜尋或 Patient/$everything 的完整 URL。支援同來源分頁；最多 10 頁、1000 個資源。"} />
                <TextField label="API Access token（如需要）" type="password" disabled={busy} value={accessToken} fullWidth autoComplete="off"
                  onChange={event => { invalidateFhir(); setAccessToken(event.target.value); }}
                  helperText="讀取完成後自動清除金鑰。使用管理員已啟用的 API 來源。" />
              </Stack>}
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <Button variant="contained" startIcon={<VisibilityIcon />} onClick={previewFhir} disabled={!fhirReady || busy}>預覽</Button>
                {!fhirPreview && <Button variant="outlined" startIcon={<FileUploadIcon />} disabled>確認匯入</Button>}
                <Button startIcon={<RestartAltIcon />} onClick={reset} disabled={busy}>清除</Button>
              </Stack>
            </Stack>
          )}

        </Stack>
      </Paper>

      {busy && <Typography role="status" className="import-processing">{processingText}</Typography>}
      {preview && (
        <Paper className="work-panel" sx={{ mt: 2 }}>
          <Typography ref={csvPreviewHeading} tabIndex={-1} component="h2" variant="h6" sx={{ scrollMarginTop: 88 }}>檔案預覽</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {preview.row_count ?? 0} 筆資料，{preview.headers?.length ?? 0} 個欄位
          </Typography>
          <TableContainer role="region" aria-label="匯入檔案樣本捲動區" tabIndex={0}>
            <Table size="small" aria-label="匯入檔案樣本">
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
          <Button variant="contained" startIcon={<FileUploadIcon />} onClick={importFile} disabled={!file || busy || Boolean(result)} sx={{ mt: 3, width: { xs: '100%', sm: 'auto' } }}>確認匯入</Button>
        </Paper>
      )}

      {fhirPreview && (
        <Paper className="work-panel" sx={{ mt: 2 }}>
          <Typography ref={fhirPreviewHeading} tabIndex={-1} component="h2" variant="h6" sx={{ scrollMarginTop: 88 }}>FHIR 預覽</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2 }}>
            共 {fhirPreview.totalResources} 筆資源 · 尚未寫入系統
          </Typography>
          {previewPatients.length > 0 && <Box component="section" aria-label="預覽病患資料" sx={{ mb: 2 }}>
            <Typography component="h3" variant="subtitle2">核對病患資料</Typography>
            <Box component="ul" sx={{ pl: 2.5, my: 1 }}>
              {previewPatients.slice(0, 5).map((patient, index) => {
                const name = patient.name?.find(item => item.use === 'official') || patient.name?.[0];
                const displayName = name?.text || [name?.family, ...(name?.given || [])].filter(Boolean).join(' ') || '姓名未提供';
                const identifiers = (patient.identifier || []).map(item => item.value).filter(Boolean);
                return <Box component="li" key={patient.id || index} sx={{ mb: 1, overflowWrap: 'anywhere' }}>
                  <Typography component="span" variant="body2" sx={{ fontWeight: 600 }}>{displayName}</Typography>
                  <Typography component="p" variant="caption" color="text.secondary">{identifiers.length ? '識別碼：' + identifiers.join(' · ') : '資源 ID：' + (patient.id || '未提供')}</Typography>
                </Box>;
              })}
            </Box>
            {previewPatients.length > 5 && <Typography variant="caption" color="text.secondary">另有 {previewPatients.length - 5} 筆病患資料；本次合計 {previewPatients.length} 筆。</Typography>}
          </Box>}
          <TableContainer role="region" aria-label="FHIR 資源摘要捲動區" tabIndex={0}>
            <Table size="small" aria-label="FHIR 資源摘要">
              <TableHead><TableRow><TableCell>資源內容</TableCell><TableCell>FHIR 類型</TableCell><TableCell align="right">筆數</TableCell></TableRow></TableHead>
              <TableBody>
                {Object.entries(fhirPreview.byType || {}).map(([resourceType, count]) => (
                  <TableRow key={resourceType}>
                    <TableCell component="th" scope="row">{resourceLabels[resourceType] || resourceType}</TableCell>
                    <TableCell sx={{ overflowWrap: 'anywhere' }}>{resourceType}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>{count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Button variant="contained" startIcon={<FileUploadIcon />} onClick={importFhir} disabled={busy || Boolean(result)} sx={{ mt: 3, width: { xs: '100%', sm: 'auto' } }}>確認匯入</Button>
        </Paper>
      )}

      {result && (
        <Paper className="work-panel" sx={{ mt: 2 }}>
          <Stack spacing={2}>
            <Typography ref={resultHeading} tabIndex={-1} component="h2" variant="h6" sx={{ scrollMarginTop: 88 }}>匯入結果</Typography>
            <Box component="dl" className="import-result-summary" aria-label="匯入筆數摘要">
              {[['成功', result.success_count], ['錯誤', result.error_count], ['總數', result.total_count]].map(([label, count]) => (
                <Box key={label}>
                  <Typography component="dt" variant="caption" color="text.secondary">{label}</Typography>
                  <Typography component="dd" variant="h5">{displayValue(count, '未提供')}</Typography>
                </Box>
              ))}
            </Box>
            {Array.isArray(result.errors) && result.errors.length > 0 && (
              <Alert severity="warning" role="group" aria-label="未成功匯入的資料">
                <Box component="ul" id={importErrorsId} sx={{ m: 0, pl: 2.5, '& li': { mb: 0.5, overflowWrap: 'anywhere' } }}>
                  {(showAllErrors ? result.errors : result.errors.slice(0, 5)).map((error, index) => (
                    <Box component="li" key={index}>{error?.row ? '第 ' + error.row + ' 列：' : ''}{importErrorText(error)}</Box>
                  ))}
                </Box>
              </Alert>
            )}
            {result.errors?.length > 5 && <Button aria-expanded={showAllErrors} aria-controls={importErrorsId} onClick={() => setShowAllErrors(value => !value)}>{showAllErrors ? '收合錯誤清單' : '查看全部 ' + result.errors.length + ' 筆錯誤'}</Button>}
            <Button
              variant="contained"
              startIcon={<AnalyticsIcon />}
              sx={{ alignSelf: 'flex-start' }}
              component={RouterLink}
              to={analysisPatientId
                ? `/risk-analysis?patient_id=${encodeURIComponent(analysisPatientId)}`
                : '/risk-analysis'}
            >
              {analysisPatientId ? '分析這位病患的風險' : '前往風險分析'}
            </Button>
          </Stack>
        </Paper>
      )}
    </Box>
  );
}

export default BulkHealthDataImport;
