import React, { useEffect, useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import RefreshIcon from '@mui/icons-material/Refresh';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage, listFromResponse } from '../utils/apiData';

const fieldLabels = {
  age: '年齡',
  sex: '性別',
  gender: '性別',
  fasting_glucose: 'FPG',
  bmi: 'BMI',
  body_height: '身高',
  body_weight: '體重',
  hdl_cholesterol: 'HDL',
  total_cholesterol: 'TC',
  triglycerides: 'TG',
  systolic_bp: 'SBP',
  diastolic_bp: 'DBP',
  resting_heart_rate: '靜息心率',
  heart_rate: '心率',
  family_history_diabetes: '糖尿病家族史',
  anti_hypertensive_drugs: '降血壓藥物',
  using_lipid_lowering_drugs: '降血脂藥物',
  waist_circumference: '腰圍',
  hip_circumference: '臀圍',
  waist_hip_ratio: '腰臀比',
  has_diabetes: '糖尿病',
  prediabetes: 'Prediabetes',
  has_hypertension: '高血壓',
  vegetables_daily: '每日蔬菜',
  is_smoker: '吸菸',
  physical_activity_active: '規律活動',
  ast_got: 'AST',
  alt_gpt: 'ALT',
  ast_uln: 'AST ULN',
  platelet_count: 'Platelet count',
  albumin: 'Albumin',
  ggt: 'GGT',
  insulin: 'Insulin',
  alcohol_drinks_per_week: '每週酒精量',
  apoe_e4: 'APOE e4',
};

const levelLabels = {
  missing: '資料不足',
  low: '低',
  moderate_low: '中低',
  moderate: '中',
  moderate_high: '中高',
  high: '高',
};

const levelStyles = {
  missing: { color: '#64748b', background: '#f8fafc', border: '#cbd5e1', strip: '#94a3b8' },
  low: { color: '#047857', background: '#f0fdf4', border: '#bbf7d0', strip: '#22c55e' },
  moderate_low: { color: '#0f766e', background: '#ecfeff', border: '#a5f3fc', strip: '#15d1c3' },
  moderate: { color: '#a16207', background: '#fffbeb', border: '#fde68a', strip: '#f59e0b' },
  moderate_high: { color: '#c2410c', background: '#fff7ed', border: '#fed7aa', strip: '#f97316' },
  high: { color: '#b91c1c', background: '#fef2f2', border: '#fecaca', strip: '#ef4444' },
};

const valueOrEmpty = (value) => {
  if (value === true) return '是';
  if (value === false) return '否';
  if (value === null || value === undefined || value === '') return '無資料';
  return String(value);
};

const normalizeRiskResults = (riskData) => {
  if (!Array.isArray(riskData?.disease_risk_results)) return [];
  return riskData.disease_risk_results.map((result) => {
    const missing = result.missing_data_labels?.length
      ? result.missing_data_labels
      : (result.missing_data || []).map((field) => fieldLabels[field] || field);
    const level = missing.length ? 'missing' : (result.risk_level || 'missing');
    return {
      id: result.id || `${result.algorithm || 'algorithm'}-${result.outcome || 'outcome'}`,
      title: result.display_name || result.algorithm_name || result.algorithm || '風險模型',
      item: result.outcome_label || result.outcome || '風險結果',
      value: missing.length ? '資料不足' : valueOrEmpty(result.risk_percentage),
      level,
      levelLabel: levelLabels[level] || valueOrEmpty(result.risk_level),
      missing,
      recommendation: result.recommendation_text || '',
      review: Boolean(result.requires_doctor_review),
    };
  });
};

