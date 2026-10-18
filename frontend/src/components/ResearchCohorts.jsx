import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
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
import BiotechIcon from '@mui/icons-material/Biotech';
import FilterAltIcon from '@mui/icons-material/FilterAlt';
import LockIcon from '@mui/icons-material/Lock';
import ManageSearchIcon from '@mui/icons-material/ManageSearch';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
import ShieldIcon from '@mui/icons-material/Shield';
import VerifiedIcon from '@mui/icons-material/Verified';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage } from '../utils/apiData';
import { ratioValue } from '../utils/numericDisplay';
import './ResearchCohorts.css';

const numericFilters = [
  { key: 'sbp', label: '收縮壓 SBP', unit: 'mmHg' },
  { key: 'dbp', label: '舒張壓 DBP', unit: 'mmHg' },
  { key: 'bmi', label: 'BMI', unit: 'kg/m2' },
  { key: 'fpg', label: '空腹血糖 FPG', unit: 'mg/dL' },
  { key: 'hba1c', label: 'HbA1c', unit: '%' },
  { key: 'ldl', label: 'LDL', unit: 'mg/dL' },
  { key: 'hdl', label: 'HDL', unit: 'mg/dL' },
  { key: 'tg', label: '三酸甘油脂 TG', unit: 'mg/dL' },
  { key: 'tc', label: '總膽固醇 TC', unit: 'mg/dL' },
  { key: 'waist', label: '腰圍', unit: 'cm' },
];

const booleanFilters = [
  { key: 'smoker', label: '吸菸' },
  { key: 'diabetes', label: '糖尿病' },
  { key: 'hypertension_treated', label: '高血壓治療' },
  { key: 'diabetes_treated', label: '糖尿病治療' },
  { key: 'chd_history', label: '冠心病病史' },
  { key: 'cvd_history', label: '心血管疾病病史' },
];

const defaultFilters = {
  sex: '',
  age_min: '',
  age_max: '',
  date_from: '',
  date_to: '',
  sbp_min: '',
  hba1c_min: '',
  ldl_min: '',
  smoker: '',
  diabetes: '',
  hypertension_treated: '',
};

const defaultSimilarProfile = {
  age: '',
  sex: '',
  sbp: '',
  dbp: '',
  bmi: '',
  hba1c: '',
  ldl: '',
  hdl: '',
  tg: '',
  fpg: '',
  sbp_delta: '',
  hba1c_delta: '',
  ldl_delta: '',
  smoker: '',
  diabetes: '',
  limit: '',
};

const readinessLabel = {
  research_ready: '可供研究',
  needs_review: '需要檢查',
  insufficient_data: '資料不足',
};

const displayNumber = (value, suffix = '') => {
  if (value === null || value === undefined || value === '') return '未釋出';
  if (typeof value === 'number') return Number.isFinite(value) ? `${Number.isInteger(value) ? value : value.toFixed(2)}${suffix}` : '未釋出';
  if (typeof value === 'string' && value.trim()) return `${value.trim()}${suffix}`;
  return '未釋出';
};

const statRows = (summary) => {
  const features = summary?.features || {};
  return numericFilters
    .map((item) => {
      const stats = features[item.key];
      if (!stats) return null;
      return {
        key: item.key,
        label: item.label || stats.label,
        unit: stats.unit || item.unit,
        count: stats.count,
        mean: stats.mean,
        min: stats.min,
        max: stats.max,
      };
    })
    .filter(Boolean);
};

const trendLabel = (key, fallback) => {
  const feature = numericFilters.find(item => item.key === key.replace(/^delta_|_delta$/g, ''));
  return feature ? feature.label + '變化' : fallback || key;
};

const trendRows = (summary) => Object.entries(summary?.trends || {}).map(([key, stats]) => ({
  key,
  label: trendLabel(key, stats.label),
  unit: stats.unit || '',
  count: stats.count,
  mean: stats.mean,
  min: stats.min,
  max: stats.max,
}));

