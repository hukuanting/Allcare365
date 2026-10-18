import { useAuth } from '../hooks/useAuth';
import { hasAnyRole, CLINICAL_WRITE_ROLES } from '../utils/roles';
import React, { useEffect, useState } from 'react';
import { Link as RouterLink, useLocation, useParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Skeleton from '@mui/material/Skeleton';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import TabScrollButton from '@mui/material/TabScrollButton';

function ChartTabScrollButton(props) {
  return <TabScrollButton {...props} component="button" type="button" disabled={props.disabled} aria-label={props.direction === 'left' ? '顯示前面的病歷分類' : '顯示後面的病歷分類'} sx={{ minWidth: 44 }} />;
}

import Typography from '@mui/material/Typography';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import EditNoteIcon from '@mui/icons-material/EditNote';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage, displayValue } from '../utils/apiData';

const sections = [
  { id: 'summary', label: '摘要' },
  { id: 'allergies', label: '過敏', field: 'allergies' },
  { id: 'orders', label: '醫囑', field: 'medical_orders' },
  { id: 'medications', label: '用藥', field: 'medications' },
  { id: 'care-team', label: '照護團隊', field: 'care_team' },
  { id: 'documents', label: '文件', field: 'clinical_notes' },
];
const list = value => Array.isArray(value) ? value : [];
const statusLabels = { active: '使用中', inactive: '已停用', deceased: '已故', research: '研究個案' };
const orderLabels = { medication: '用藥醫囑', laboratory: '檢驗醫囑', diagnostic_imaging: '影像檢查', clinical_test: '臨床檢查', procedure: '處置', portable: '攜帶式醫囑' };
const noteLabels = { consultation: '會診紀錄', discharge_summary: '出院摘要', emergency: '急診紀錄', history_physical: '病史與理學檢查', operative: '手術紀錄', procedure: '處置紀錄', progress: '病程紀錄' };

function DetailRow({ label, value }) {
  return <div className="chart-detail"><dt>{label}</dt><dd>{displayValue(value, '未提供')}</dd></div>;
}
function EmptyRecords({ label }) {
  return <div className="chart-empty"><span className="atlas-eyebrow">RECORDS</span><Typography component="h3" variant="h6">尚無{label}紀錄</Typography><Typography variant="body2" color="text.secondary">此病歷尚未提供相關資料。</Typography></div>;
}

