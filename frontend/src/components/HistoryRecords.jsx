import { useAuth } from '../hooks/useAuth';
import { hasAnyRole, CLINICAL_WRITE_ROLES } from '../utils/roles';
import React, { useEffect, useRef, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import Paper from '@mui/material/Paper';
import Skeleton from '@mui/material/Skeleton';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import RefreshIcon from '@mui/icons-material/Refresh';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage, countFromResponse, displayValue, listFromResponse } from '../utils/apiData';

const encounterLabels = { annual_physical: '年度健檢', inpatient: '住院', outpatient: '門診', h2u_cvd_screening: 'H2U 心血管健檢' };
const encounterLabel = value => encounterLabels[value] || displayValue(value);

export default function HistoryRecords() {
  const { userInfo } = useAuth();
  const canWrite = hasAnyRole(userInfo, CLINICAL_WRITE_ROLES);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const errorNotice = useRef(null);
  useEffect(() => {
    if (!loading && error) errorNotice.current?.focus({ preventScroll: true });
  }, [loading, error]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(null);
  const [hasNext, setHasNext] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setRecords([]); setCount(null); setHasNext(false);
    (async () => {
      try {
        const response = await api.get(API_CONFIG.ENDPOINTS.HEALTH_SCREENINGS + '?page=' + page, { signal: controller.signal });
        const data = await parseApiResponse(response);
        if (controller.signal.aborted) return;
        if (!response.ok) throw new Error(apiErrorMessage(data, '無法讀取健檢紀錄，請稍後重試。'));
        setRecords(listFromResponse(data)); setCount(countFromResponse(data)); setHasNext(Boolean(data?.next));
      } catch (requestError) { if (!controller.signal.aborted) setError(requestError.message); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => controller.abort();
  }, [page, revision]);
  return <Box className="page-frame atlas-registry atlas-history">
    <Box className="page-heading"><Box><Typography variant="overline" color="primary">LONGITUDINAL RECORDS</Typography><Typography component="h1" variant="h4">健檢紀錄</Typography><Typography color="text.secondary" sx={{ mt: .75 }}>依日期查看每次健檢；病患風險分析整合目前有效的資料。</Typography></Box><Stack direction="row" spacing={1}><Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => setRevision(value => value + 1)} disabled={loading}>重新整理</Button>{canWrite && <Button component={RouterLink} to="/health-data-input" variant="contained">新增健檢</Button>}</Stack></Box>
    {error && <Alert ref={errorNotice} tabIndex={-1} severity="error" sx={{ mb: 2 }} action={<Button onClick={() => setRevision(value => value + 1)}>重試</Button>}>{error}</Alert>}
    <Typography role="status" variant="body2" color="text.secondary" sx={{ mb: 2 }}>{loading ? '正在讀取健檢紀錄…' : count === null ? '資料尚未載入' : '共 ' + count.toLocaleString() + ' 筆紀錄'}</Typography>
    <TableContainer component={Paper} className="data-table" role="region" aria-label="健檢紀錄表格捲動區" tabIndex={0}><Table role="table" size="small" aria-label="健檢紀錄清單" aria-busy={loading}><TableHead role="rowgroup"><TableRow role="row"><TableCell role="columnheader">健檢日期</TableCell><TableCell role="columnheader">病患</TableCell><TableCell role="columnheader">就診類型</TableCell><TableCell role="columnheader" align="right">病患分析</TableCell></TableRow></TableHead><TableBody role="rowgroup">
      {loading ? Array.from({length:5},(_,index)=><TableRow role="row" key={index}>{Array.from({length:4},(_,cell)=><TableCell key={cell}><Skeleton animation={false}/></TableCell>)}</TableRow>) : records.map(record => <TableRow role="row" key={record.id} className="history-record" hover><TableCell role="cell" className="registry-mrn history-date">{displayValue(record.screening_date)}</TableCell><TableCell role="cell" className="history-patient">{record.patient ? <Link component={RouterLink} to={'/patients/' + record.patient} className="registry-patient-link">{displayValue(record.patient_name)}</Link> : displayValue(record.patient_name)}</TableCell><TableCell role="cell" className="history-type">{encounterLabel(record.encounter_type)}</TableCell><TableCell role="cell" className="history-action" align="right">{record.patient ? <Button component={RouterLink} to={'/risk-analysis?patient_id=' + encodeURIComponent(record.patient)} size="small" aria-label={'開啟 ' + displayValue(record.patient_name) + ' 的病患風險分析'}>病患風險 ↗</Button> : '未提供病患識別'}</TableCell></TableRow>)}
      {!loading && !error && !records.length && <TableRow role="row"><TableCell colSpan={4}><div className="chart-empty"><Typography component="h2" variant="h6">{page > 1 ? '本頁沒有健檢紀錄' : '尚無健檢紀錄'}</Typography><Typography variant="body2" color="text.secondary">{page > 1 ? '可返回上一頁查看紀錄，或重新整理本頁。' : canWrite ? '新增一筆健檢，或透過資料匯入整理既有紀錄。' : '目前沒有可查看的授權紀錄。'}</Typography>{canWrite && page === 1 && <Button component={RouterLink} to="/bulk-import" sx={{ mt: 2 }}>前往資料匯入</Button>}</div></TableCell></TableRow>}
    </TableBody></Table></TableContainer>
    <div className="registry-pagination"><Typography variant="caption" color="text.secondary">{count === null ? '以授權範圍內的紀錄為準' : '第 ' + page + ' 頁 · 本頁 ' + records.length + ' 筆'}</Typography><Stack direction="row" spacing={1}><Button disabled={loading || page === 1} onClick={() => setPage(value => value - 1)}>上一頁</Button><Button disabled={loading || !hasNext} onClick={() => setPage(value => value + 1)}>下一頁</Button></Stack></div>
  </Box>;
}