function RiskAnalysis() {
  const [patients, setPatients] = useState([]);
  const [screenings, setScreenings] = useState([]);
  const [patientId, setPatientId] = useState('');
  const [screeningId, setScreeningId] = useState('');
  const [riskData, setRiskData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const response = await api.get(API_CONFIG.ENDPOINTS.PATIENTS);
        const data = await parseApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(data, '病患清單讀取失敗'));
        setPatients(listFromResponse(data));
      } catch (error) {
        setMessage({ type: 'error', text: error.message });
      }
    };
    fetchPatients();
  }, []);

  useEffect(() => {
    const fetchScreenings = async () => {
      if (!patientId) {
        setScreenings([]);
        setScreeningId('');
        setRiskData(null);
        return;
      }

      try {
        const response = await api.get(`${API_CONFIG.ENDPOINTS.HEALTH_SCREENINGS}?patient_id=${patientId}`);
        const data = await parseApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(data, '健檢紀錄讀取失敗'));
        const list = listFromResponse(data);
        setScreenings(list);
        setScreeningId(list[0]?.id || '');
        setRiskData(null);
      } catch (error) {
        setMessage({ type: 'error', text: error.message });
      }
    };
    fetchScreenings();
  }, [patientId]);

  const selectedPatient = patients.find((patient) => String(patient.id) === String(patientId));
  const riskCards = useMemo(() => normalizeRiskResults(riskData), [riskData]);
  const sourceData = riskData?.data_summary?.data || {};
  const visibleSnapshot = Object.entries(sourceData).filter(([key]) => fieldLabels[key]);

  const calculateRisk = async () => {
    if (!screeningId) {
      setMessage({ type: 'error', text: '請先選擇健檢紀錄' });
      return;
    }

    setLoading(true);
    setMessage(null);
    setRiskData(null);

    try {
      const response = await api.post(`${API_CONFIG.ENDPOINTS.HEALTH_SCREENINGS}${screeningId}/calculate_comprehensive_risk/`, {});
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, '風險分析失敗'));
      setRiskData(data);
      setMessage({ type: 'success', text: '後端已完成風險分析' });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box className="page-frame">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">風險分析</Typography>
          <Typography variant="h4">臨床風險分析</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            選擇後端已有的病患與健檢紀錄，執行可追溯的風險模型。
          </Typography>
        </Box>
      </Box>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Paper className="work-panel">
        <Stack spacing={3}>
          <Box>
            <Typography variant="h6">選擇資料來源</Typography>
            <Typography variant="body2" color="text.secondary">風險結果只會在後端成功回傳後顯示。</Typography>
          </Box>

          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '2fr 2fr auto' }, alignItems: 'center' }}>
            <FormControl fullWidth>
              <InputLabel id="risk-patient-label">病患</InputLabel>
              <Select labelId="risk-patient-label" label="病患" value={patientId} onChange={(event) => setPatientId(event.target.value)}>
                {patients.map((patient) => (
                  <MenuItem key={patient.id} value={patient.id}>
                    {[patient.first_name, patient.last_name].filter(Boolean).join(' ') || patient.full_name || patient.id} ({patient.medical_record_number || patient.id})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth disabled={!screenings.length}>
              <InputLabel id="risk-screening-label">健檢紀錄</InputLabel>
              <Select labelId="risk-screening-label" label="健檢紀錄" value={screeningId} onChange={(event) => setScreeningId(event.target.value)}>
                {screenings.map((screening) => (
                  <MenuItem key={screening.id} value={screening.id}>
                    {screening.screening_date} - {screening.encounter_type || '未指定 encounter'}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button variant="contained" startIcon={loading ? <RefreshIcon /> : <AnalyticsIcon />} disabled={!screeningId || loading} onClick={calculateRisk} sx={{ minWidth: 150 }}>
              {loading ? '分析中' : '開始分析'}
            </Button>
          </Box>

          {selectedPatient && (
            <Alert severity="info" variant="outlined">
              {[selectedPatient.first_name, selectedPatient.last_name].filter(Boolean).join(' ') || selectedPatient.full_name}，MRN {selectedPatient.medical_record_number || '無資料'}，{selectedPatient.age ?? '無資料'} 歲
            </Alert>
          )}
        </Stack>
      </Paper>

      {riskData && (
        <Box sx={{ mt: 3 }}>
          <Stack spacing={3}>
            <Box>
              <Typography variant="h6">分析結果</Typography>
              <Typography variant="body2" color="text.secondary">
                以下內容由後端風險分析 API 回傳；缺值、遮蔽或不可計算狀態不以前端資料補齊。
              </Typography>
            </Box>

            {riskCards.length > 0 ? (
              <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))', xl: 'repeat(3, minmax(0, 1fr))' } }}>
                {riskCards.map((card) => {
                  const style = levelStyles[card.level] || levelStyles.missing;
                  return (
                    <Paper
                      key={card.id}
                      variant="outlined"
                      sx={{
                        position: 'relative',
                        overflow: 'hidden',
                        p: 2.25,
                        minHeight: 250,
                        borderColor: style.border,
                        background: style.background,
                      }}
                    >
                      <Box sx={{ position: 'absolute', left: 0, top: 0, right: 0, height: 5, background: style.strip }} />
                      <Stack spacing={1.5} sx={{ height: '100%' }}>
                        <Stack direction="row" spacing={1} justifyContent="space-between" alignItems="flex-start">
                          <Box sx={{ minWidth: 0 }}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 850, color: '#102033' }}>
                              {card.title}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">{card.item}</Typography>
                          </Box>
                          <Chip size="small" label={card.levelLabel} sx={{ color: style.color, borderColor: style.border, backgroundColor: '#ffffff', fontWeight: 800 }} variant="outlined" />
                        </Stack>

                        <Box>
                          <Typography variant="h4" sx={{ fontWeight: 900, color: style.color, lineHeight: 1.1 }}>
                            {card.value}
                          </Typography>
                          {card.review && <Typography variant="caption" color="text.secondary">需要臨床人員覆核</Typography>}
                        </Box>

                        {card.missing.length > 0 && (
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 800, mb: 1, color: '#334155' }}>缺少資料</Typography>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                              {card.missing.map((item) => (
                                <Chip key={item} size="small" label={item} sx={{ backgroundColor: '#ffffff', border: '1px solid #dbe5ef' }} />
                              ))}
                            </Box>
                          </Box>
                        )}

                        {card.recommendation && (
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 'auto' }}>
                            {card.recommendation}
                          </Typography>
                        )}
                      </Stack>
                    </Paper>
                  );
                })}
              </Box>
            ) : (
              <Alert severity="warning">後端未回傳可顯示的風險結果。</Alert>
            )}

            {visibleSnapshot.length > 0 && (
              <>
                <Divider />
                <Box>
                  <Typography variant="h6">輸入資料摘要</Typography>
                  <Box className="surface-grid" sx={{ mt: 2 }}>
                    {visibleSnapshot.map(([key, value]) => (
                      <Paper key={key} variant="outlined" sx={{ p: 2 }}>
                        <Typography variant="caption" color="text.secondary">{fieldLabels[key]}</Typography>
                        <Typography variant="body1">{valueOrEmpty(value)}</Typography>
                      </Paper>
                    ))}
                  </Box>
                </Box>
              </>
            )}
          </Stack>
        </Box>
      )}
    </Box>
  );
}

export default RiskAnalysis;