export default function PatientChart() {
  const location = useLocation();
  const { userInfo } = useAuth();
  const canWrite = hasAnyRole(userInfo, CLINICAL_WRITE_ROLES);
  const { patientId } = useParams();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const [tab, setTab] = useState('summary');
  useEffect(() => { setTab('summary'); }, [patientId]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setResult(null);
    (async () => {
      try {
        const response = await api.get(API_CONFIG.ENDPOINTS.PATIENTS + patientId + '/', { signal: controller.signal });
        const payload = await parseApiResponse(response);
        if (controller.signal.aborted) return;
        if (!response.ok) throw new Error(apiErrorMessage(payload, '無法讀取此病歷，請確認存取權限或稍後重試。'));
        if (!payload || typeof payload !== 'object' || Array.isArray(payload) || String(payload.id) !== String(patientId)) throw new Error('病歷資料格式不完整，請重新載入。');
        setResult({ patientId, patient: payload });
      } catch (requestError) {
        if (!controller.signal.aborted) setError(requestError.message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [patientId, reload]);
  // Bind records to the route even before the next effect clears prior state.
  const patient = result?.patientId === patientId ? result.patient : null;
  const back = <Button component={RouterLink} to="/patients" state={{ patientList: location.state?.patientList }} startIcon={<ArrowBackIcon />} sx={{ mb: 2 }}>返回病患清單</Button>;
  if (loading || (!error && !patient)) return <Box className="page-frame atlas-chart">{back}<div role="status" aria-label="載入病歷" className="chart-loading"><Typography color="text.secondary">正在讀取病歷紀錄…</Typography><Skeleton animation={false} height={120} /><Skeleton animation={false} height={56} /><Skeleton animation={false} height={240} /></div></Box>;
  if (error) return <Box className="page-frame atlas-chart">{back}<Paper className="work-panel"><Typography component="h1" variant="h5" sx={{ mb: 2 }}>病歷暫時無法載入</Typography><Alert severity="error">{error}</Alert><Button variant="outlined" sx={{ mt: 3 }} onClick={() => setReload(value => value + 1)}>重新載入病歷</Button></Paper></Box>;
  const fullName = patient.full_name || [patient.last_name, patient.first_name].filter(Boolean).join(' ') || '未提供姓名';
  const address = [patient.current_address_line1, patient.city, patient.state].filter(Boolean).join('，');
  const activeSection = sections.find(section => section.id === tab) || sections[0];
  const tabId = 'chart-tab-' + tab;
  const records = list(patient[activeSection.field]);
  return <Box className="page-frame atlas-chart">
    {back}
    {patient.is_demo_patient && <Alert severity="info" sx={{ mb: 2 }}>{patient.demo_label || '展示用合成病患'} · 合成測試資料</Alert>}
    <Paper className="chart-header">
      <div className="chart-identity"><span className="atlas-eyebrow">PATIENT RECORD</span><Typography component="h1" variant="h4">{fullName}</Typography><div className="chart-identifiers"><span className="chart-mrn">MRN {displayValue(patient.medical_record_number, '未提供')}</span><span>{patient.age === null || patient.age === undefined ? '年齡未提供' : patient.age + ' 歲'}</span><span>{({ M: '男', F: '女', O: '其他', U: '性別未提供' })[patient.sex] || displayValue(patient.sex, '性別未提供')}</span><Chip size="small" label={statusLabels[patient.status] || patient.status || '狀態未提供'} color={patient.status === 'active' ? 'success' : 'default'} variant="outlined" /></div></div>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>{canWrite && <Button component={RouterLink} to={'/health-data-input?patient_id=' + encodeURIComponent(patient.id)} variant="outlined" startIcon={<EditNoteIcon />}>新增健檢</Button>}<Button component={RouterLink} to={'/risk-analysis?patient_id=' + encodeURIComponent(patient.id)} variant="contained" startIcon={<AnalyticsIcon />}>風險分析</Button><Button component={RouterLink} to={'/disease-network?patient_id=' + encodeURIComponent(patient.id)} variant="outlined">疾病網絡</Button></Stack>
    </Paper>
    <div className="chart-tabs"><Tabs value={tab} onChange={(_event, next) => setTab(next)} variant="scrollable" scrollButtons="auto" allowScrollButtonsMobile slots={{ scrollButtons: ChartTabScrollButton }} aria-label="病歷分類">{sections.map(section => <Tab key={section.id} id={'chart-tab-' + section.id} aria-controls={'chart-panel-' + section.id} value={section.id} label={section.label + (section.field ? ' ' + list(patient[section.field]).length : '')} />)}</Tabs></div>
    <section role="tabpanel" id={'chart-panel-' + tab} aria-labelledby={tabId} tabIndex={0}>
      {tab === 'summary' ? <div className="chart-grid">
        <Paper className="work-panel"><div className="panel-heading"><Typography component="h2" variant="h6">基本資料</Typography><span className="atlas-eyebrow">01 / PROFILE</span></div><dl className="chart-profile"><DetailRow label="出生日期" value={patient.date_of_birth} /><DetailRow label="電話" value={patient.phone_number} /><DetailRow label="Email" value={patient.email_address} /><DetailRow label="地址" value={address} /></dl></Paper>
        <Paper className="work-panel"><div className="panel-heading"><Typography component="h2" variant="h6">病歷索引</Typography><span className="atlas-eyebrow">02 / RECORDS</span></div><div className="chart-index">{sections.filter(section => section.field).map(section => <button key={section.id} onClick={() => { setTab(section.id); document.getElementById('chart-tab-' + section.id)?.focus(); }}><span>{section.label}</span><b>{list(patient[section.field]).length}</b><span aria-hidden="true">↗</span></button>)}</div></Paper>
        <Paper className="work-panel chart-allergy-summary"><div className="panel-heading"><Typography component="h2" variant="h6">過敏紀錄</Typography><Button onClick={() => { setTab('allergies'); document.getElementById('chart-tab-allergies')?.focus(); }}>查看全部</Button></div>{list(patient.allergies).length ? <ul className="chart-record-list">{list(patient.allergies).slice(0,3).map((allergy,index) => <li key={allergy.id || index}><strong>{displayValue(allergy.substance, '物質未提供')}</strong><p>{displayValue(allergy.reaction, '反應未提供')}</p></li>)}</ul> : <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>過敏狀態待補充。</Typography>}</Paper>
      </div> : <Paper className="work-panel"><div className="panel-heading"><Typography component="h2" variant="h6">{activeSection.label}</Typography><Typography variant="caption" color="text.secondary">{records.length} 筆紀錄</Typography></div>{records.length ? <ul className="chart-record-list">{records.map((record,index) => <li key={record.id || index}>
        {tab === 'allergies' && <><strong>{displayValue(record.substance, '物質未提供')}</strong><dl className="chart-record-details"><DetailRow label="反應" value={record.reaction} /><DetailRow label="嚴重程度" value={record.severity} /></dl></>}
        {tab === 'orders' && <><strong>{orderLabels[record.order_type] || displayValue(record.order_type)}</strong><p>{displayValue(record.order_detail)}</p><small>紀錄時間 · {displayValue(record.order_date)}</small></>}
        {tab === 'medications' && <><strong>{displayValue(record.medication)}</strong><p>{displayValue(record.medication_instructions || record.indication)}</p><dl className="chart-record-details"><DetailRow label="給藥途徑" value={record.route_of_administration} /><DetailRow label="開始日期" value={record.start_date} /><DetailRow label="結束日期" value={record.end_date} /><DetailRow label="狀態" value={record.dispense_status} /></dl></>}
        {tab === 'care-team' && <><strong>{displayValue(record.name)}</strong><p>{displayValue(record.role)}</p><small>聯絡方式 · {displayValue(record.telecom)}</small></>}
        {tab === 'documents' && <><strong>{noteLabels[record.note_type] || displayValue(record.note_type)}</strong><small>紀錄時間 · {displayValue(record.document_date)}</small><p className="chart-note-content">{displayValue(record.content, '尚未提供文件內容')}</p></>}
      </li>)}</ul> : <EmptyRecords label={activeSection.label} />}{tab === 'allergies' && !records.length && <Typography variant="caption" color="text.secondary">補充過敏物質與反應，更新照護紀錄。</Typography>}</Paper>}
    </section>
  </Box>;
}