function BooleanFilter({ item, value, onChange }) {
  const labelId = useId();
  return (
    <FormControl fullWidth size="small">
      <InputLabel id={labelId}>{item.label}</InputLabel>
      <Select labelId={labelId} label={item.label} value={value || ''} onChange={(event) => onChange(item.key, event.target.value)}>
        <MenuItem value="">不限制</MenuItem>
        <MenuItem value="true">是</MenuItem>
        <MenuItem value="false">否</MenuItem>
      </Select>
    </FormControl>
  );
}

function StatsTable({ rows }) {
  if (!rows.length) {
    return <Typography role="status" variant="body2" color="text.secondary">本次查詢沒有彙總指標。</Typography>;
  }

  return (
    <TableContainer component={Paper} className="cohort-table" role="region" aria-label="族群指標摘要捲動區" tabIndex={0}>
      <Table stickyHeader size="small" aria-label="族群指標摘要">
        <TableHead>
          <TableRow>
            <TableCell>指標</TableCell>
            <TableCell align="right">樣本數</TableCell>
            <TableCell align="right">平均</TableCell>
            <TableCell align="right">最小值</TableCell>
            <TableCell align="right">最大值</TableCell>
            <TableCell>單位</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.key}>
              <TableCell>{row.label}</TableCell>
              <TableCell align="right">{displayNumber(row.count)}</TableCell>
              <TableCell align="right">{displayNumber(row.mean)}</TableCell>
              <TableCell align="right">{displayNumber(row.min)}</TableCell>
              <TableCell align="right">{displayNumber(row.max)}</TableCell>
              <TableCell>{row.unit}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function ResearchCohorts() {
  const [filters, setFilters] = useState(defaultFilters);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [result, setResult] = useState(null);
  const cohortResultHeading = useRef(null);
  const similarResultHeading = useRef(null);
  const [similarProfile, setSimilarProfile] = useState(defaultSimilarProfile);
  const [similarResult, setSimilarResult] = useState(null);
  const [quality, setQuality] = useState(null);
  const [loading, setLoading] = useState(false);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [queryError, setQueryError] = useState('');
  const [similarError, setSimilarError] = useState('');
  const queryRequest = useRef(null);
  const similarRequest = useRef(null);
  const queryPlaceholder = loading ? '查詢中…' : queryError ? '查詢未完成' : '未執行';
  const similarPlaceholder = similarLoading ? '比對中…' : similarError ? '比對未完成' : '未執行';
  useEffect(() => () => { queryRequest.current?.abort(); similarRequest.current?.abort(); }, []);

  useEffect(() => {
    if (result && cohortResultHeading.current) {
      cohortResultHeading.current.focus({ preventScroll: true });
      cohortResultHeading.current.scrollIntoView?.({ block: 'start', behavior: 'instant' });
    }
  }, [result]);
  useEffect(() => {
    if (similarResult && similarResultHeading.current) {
      similarResultHeading.current.focus({ preventScroll: true });
      similarResultHeading.current.scrollIntoView?.({ block: 'start', behavior: 'instant' });
    }
  }, [similarResult]);

  const rows = useMemo(() => statRows(result?.summary), [result]);
  const similarRows = useMemo(() => statRows(similarResult?.summary), [similarResult]);
  const similarTrendRows = useMemo(() => trendRows(similarResult?.summary), [similarResult]);
  const sexCounts = result?.summary?.demographics?.sex || {};
  const ageStats = result?.summary?.demographics?.age;
  const similarAgeStats = similarResult?.summary?.demographics?.age;
  const averageSimilarity = ratioValue(similarResult?.average_similarity);
  const flagSummary = result?.summary?.flags || {};
  const coreCoverage = useMemo(() => {
    const coverage = quality?.feature_coverage || {};
    return ['sbp', 'hba1c', 'ldl', 'fpg', 'bmi']
      .map((key) => ({ key, ...coverage[key] }))
      .filter((item) => item.coverage !== undefined);
  }, [quality]);

  useEffect(() => {
    let mounted = true;
    const loadQuality = async () => {
      setQualityLoading(true);
      try {
        const response = await api.get(API_CONFIG.ENDPOINTS.DATA_QUALITY_SUMMARY);
        const data = await parseApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(data, '資料品質摘要讀取失敗'));
        if (mounted) setQuality(data);
      } catch (error) {
        if (mounted) setMessage({ type: 'error', text: error.message });
      } finally {
        if (mounted) setQualityLoading(false);
      }
    };
    loadQuality();
    return () => {
      mounted = false;
    };
  }, []);

  const updateFilter = (key, value) => {
    queryRequest.current?.abort(); setLoading(false); setResult(null); setQueryError('');
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const updateSimilarProfile = (key, value) => {
    similarRequest.current?.abort(); setSimilarLoading(false); setSimilarResult(null); setSimilarError('');
    setSimilarProfile((current) => ({ ...current, [key]: value }));
  };

  const paramsFrom = (values) => {
    const params = new URLSearchParams();
    Object.entries(values).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) params.set(key, value);
    });
    return params;
  };

  const runQuery = async () => {
    queryRequest.current?.abort();
    setResult(null); setQueryError('');
    const invalidRange = ['age', ...numericFilters.map(item => item.key)].find(key => filters[key + '_min'] !== undefined && filters[key + '_min'] !== '' && filters[key + '_max'] !== undefined && filters[key + '_max'] !== '' && Number(filters[key + '_min']) > Number(filters[key + '_max']));
    if (invalidRange || (filters.date_from && filters.date_to && filters.date_from > filters.date_to)) { setQueryError('請確認範圍：下限或起始日期不得超過上限或結束日期。'); return; }
    const controller = new AbortController(); queryRequest.current = controller;
    setLoading(true);
    try {
      const params = paramsFrom(filters);
      const suffix = params.toString() ? `?${params.toString()}` : '';
      const response = await api.get(`${API_CONFIG.ENDPOINTS.COHORT_SUMMARY}${suffix}`, { signal: controller.signal });
      const data = await parseApiResponse(response);
      if (controller.signal.aborted) return;
      if (!response.ok) throw new Error(apiErrorMessage(data, '族群查詢失敗'));
      setResult(data);
    } catch (error) {
      if (!controller.signal.aborted) setQueryError(error.message);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  const runSimilarQuery = async () => {
    similarRequest.current?.abort(); setSimilarResult(null); setSimilarError('');
    const controller = new AbortController(); similarRequest.current = controller;
    setSimilarLoading(true);
    try {
      const params = paramsFrom(similarProfile);
      const suffix = params.toString() ? `?${params.toString()}` : '';
      const response = await api.get(`${API_CONFIG.ENDPOINTS.PATIENTS_LIKE_THIS}${suffix}`, { signal: controller.signal });
      const data = await parseApiResponse(response);
      if (controller.signal.aborted) return;
      if (!response.ok) throw new Error(apiErrorMessage(data, '相似族群查詢失敗'));
      setSimilarResult(data);
    } catch (error) {
      if (!controller.signal.aborted) setSimilarError(error.message);
    } finally {
      if (!controller.signal.aborted) setSimilarLoading(false);
    }
  };

  return (
    <Box className="page-frame research-cohorts">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">研究</Typography>
          <Typography component="h1" variant="h4">研究族群工作台</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            定義研究族群，比對相近條件，檢視群體摘要與資料品質。
          </Typography>
        </Box>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Chip icon={<ShieldIcon />} label="群體摘要" color="success" variant="outlined" />
          <Chip icon={<LockIcon />} label="小樣本遮蔽" color="primary" variant="outlined" />
        </Stack>
      </Box>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Box className="cohort-layout">
        <Paper className="work-panel cohort-filter-panel">
          <Box className="panel-heading">
            <Typography component="h2" variant="h6">族群條件</Typography>
            <FilterAltIcon color="primary" />
          </Box>

          {queryError && <Alert severity="error" sx={{ mt: 2 }}>{queryError}</Alert>}
          <Box className="cohort-filter-grid">
            <FormControl fullWidth size="small" className="cohort-filter-wide">
              <InputLabel id="cohort-sex-label">性別</InputLabel>
              <Select labelId="cohort-sex-label" label="性別" value={filters.sex} onChange={(event) => updateFilter('sex', event.target.value)}>
                <MenuItem value="">不限制</MenuItem>
                <MenuItem value="F">女性</MenuItem>
                <MenuItem value="M">男性</MenuItem>
              </Select>
            </FormControl>
            <TextField size="small" label="年齡下限" InputLabelProps={{ shrink: true }} type="number" value={filters.age_min} onChange={(event) => updateFilter('age_min', event.target.value)} />
            <TextField size="small" label="年齡上限" InputLabelProps={{ shrink: true }} type="number" value={filters.age_max} onChange={(event) => updateFilter('age_max', event.target.value)} />
            <TextField size="small" label="日期起" type="date" value={filters.date_from} onChange={(event) => updateFilter('date_from', event.target.value)} InputLabelProps={{ shrink: true }} />
            <TextField size="small" label="日期迄" type="date" value={filters.date_to} onChange={(event) => updateFilter('date_to', event.target.value)} InputLabelProps={{ shrink: true }} />
            <TextField size="small" label="SBP 下限" InputLabelProps={{ shrink: true }} type="number" value={filters.sbp_min} onChange={(event) => updateFilter('sbp_min', event.target.value)} inputProps={{ 'aria-describedby': 'cohort-unit-sbp-min' }} InputProps={{ endAdornment: <InputAdornment position="end"><span id="cohort-unit-sbp-min">mmHg</span></InputAdornment> }} />
            <TextField size="small" label="HbA1c 下限" InputLabelProps={{ shrink: true }} type="number" value={filters.hba1c_min} onChange={(event) => updateFilter('hba1c_min', event.target.value)} inputProps={{ 'aria-describedby': 'cohort-unit-hba1c-min' }} InputProps={{ endAdornment: <InputAdornment position="end"><span id="cohort-unit-hba1c-min">%</span></InputAdornment> }} />
            <TextField size="small" label="LDL 下限" InputLabelProps={{ shrink: true }} type="number" value={filters.ldl_min} onChange={(event) => updateFilter('ldl_min', event.target.value)} inputProps={{ 'aria-describedby': 'cohort-unit-ldl-min' }} InputProps={{ endAdornment: <InputAdornment position="end"><span id="cohort-unit-ldl-min">mg/dL</span></InputAdornment> }} />
            {booleanFilters.slice(0, 3).map((item) => (
              <BooleanFilter key={item.key} item={item} value={filters[item.key]} onChange={updateFilter} />
            ))}
          </Box>

            <Button sx={{ mt: 2 }} variant="outlined" aria-expanded={advancedOpen} aria-controls="cohort-advanced" onClick={() => setAdvancedOpen((open) => !open)}>
              {advancedOpen ? '收合條件' : '更多條件'}
            </Button>

          {advancedOpen && (
            <Box className="cohort-filter-grid advanced-filters" id="cohort-advanced">
              {numericFilters.filter((item) => !['sbp', 'hba1c', 'ldl'].includes(item.key)).map((item) => (
                <React.Fragment key={item.key}>
                  <TextField size="small" label={`${item.label} 下限`} InputLabelProps={{ shrink: true }} type="number" value={filters[`${item.key}_min`] || ''} onChange={(event) => updateFilter(`${item.key}_min`, event.target.value)} inputProps={{ 'aria-describedby': 'cohort-unit-' + item.key + '-min' }} InputProps={{ endAdornment: <InputAdornment position="end"><span id={'cohort-unit-' + item.key + '-min'}>{item.unit}</span></InputAdornment> }} />
                  <TextField size="small" label={`${item.label} 上限`} InputLabelProps={{ shrink: true }} type="number" value={filters[`${item.key}_max`] || ''} onChange={(event) => updateFilter(`${item.key}_max`, event.target.value)} inputProps={{ 'aria-describedby': 'cohort-unit-' + item.key + '-max' }} InputProps={{ endAdornment: <InputAdornment position="end"><span id={'cohort-unit-' + item.key + '-max'}>{item.unit}</span></InputAdornment> }} />
                </React.Fragment>
              ))}
              {booleanFilters.slice(3).map((item) => (
                <BooleanFilter key={item.key} item={item} value={filters[item.key]} onChange={updateFilter} />
              ))}
            </Box>
          )}

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25} sx={{ mt: 2 }}>
            <Button variant="contained" startIcon={<QueryStatsIcon />} onClick={runQuery} disabled={loading}>
              {loading ? '查詢中' : '查詢族群'}
            </Button>

            <Button variant="text" onClick={() => { queryRequest.current?.abort(); setLoading(false); setFilters(defaultFilters); setResult(null); setQueryError(''); }}>清除</Button>
          </Stack>
        </Paper>

        <Paper className="work-panel patients-like-panel">
          <Box className="panel-heading">
            <Typography component="h2" variant="h6">相似族群條件</Typography>
            <ManageSearchIcon color="primary" />
          </Box>
          {similarError && <Alert severity="error" sx={{ mt: 2 }}>{similarError}</Alert>}
          <Box className="similar-profile-grid">
            <TextField size="small" label="年齡" InputLabelProps={{ shrink: true }} type="number" value={similarProfile.age} onChange={(event) => updateSimilarProfile('age', event.target.value)} />
            <FormControl fullWidth size="small">
              <InputLabel id="similar-sex-label">性別</InputLabel>
              <Select labelId="similar-sex-label" label="性別" value={similarProfile.sex} onChange={(event) => updateSimilarProfile('sex', event.target.value)}>
                <MenuItem value="">不限制</MenuItem>
                <MenuItem value="F">女性</MenuItem>
                <MenuItem value="M">男性</MenuItem>
              </Select>
            </FormControl>
            {['sbp', 'dbp', 'hba1c', 'ldl', 'bmi', 'sbp_delta', 'hba1c_delta', 'ldl_delta', 'limit'].map((key) => {
              const unit = key === 'limit' ? '筆' : numericFilters.find(item => item.key === key.replace(/_delta$/, ''))?.unit;
              return <TextField key={key} size="small" label={({sbp:"收縮壓 SBP",dbp:"舒張壓 DBP",hba1c:"HbA1c",ldl:"LDL",bmi:"BMI",sbp_delta:"SBP 差值",hba1c_delta:"HbA1c 差值",ldl_delta:"LDL 差值",limit:"結果筆數"})[key]} inputProps={{step:key === "limit" ? 1 : "any", 'aria-describedby': unit ? 'similar-unit-' + key : undefined}} InputProps={unit ? { endAdornment: <InputAdornment position="end"><span id={'similar-unit-' + key}>{unit}</span></InputAdornment> } : undefined} InputLabelProps={{ shrink: true }} type="number" value={similarProfile[key]} onChange={(event) => updateSimilarProfile(key, event.target.value)} />;
            })}
            <BooleanFilter item={{ key: 'smoker', label: '吸菸' }} value={similarProfile.smoker} onChange={updateSimilarProfile} />
            <BooleanFilter item={{ key: 'diabetes', label: '糖尿病' }} value={similarProfile.diabetes} onChange={updateSimilarProfile} />
          </Box>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25} sx={{ mt: 2 }}>
            <Button variant="contained" startIcon={<ManageSearchIcon />} onClick={runSimilarQuery} disabled={similarLoading}>
              {similarLoading ? '比對中' : '查詢相似族群'}
            </Button>
            <Button variant="text" onClick={() => { similarRequest.current?.abort(); setSimilarLoading(false); setSimilarProfile(defaultSimilarProfile); setSimilarResult(null); setSimilarError(''); }}>清除</Button>
          </Stack>
        </Paper>

        <Box className="cohort-results">
          <Paper className="work-panel quality-panel">
            <Box className="panel-heading">
              <Stack direction="row" spacing={1} alignItems="center">
                <VerifiedIcon color="success" />
                <Typography component="h2" variant="h6">資料品質</Typography>
              </Stack>
              <Chip size="small" label={qualityLoading ? '讀取中' : readinessLabel[quality?.readiness?.label] || quality?.readiness?.label || '未載入'} color={quality?.readiness?.label === 'research_ready' ? 'success' : 'warning'} variant="outlined" />
            </Box>
            <Box className="quality-grid">
              <Box className="quality-stat"><Typography variant="caption" color="text.secondary">病患</Typography><Typography component="p" variant="h6">{displayNumber(quality?.record_counts?.patients)}</Typography></Box>
              <Box className="quality-stat"><Typography variant="caption" color="text.secondary">健檢</Typography><Typography component="p" variant="h6">{displayNumber(quality?.record_counts?.screenings)}</Typography></Box>
              <Box className="quality-stat"><Typography variant="caption" color="text.secondary">日期範圍</Typography><Typography variant="body2" fontWeight={900}>{quality?.date_range?.first ? `${quality.date_range.first} 至 ${quality.date_range.last}` : '未載入'}</Typography></Box>
              <Box className="quality-stat"><Typography variant="caption" color="text.secondary">重複就診紀錄</Typography><Typography component="p" variant="h6">{displayNumber(quality?.duplicates?.duplicate_encounter_identifiers)}</Typography></Box>
            </Box>
            {coreCoverage.length > 0 && (
              <Box className="coverage-strip">
                {coreCoverage.map((item) => {
                  const coverage = ratioValue(item.coverage);
                  const known = coverage !== null;
                  const percentage = known ? Math.round(coverage * 100) : null;
                  return <Box className="coverage-item" key={item.key}>
                    <Typography variant="caption" color="text.secondary">{item.key.toUpperCase()}</Typography>
                    {known ? <Box className="coverage-track" role="meter" aria-label={item.key.toUpperCase() + ' 資料覆蓋率'} aria-valuemin={0} aria-valuemax={100} aria-valuenow={coverage * 100} aria-valuetext={percentage + '%'}><Box className="coverage-fill" style={{ width: coverage * 100 + '%' }} /></Box> : <Box aria-hidden="true" />}
                    <Typography variant="caption" fontWeight={900}>{known ? percentage + '%' : '未提供'}</Typography>
                  </Box>;
                })}
              </Box>
            )}
          </Paper>

          {result && <Typography ref={cohortResultHeading} tabIndex={-1} component="h2" variant="h6" sx={{ scrollMarginTop: 88 }}>族群查詢結果</Typography>}
          <Box className="cohort-metric-strip">
            <Paper className="cohort-metric">
              <BiotechIcon color="primary" />
              <Box><Typography variant="caption" color="text.secondary">資料集</Typography><Typography component="p" variant="h6">{result ? result.dataset || '未提供' : queryPlaceholder}</Typography></Box>
            </Paper>
            <Paper className="cohort-metric cohort-count">
              <QueryStatsIcon color="success" />
              <Box><Typography variant="caption" color="text.secondary">族群人數</Typography><Typography component="p" variant="h5">{result ? displayNumber(result.cohort_count) : queryPlaceholder}</Typography></Box>
            </Paper>
            <Paper className="cohort-metric">
              <LockIcon color={result?.privacy?.suppressed ? 'warning' : 'primary'} />
              <Box><Typography variant="caption" color="text.secondary">隱私狀態</Typography><Typography component="p" variant="h6">{result ? (result.privacy?.suppressed === true ? '已遮蔽' : result.privacy?.suppressed === false ? '未遮蔽' : '未提供') : queryPlaceholder}</Typography></Box>
            </Paper>
          </Box>

          {result && (
            <>
              {result.privacy?.suppressed && <Alert severity="warning" sx={{ mb: 2 }}>此 cohort 人數低於釋出門檻，結果已遮蔽。</Alert>}
              <Paper className="work-panel cohort-summary-panel">
                <Box className="panel-heading"><Typography component="h2" variant="h6">族群概況</Typography><Chip size="small" label="群體摘要" variant="outlined" /></Box>
                <Box className="cohort-demographics">
                  <Box className="demographic-stat"><Typography variant="caption" color="text.secondary">平均年齡</Typography><Typography component="p" variant="h5">{displayNumber(ageStats?.mean)}</Typography></Box>
                  <Box className="demographic-stat"><Typography variant="caption" color="text.secondary">年齡範圍</Typography><Typography component="p" variant="h6">{ageStats ? `${displayNumber(ageStats.min)} - ${displayNumber(ageStats.max)}` : '未釋出'}</Typography></Box>
                  <Box className="demographic-stat"><Typography variant="caption" color="text.secondary">女性</Typography><Typography component="p" variant="h6">{displayNumber(sexCounts.F)}</Typography></Box>
                  <Box className="demographic-stat"><Typography variant="caption" color="text.secondary">男性</Typography><Typography component="p" variant="h6">{displayNumber(sexCounts.M)}</Typography></Box>
                </Box>
              </Paper>
              <StatsTable rows={rows} />
              <Paper className="work-panel cohort-summary-panel">
                <Box className="panel-heading"><Typography component="h2" variant="h6">病史與生活習慣</Typography><Chip size="small" label="群體統計" variant="outlined" /></Box>
                <Box className="flag-grid">
                  {booleanFilters.map((item) => {
                    const counts = flagSummary[item.key] || {};
                    return (
                      <Box className="flag-tile" key={item.key}>
                        <Typography variant="body2" fontWeight={900}>{item.label}</Typography>
                        <Typography variant="caption" color="text.secondary">是 {displayNumber(counts.true)} / 否 {displayNumber(counts.false)}</Typography>
                      </Box>
                    );
                  })}
                </Box>
              </Paper>
            </>
          )}

          <Paper className="work-panel similar-results-panel">
            <Box className="panel-heading">
              <Stack direction="row" spacing={1} alignItems="center"><ManageSearchIcon color="primary" /><Typography ref={similarResultHeading} tabIndex={-1} component="h2" variant="h6" sx={{ scrollMarginTop: 88 }}>相似族群</Typography></Stack>
              {similarResult?.matching_model?.version && <Chip size="small" label={similarResult.matching_model.version} variant="outlined" />}
            </Box>
            <Box className="similar-metric-grid">
              <Box className="similar-stat"><Typography variant="caption" color="text.secondary">符合人數</Typography><Typography component="p" variant="h5">{similarResult ? displayNumber(similarResult.matched_count) : similarPlaceholder}</Typography></Box>
              <Box className="similar-stat"><Typography variant="caption" color="text.secondary">平均相似度</Typography><Typography component="p" variant="h5">{similarResult ? (averageSimilarity === null ? '未釋出' : `${Math.round(averageSimilarity * 100)}%`) : similarPlaceholder}</Typography></Box>
              <Box className="similar-stat"><Typography variant="caption" color="text.secondary">平均年齡</Typography><Typography component="p" variant="h5">{similarResult ? displayNumber(similarAgeStats?.mean) : similarPlaceholder}</Typography></Box>
              <Box className="similar-stat"><Typography variant="caption" color="text.secondary">隱私</Typography><Typography component="p" variant="h6">{similarResult ? (similarResult.privacy?.suppressed === true ? '已遮蔽' : similarResult.privacy?.suppressed === false ? '未遮蔽' : '未提供') : similarPlaceholder}</Typography></Box>
            </Box>
            {similarResult?.privacy?.suppressed && <Alert severity="warning" sx={{ mt: 2 }}>相似族群 人數低於釋出門檻，結果已遮蔽。</Alert>}
            {similarResult && (
              <>
                <Box className="similar-feature-list">
                  {similarRows.length > 0 ? similarRows.slice(0, 6).map((row) => (
                    <Box className="similar-feature" key={row.key}>
                      <Typography variant="body2" fontWeight={900}>{row.label}</Typography>
                      <Typography variant="caption" color="text.secondary">平均 {displayNumber(row.mean)} {row.unit || ''}</Typography>
                    </Box>
                  )) : <Alert severity="info">本次查詢沒有相似族群 指標。</Alert>}
                </Box>
                {similarTrendRows.length > 0 && (
                  <Box className="similar-trend-list">
                    {similarTrendRows.slice(0, 6).map((row) => (
                      <Box className="similar-feature similar-trend" key={row.key}>
                        <Typography variant="body2" fontWeight={900}>{row.label}</Typography>
                        <Typography variant="caption" color="text.secondary">平均變化 {displayNumber(row.mean)} {row.unit || ''}</Typography>
                      </Box>
                    ))}
                  </Box>
                )}
              </>
            )}
          </Paper>
        </Box>
      </Box>
    </Box>
  );
}

export default ResearchCohorts;
