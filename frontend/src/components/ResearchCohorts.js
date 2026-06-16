import React, { useEffect, useMemo, useState } from 'react';
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
import './ResearchCohorts.css';

const numericFilters = [
  { key: 'sbp', label: 'SBP', unit: 'mmHg' },
  { key: 'dbp', label: 'DBP', unit: 'mmHg' },
  { key: 'bmi', label: 'BMI', unit: 'kg/m2' },
  { key: 'fpg', label: 'FPG', unit: 'mg/dL' },
  { key: 'hba1c', label: 'HbA1c', unit: '%' },
  { key: 'ldl', label: 'LDL', unit: 'mg/dL' },
  { key: 'hdl', label: 'HDL', unit: 'mg/dL' },
  { key: 'tg', label: 'TG', unit: 'mg/dL' },
  { key: 'tc', label: 'TC', unit: 'mg/dL' },
  { key: 'waist', label: '腰圍', unit: 'cm' },
];

const booleanFilters = [
  { key: 'smoker', label: '吸菸' },
  { key: 'diabetes', label: '糖尿病' },
  { key: 'hypertension_treated', label: '高血壓治療' },
  { key: 'diabetes_treated', label: '糖尿病治療' },
  { key: 'chd_history', label: 'CHD history' },
  { key: 'cvd_history', label: 'CVD history' },
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
  if (typeof value === 'number') return `${Number.isInteger(value) ? value : value.toFixed(2)}${suffix}`;
  return `${value}${suffix}`;
};

const statRows = (summary) => {
  const features = summary?.features || {};
  return numericFilters
    .map((item) => {
      const stats = features[item.key];
      if (!stats) return null;
      return {
        key: item.key,
        label: stats.label || item.label,
        unit: stats.unit || item.unit,
        count: stats.count,
        mean: stats.mean,
        min: stats.min,
        max: stats.max,
      };
    })
    .filter(Boolean);
};

const trendRows = (summary) => Object.entries(summary?.trends || {}).map(([key, stats]) => ({
  key,
  label: stats.label || key,
  unit: stats.unit || '',
  count: stats.count,
  mean: stats.mean,
  min: stats.min,
  max: stats.max,
}));

function BooleanFilter({ item, value, onChange }) {
  return (
    <FormControl fullWidth size="small">
      <InputLabel id={`${item.key}-label`}>{item.label}</InputLabel>
      <Select labelId={`${item.key}-label`} label={item.label} value={value || ''} onChange={(event) => onChange(item.key, event.target.value)}>
        <MenuItem value="">不限制</MenuItem>
        <MenuItem value="true">是</MenuItem>
        <MenuItem value="false">否</MenuItem>
      </Select>
    </FormControl>
  );
}

function StatsTable({ rows }) {
  if (!rows.length) {
    return <Alert severity="info">後端目前沒有回傳可顯示的 aggregate 指標。</Alert>;
  }

  return (
    <TableContainer component={Paper} className="cohort-table">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>指標</TableCell>
            <TableCell align="right">N</TableCell>
            <TableCell align="right">Mean</TableCell>
            <TableCell align="right">Min</TableCell>
            <TableCell align="right">Max</TableCell>
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
  const [similarProfile, setSimilarProfile] = useState(defaultSimilarProfile);
  const [similarResult, setSimilarResult] = useState(null);
  const [quality, setQuality] = useState(null);
  const [loading, setLoading] = useState(false);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const rows = useMemo(() => statRows(result?.summary), [result]);
  const similarRows = useMemo(() => statRows(similarResult?.summary), [similarResult]);
  const similarTrendRows = useMemo(() => trendRows(similarResult?.summary), [similarResult]);
  const sexCounts = result?.summary?.demographics?.sex || {};
  const ageStats = result?.summary?.demographics?.age;
  const similarAgeStats = similarResult?.summary?.demographics?.age;
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
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const updateSimilarProfile = (key, value) => {
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
    setLoading(true);
    setMessage(null);
    try {
      const params = paramsFrom(filters);
      const suffix = params.toString() ? `?${params.toString()}` : '';
      const response = await api.get(`${API_CONFIG.ENDPOINTS.COHORT_SUMMARY}${suffix}`);
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, 'Cohort 查詢失敗'));
      setResult(data);
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  };

  const runSimilarQuery = async () => {
    setSimilarLoading(true);
    setMessage(null);
    try {
      const params = paramsFrom(similarProfile);
      const suffix = params.toString() ? `?${params.toString()}` : '';
      const response = await api.get(`${API_CONFIG.ENDPOINTS.PATIENTS_LIKE_THIS}${suffix}`);
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, 'Patients-like-this 查詢失敗'));
      setSimilarResult(data);
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setSimilarLoading(false);
    }
  };

  return (
    <Box className="page-frame research-cohorts">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">研究</Typography>
          <Typography variant="h4">Cohort 工作台</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            以後端 H2U CVD 資料庫執行 aggregate cohort 查詢與相似病患分群。
          </Typography>
        </Box>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Chip icon={<ShieldIcon />} label="僅 aggregate" color="success" variant="outlined" />
          <Chip icon={<LockIcon />} label="小樣本遮蔽" color="primary" variant="outlined" />
        </Stack>
      </Box>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Box className="cohort-layout">
        <Paper className="work-panel cohort-filter-panel">
          <Box className="panel-heading">
            <Typography variant="h6">Cohort 條件</Typography>
            <FilterAltIcon color="primary" />
          </Box>

          <Box className="cohort-filter-grid">
            <FormControl fullWidth size="small">
              <InputLabel id="cohort-sex-label">性別</InputLabel>
              <Select labelId="cohort-sex-label" label="性別" value={filters.sex} onChange={(event) => updateFilter('sex', event.target.value)}>
                <MenuItem value="">不限制</MenuItem>
                <MenuItem value="F">女性</MenuItem>
                <MenuItem value="M">男性</MenuItem>
              </Select>
            </FormControl>
            <TextField size="small" label="年齡下限" type="number" value={filters.age_min} onChange={(event) => updateFilter('age_min', event.target.value)} />
            <TextField size="small" label="年齡上限" type="number" value={filters.age_max} onChange={(event) => updateFilter('age_max', event.target.value)} />
            <TextField size="small" label="日期起" type="date" value={filters.date_from} onChange={(event) => updateFilter('date_from', event.target.value)} InputLabelProps={{ shrink: true }} />
            <TextField size="small" label="日期迄" type="date" value={filters.date_to} onChange={(event) => updateFilter('date_to', event.target.value)} InputLabelProps={{ shrink: true }} />
            <TextField size="small" label="SBP 下限" type="number" value={filters.sbp_min} onChange={(event) => updateFilter('sbp_min', event.target.value)} InputProps={{ endAdornment: <InputAdornment position="end">mmHg</InputAdornment> }} />
            <TextField size="small" label="HbA1c 下限" type="number" value={filters.hba1c_min} onChange={(event) => updateFilter('hba1c_min', event.target.value)} InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }} />
            <TextField size="small" label="LDL 下限" type="number" value={filters.ldl_min} onChange={(event) => updateFilter('ldl_min', event.target.value)} InputProps={{ endAdornment: <InputAdornment position="end">mg/dL</InputAdornment> }} />
            {booleanFilters.slice(0, 3).map((item) => (
              <BooleanFilter key={item.key} item={item} value={filters[item.key]} onChange={updateFilter} />
            ))}
          </Box>

          {advancedOpen && (
            <Box className="cohort-filter-grid advanced-filters">
              {numericFilters.filter((item) => !['sbp', 'hba1c', 'ldl'].includes(item.key)).map((item) => (
                <React.Fragment key={item.key}>
                  <TextField size="small" label={`${item.label} 下限`} type="number" value={filters[`${item.key}_min`] || ''} onChange={(event) => updateFilter(`${item.key}_min`, event.target.value)} InputProps={{ endAdornment: <InputAdornment position="end">{item.unit}</InputAdornment> }} />
                  <TextField size="small" label={`${item.label} 上限`} type="number" value={filters[`${item.key}_max`] || ''} onChange={(event) => updateFilter(`${item.key}_max`, event.target.value)} InputProps={{ endAdornment: <InputAdornment position="end">{item.unit}</InputAdornment> }} />
                </React.Fragment>
              ))}
              {booleanFilters.slice(3).map((item) => (
                <BooleanFilter key={item.key} item={item} value={filters[item.key]} onChange={updateFilter} />
              ))}
            </Box>
          )}

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25} sx={{ mt: 2 }}>
            <Button variant="contained" startIcon={<QueryStatsIcon />} onClick={runQuery} disabled={loading}>
              {loading ? '查詢中' : '執行 cohort'}
            </Button>
            <Button variant="outlined" onClick={() => setAdvancedOpen((open) => !open)}>
              {advancedOpen ? '收合條件' : '更多條件'}
            </Button>
            <Button variant="text" onClick={() => { setFilters(defaultFilters); setResult(null); setMessage(null); }}>清除</Button>
          </Stack>
        </Paper>

        <Paper className="work-panel patients-like-panel">
          <Box className="panel-heading">
            <Typography variant="h6">Patients-like-this</Typography>
            <ManageSearchIcon color="primary" />
          </Box>
          <Box className="similar-profile-grid">
            <TextField size="small" label="年齡" type="number" value={similarProfile.age} onChange={(event) => updateSimilarProfile('age', event.target.value)} />
            <FormControl fullWidth size="small">
              <InputLabel id="similar-sex-label">性別</InputLabel>
              <Select labelId="similar-sex-label" label="性別" value={similarProfile.sex} onChange={(event) => updateSimilarProfile('sex', event.target.value)}>
                <MenuItem value="">不限制</MenuItem>
                <MenuItem value="F">女性</MenuItem>
                <MenuItem value="M">男性</MenuItem>
              </Select>
            </FormControl>
            {['sbp', 'dbp', 'hba1c', 'ldl', 'bmi', 'sbp_delta', 'hba1c_delta', 'ldl_delta', 'limit'].map((key) => (
              <TextField key={key} size="small" label={key.toUpperCase()} type="number" value={similarProfile[key]} onChange={(event) => updateSimilarProfile(key, event.target.value)} />
            ))}
            <BooleanFilter item={{ key: 'smoker', label: '吸菸' }} value={similarProfile.smoker} onChange={updateSimilarProfile} />
            <BooleanFilter item={{ key: 'diabetes', label: '糖尿病' }} value={similarProfile.diabetes} onChange={updateSimilarProfile} />
          </Box>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25} sx={{ mt: 2 }}>
            <Button variant="contained" startIcon={<ManageSearchIcon />} onClick={runSimilarQuery} disabled={similarLoading}>
              {similarLoading ? '比對中' : '尋找相似 cohort'}
            </Button>
            <Button variant="text" onClick={() => { setSimilarProfile(defaultSimilarProfile); setSimilarResult(null); setMessage(null); }}>清除</Button>
          </Stack>
        </Paper>

        <Box className="cohort-results">
          <Paper className="work-panel quality-panel">
            <Box className="panel-heading">
              <Stack direction="row" spacing={1} alignItems="center">
                <VerifiedIcon color="success" />
                <Typography variant="h6">資料品質</Typography>
              </Stack>
              <Chip size="small" label={qualityLoading ? '讀取中' : readinessLabel[quality?.readiness?.label] || quality?.readiness?.label || '未載入'} color={quality?.readiness?.label === 'research_ready' ? 'success' : 'warning'} variant="outlined" />
            </Box>
            <Box className="quality-grid">
              <Box className="quality-stat"><Typography variant="caption" color="text.secondary">病患</Typography><Typography variant="h6">{displayNumber(quality?.record_counts?.patients)}</Typography></Box>
              <Box className="quality-stat"><Typography variant="caption" color="text.secondary">健檢</Typography><Typography variant="h6">{displayNumber(quality?.record_counts?.screenings)}</Typography></Box>
              <Box className="quality-stat"><Typography variant="caption" color="text.secondary">日期範圍</Typography><Typography variant="body2" fontWeight={900}>{quality?.date_range?.first ? `${quality.date_range.first} 至 ${quality.date_range.last}` : '未載入'}</Typography></Box>
              <Box className="quality-stat"><Typography variant="caption" color="text.secondary">重複 encounter</Typography><Typography variant="h6">{displayNumber(quality?.duplicates?.duplicate_encounter_identifiers)}</Typography></Box>
            </Box>
            {coreCoverage.length > 0 && (
              <Box className="coverage-strip">
                {coreCoverage.map((item) => (
                  <Box className="coverage-item" key={item.key}>
                    <Typography variant="caption" color="text.secondary">{item.key.toUpperCase()}</Typography>
                    <Box className="coverage-track"><Box className="coverage-fill" style={{ width: `${Math.round((item.coverage || 0) * 100)}%` }} /></Box>
                    <Typography variant="caption" fontWeight={900}>{Math.round((item.coverage || 0) * 100)}%</Typography>
                  </Box>
                ))}
              </Box>
            )}
          </Paper>

          <Box className="cohort-metric-strip">
            <Paper className="cohort-metric">
              <BiotechIcon color="primary" />
              <Box><Typography variant="caption" color="text.secondary">Dataset</Typography><Typography variant="h6">{result?.dataset || '未執行'}</Typography></Box>
            </Paper>
            <Paper className="cohort-metric cohort-count">
              <QueryStatsIcon color="success" />
              <Box><Typography variant="caption" color="text.secondary">Cohort count</Typography><Typography variant="h5">{result ? displayNumber(result.cohort_count) : '未執行'}</Typography></Box>
            </Paper>
            <Paper className="cohort-metric">
              <LockIcon color={result?.privacy?.suppressed ? 'warning' : 'primary'} />
              <Box><Typography variant="caption" color="text.secondary">隱私狀態</Typography><Typography variant="h6">{result ? (result.privacy?.suppressed ? '已遮蔽' : '可釋出') : '未執行'}</Typography></Box>
            </Paper>
          </Box>

          {result && (
            <>
              {result.privacy?.suppressed && <Alert severity="warning" sx={{ mb: 2 }}>此 cohort 低於釋出門檻，後端已遮蔽結果。</Alert>}
              <Paper className="work-panel cohort-summary-panel">
                <Box className="panel-heading"><Typography variant="h6">Demographics</Typography><Chip size="small" label="無 row-level data" variant="outlined" /></Box>
                <Box className="cohort-demographics">
                  <Box className="demographic-stat"><Typography variant="caption" color="text.secondary">平均年齡</Typography><Typography variant="h5">{displayNumber(ageStats?.mean)}</Typography></Box>
                  <Box className="demographic-stat"><Typography variant="caption" color="text.secondary">年齡範圍</Typography><Typography variant="h6">{ageStats ? `${displayNumber(ageStats.min)} - ${displayNumber(ageStats.max)}` : '未釋出'}</Typography></Box>
                  <Box className="demographic-stat"><Typography variant="caption" color="text.secondary">女性</Typography><Typography variant="h6">{displayNumber(sexCounts.F)}</Typography></Box>
                  <Box className="demographic-stat"><Typography variant="caption" color="text.secondary">男性</Typography><Typography variant="h6">{displayNumber(sexCounts.M)}</Typography></Box>
                </Box>
              </Paper>
              <StatsTable rows={rows} />
              <Paper className="work-panel cohort-summary-panel">
                <Box className="panel-heading"><Typography variant="h6">Clinical flags</Typography><Chip size="small" label="Cell suppression active" variant="outlined" /></Box>
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
              <Stack direction="row" spacing={1} alignItems="center"><ManageSearchIcon color="primary" /><Typography variant="h6">相似 cohort</Typography></Stack>
              {similarResult?.matching_model?.version && <Chip size="small" label={similarResult.matching_model.version} variant="outlined" />}
            </Box>
            <Box className="similar-metric-grid">
              <Box className="similar-stat"><Typography variant="caption" color="text.secondary">Matched count</Typography><Typography variant="h5">{similarResult ? displayNumber(similarResult.matched_count) : '未執行'}</Typography></Box>
              <Box className="similar-stat"><Typography variant="caption" color="text.secondary">Average similarity</Typography><Typography variant="h5">{similarResult?.average_similarity ? `${Math.round(similarResult.average_similarity * 100)}%` : '未執行'}</Typography></Box>
              <Box className="similar-stat"><Typography variant="caption" color="text.secondary">平均年齡</Typography><Typography variant="h5">{similarResult ? displayNumber(similarAgeStats?.mean) : '未執行'}</Typography></Box>
              <Box className="similar-stat"><Typography variant="caption" color="text.secondary">隱私</Typography><Typography variant="h6">{similarResult ? (similarResult.privacy?.suppressed ? '已遮蔽' : '可釋出') : '未執行'}</Typography></Box>
            </Box>
            {similarResult?.privacy?.suppressed && <Alert severity="warning" sx={{ mt: 2 }}>相似 cohort 低於釋出門檻，後端已遮蔽結果。</Alert>}
            {similarResult && (
              <>
                <Box className="similar-feature-list">
                  {similarRows.length > 0 ? similarRows.slice(0, 6).map((row) => (
                    <Box className="similar-feature" key={row.key}>
                      <Typography variant="body2" fontWeight={900}>{row.label}</Typography>
                      <Typography variant="caption" color="text.secondary">Mean {displayNumber(row.mean)} {row.unit || ''}</Typography>
                    </Box>
                  )) : <Alert severity="info">後端未回傳相似 cohort 指標。</Alert>}
                </Box>
                {similarTrendRows.length > 0 && (
                  <Box className="similar-trend-list">
                    {similarTrendRows.slice(0, 6).map((row) => (
                      <Box className="similar-feature similar-trend" key={row.key}>
                        <Typography variant="body2" fontWeight={900}>{row.label}</Typography>
                        <Typography variant="caption" color="text.secondary">Mean delta {displayNumber(row.mean)} {row.unit || ''}</Typography>
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
