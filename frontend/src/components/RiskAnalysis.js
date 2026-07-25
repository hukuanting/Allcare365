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
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import DataObjectRoundedIcon from '@mui/icons-material/DataObjectRounded';
import PersonOutlineRoundedIcon from '@mui/icons-material/PersonOutlineRounded';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useSearchParams } from 'react-router-dom';
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
  creatinine: '血清肌酸酐',
  egfr: 'eGFR',
  cvd_history: '既往心血管疾病',
};

const levelLabels = {
  not_run: '尚未執行',
  review_required: '待臨床審核',
  missing: '資料不足',
  low: '低',
  moderate_low: '中低',
  moderate: '中',
  moderate_high: '中高',
  high: '高',
  not_applicable: '不適用',
};

const levelStyles = {
  not_run: { color: '#475569', background: '#f8fafc', border: '#d7e0e8', strip: '#94a3b8' },
  review_required: { color: '#8a5a13', background: '#fffaf0', border: '#ead9b7', strip: '#c38a2c' },
  missing: { color: '#64748b', background: '#f8fafc', border: '#cbd5e1', strip: '#94a3b8' },
  low: { color: '#047857', background: '#f0fdf4', border: '#bbf7d0', strip: '#22c55e' },
  moderate_low: { color: '#0f766e', background: '#ecfeff', border: '#a5f3fc', strip: '#15d1c3' },
  moderate: { color: '#a16207', background: '#fffbeb', border: '#fde68a', strip: '#f59e0b' },
  moderate_high: { color: '#c2410c', background: '#fff7ed', border: '#fed7aa', strip: '#f97316' },
  high: { color: '#b91c1c', background: '#fef2f2', border: '#fecaca', strip: '#ef4444' },
  not_applicable: { color: '#475569', background: '#f8fafc', border: '#cbd5e1', strip: '#64748b' },
};

export const RISK_SECTIONS = [
  {
    key: 'hepatic',
    code: 'HEP',
    title: '肝臟與肝纖維化',
    description: '脂肪肝、肝功能與纖維化相關評估',
    accent: '#8a6428',
    wash: '#fbf8f0',
    border: '#e8dcc2',
  },
  {
    key: 'renal',
    code: 'REN',
    title: '腎臟系統',
    description: '腎功能、慢性腎臟病與相關風險',
    accent: '#287269',
    wash: '#f2f8f6',
    border: '#cee3de',
  },
  {
    key: 'cardiovascular',
    code: 'CV',
    title: '心血管系統',
    description: '冠心病、心衰竭、高血壓與整體心血管風險',
    accent: '#9a493f',
    wash: '#fcf5f4',
    border: '#ead2cf',
  },
  {
    key: 'metabolic_endocrine',
    code: 'MET',
    title: '代謝與糖尿病',
    description: '糖尿病、胰島素阻抗、體位與代謝症候群',
    accent: '#356b88',
    wash: '#f2f7fa',
    border: '#cddfe9',
  },
  {
    key: 'neurocognitive',
    code: 'NEU',
    title: '神經與認知',
    description: '失智、認知功能與神經血管相關風險',
    accent: '#655778',
    wash: '#f7f5f9',
    border: '#ddd7e4',
  },
  {
    key: 'respiratory',
    code: 'PUL',
    title: '呼吸系統',
    description: '肺部、呼吸道與肺癌相關風險',
    accent: '#39727e',
    wash: '#f2f8f9',
    border: '#cde1e5',
  },
  {
    key: 'mental_health',
    code: 'PSY',
    title: '心理健康',
    description: '情緒、焦慮與心理症狀量表',
    accent: '#87576b',
    wash: '#faf5f7',
    border: '#e7d5dd',
  },
  {
    key: 'other',
    code: 'GEN',
    title: '其他臨床風險',
    description: '尚未歸入特定器官系統的評估',
    accent: '#5f6b7a',
    wash: '#f6f8fa',
    border: '#d9e0e7',
  },
];

const sectionKeys = new Set(RISK_SECTIONS.map((section) => section.key));

const sectionAliases = {
  hepatic: 'hepatic',
  hepatology: 'hepatic',
  liver: 'hepatic',
  fatty_liver: 'hepatic',
  liver_fibrosis: 'hepatic',
  renal: 'renal',
  nephrology: 'renal',
  kidney: 'renal',
  chronic_kidney_disease: 'renal',
  cardiovascular: 'cardiovascular',
  cardiovascular_diabetes: 'cardiovascular',
  cardiac: 'cardiovascular',
  cardiology: 'cardiovascular',
  hypertension: 'cardiovascular',
  metabolic_endocrine: 'metabolic_endocrine',
  metabolic: 'metabolic_endocrine',
  endocrine: 'metabolic_endocrine',
  diabetes: 'metabolic_endocrine',
  anthropometry: 'metabolic_endocrine',
  neurocognitive: 'neurocognitive',
  neurology: 'neurocognitive',
  dementia: 'neurocognitive',
  cognitive: 'neurocognitive',
  respiratory: 'respiratory',
  pulmonary: 'respiratory',
  lung: 'respiratory',
  lung_cancer: 'respiratory',
  mental_health: 'mental_health',
  mental: 'mental_health',
  psychiatry: 'mental_health',
  behavioral_health: 'mental_health',
  other: 'other',
  general: 'other',
};

const algorithmSectionMap = {
  bmi: 'metabolic_endocrine',
  tyg_index: 'metabolic_endocrine',
  homa_ir: 'metabolic_endocrine',
  quicki: 'metabolic_endocrine',
  framingham_diabetes: 'metabolic_endocrine',
  chinese_diabetes: 'metabolic_endocrine',
  metabolic_syndrome: 'metabolic_endocrine',
  ausdrisk_diabetes: 'metabolic_endocrine',
  cambridge_diabetes_risk: 'metabolic_endocrine',
  hepatic_steatosis_index: 'hepatic',
  nafld_liver_fat_score: 'hepatic',
  fatty_liver_index: 'hepatic',
  fib4: 'hepatic',
  apri: 'hepatic',
  rpr: 'hepatic',
  nafld_fibrosis_score: 'hepatic',
  incident_hepatic_steatosis_model_2: 'hepatic',
  nafld_fibrosis: 'hepatic',
  framingham_fatty_liver: 'hepatic',
  nafld_cv_risk_score: 'cardiovascular',
  framingham_cvd_10_lipids: 'cardiovascular',
  framingham_cvd_10_bmi: 'cardiovascular',
  framingham_hypertension: 'cardiovascular',
  nomas_global_vascular_risk: 'cardiovascular',
  christianson_t2dm_chd_score: 'cardiovascular',
  aha_prevent_cvd_10y: 'cardiovascular',
  aha_prevent_ascvd_10y: 'cardiovascular',
  aha_prevent_hf_10y: 'cardiovascular',
  dementia_risk_score_thin_60_79: 'neurocognitive',
  mayo_pulmonary_nodule: 'respiratory',
  gad7: 'mental_health',
};

const normalizeToken = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[\s./-]+/g, '_')
  .replace(/^_+|_+$/g, '');

const sectionFieldText = (value) => {
  if (Array.isArray(value)) return value.map(sectionFieldText).filter(Boolean).join(' ');
  if (value && typeof value === 'object') {
    return [value.code, value.display, value.text, value.value, value.coding]
      .map(sectionFieldText)
      .filter(Boolean)
      .join(' ');
  }
  return value === null || value === undefined ? '' : String(value);
};

const sectionFromText = (value) => {
  const token = normalizeToken(sectionFieldText(value));
  if (!token) return null;
  if (sectionAliases[token]) return sectionAliases[token];

  const keywordRules = [
    ['hepatic', /(hepatic|liver|nafld|steatosis|fibrosis|fib4|apri|肝)/],
    ['renal', /(renal|kidney|nephro|ckd|egfr|腎)/],
    ['neurocognitive', /(neuro|dement|cognit|caide|alzheimer|失智|認知|神經)/],
    ['respiratory', /(respirat|pulmonary|lung|copd|肺|呼吸)/],
    ['mental_health', /(mental|psychi|anxiety|depress|gad7|焦慮|憂鬱|心理|精神)/],
    ['cardiovascular', /(cardio|coronary|ascvd|heart|hypertension|vascular|cvd|心血管|冠心|心衰|高血壓)/],
    ['metabolic_endocrine', /(metabolic|endocrine|diabet|insulin|glucose|obesity|adiposity|anthropometr|bmi|tyg|homa|quicki|代謝|糖尿病|胰島素|肥胖)/],
  ];
  return keywordRules.find(([, pattern]) => pattern.test(token))?.[0] || null;
};

export const resolveRiskSection = (result = {}) => {
  if (result.clinical_system !== null && result.clinical_system !== undefined && result.clinical_system !== '') {
    return sectionFromText(result.clinical_system) || 'other';
  }

  const declaredSection = [result.organ_system, result.system, result.category]
    .map(sectionFromText)
    .find(Boolean);
  if (declaredSection) return declaredSection;

  const algorithm = normalizeToken(result.algorithm || result.algorithm_key);
  if (algorithmSectionMap[algorithm]) return algorithmSectionMap[algorithm];

  return sectionFromText([
    algorithm,
    result.outcome,
    result.outcome_key,
    result.display_name,
    result.algorithm_name,
    result.outcome_label,
  ]) || 'other';
};

const valueOrEmpty = (value) => {
  if (value === true) return '是';
  if (value === false) return '否';
  if (value === null || value === undefined || value === '') return '無資料';
  return String(value);
};

const normalizeComputedRiskResult = (result) => {
  const missing = result.missing_data_labels?.length
    ? result.missing_data_labels
    : (result.missing_data || []).map((field) => fieldLabels[field] || field);
  const level = missing.length ? 'missing' : (result.risk_level || 'missing');
  const limitations = Array.isArray(result.limitations) ? result.limitations : [];
  return {
    id: result.id || `${result.algorithm || 'algorithm'}-${result.outcome || 'outcome'}`,
    algorithm: result.algorithm,
    title: result.display_name_zh || result.display_name || result.algorithm_name || result.algorithm || '風險模型',
    titleEn: result.display_name_en || result.algorithm_name || result.display_name || result.algorithm || 'Risk model',
    item: result.outcome_label || result.outcome || '風險結果',
    value: missing.length ? '資料不足' : valueOrEmpty(result.risk_percentage),
    level,
    levelLabel: levelLabels[level] || valueOrEmpty(result.risk_level),
    sectionKey: resolveRiskSection(result),
    missing,
    limitations,
    recommendation: result.recommendation_text || '',
    review: Boolean(result.requires_doctor_review),
    applicability: result.applicability || 'applicable',
    catalogOnly: false,
    catalogKind: 'runtime',
  };
};

const catalogAlgorithms = (riskData) => (
  Array.isArray(riskData?.algorithm_catalog?.systems)
    ? riskData.algorithm_catalog.systems.flatMap((system) => (
      Array.isArray(system.algorithms)
        ? system.algorithms.map((algorithm) => ({
          ...algorithm,
          clinical_system: algorithm.clinical_system || system.code,
        }))
        : []
    ))
    : []
);

const catalogPlaceholderCard = (algorithm) => {
  const reviewRequired = algorithm.governance_status === 'clinical_review_required';
  const level = reviewRequired ? 'review_required' : 'not_run';
  const issues = Array.isArray(algorithm.issues) ? algorithm.issues : [];
  const clinicalReason = algorithm.clinical_review_reason
    ? [algorithm.clinical_review_reason]
    : [];
  return {
    id: `catalog-${algorithm.algorithm_id}`,
    algorithm: algorithm.algorithm_id,
    title: algorithm.display_name_zh || algorithm.display_name || algorithm.algorithm_id || '風險模型',
    titleEn: algorithm.display_name_en || algorithm.display_name || algorithm.algorithm_id || 'Risk model',
    item: algorithm.target || algorithm.declared_output || algorithm.outcome_key || '模型目錄項目',
    value: reviewRequired ? '待臨床審核' : '尚未執行',
    level,
    levelLabel: levelLabels[level],
    sectionKey: resolveRiskSection(algorithm),
    missing: [],
    limitations: [...clinicalReason, ...issues],
    recommendation: reviewRequired
      ? '完成醫院端臨床與文獻審核後才可啟用；目前不執行公式，也不產生風險分數。'
      : '選擇病患並執行分析後顯示結果。',
    review: reviewRequired,
    catalogOnly: true,
    catalogKind: algorithm.catalog_kind || 'runtime',
  };
};

export const normalizeRiskResults = (riskData) => {
  if (!Array.isArray(riskData?.disease_risk_results)) return [];
  return riskData.disease_risk_results
    .filter((result) => result.governance_status !== 'clinical_review_required')
    .map(normalizeComputedRiskResult);
};

export const normalizePendingModels = (riskData) => (
  catalogAlgorithms(riskData)
    .filter((algorithm) => algorithm.governance_status === 'clinical_review_required')
    .map(catalogPlaceholderCard)
);

export const groupRiskResults = (riskCards = []) => {
  const buckets = Object.fromEntries(RISK_SECTIONS.map((section) => [section.key, []]));
  riskCards.forEach((card) => {
    const key = sectionKeys.has(card.sectionKey) ? card.sectionKey : 'other';
    buckets[key].push(card);
  });
  return RISK_SECTIONS
    .map((section) => ({ ...section, cards: buckets[section.key] }))
    .filter((section) => section.cards.length > 0);
};

function RiskResultCard({ card }) {
  const style = levelStyles[card.level] || levelStyles.missing;
  const compactIssue = card.missing.length > 0
    ? `缺少：${card.missing.slice(0, 3).join('、')}${card.missing.length > 3 ? ` 等 ${card.missing.length} 項` : ''}`
    : card.applicability !== 'applicable' && card.limitations.length > 0
      ? card.limitations[0]
      : '';

  return (
    <Paper
      component="article"
      aria-label={`${card.title}，${card.titleEn}：${card.item}`}
      variant="outlined"
      sx={{
        position: 'relative',
        overflow: 'hidden',
        p: 1.5,
        minHeight: 132,
        borderColor: '#e1e8ec',
        borderRadius: 2,
        backgroundColor: '#ffffff',
        boxShadow: '0 2px 8px rgba(13, 36, 48, 0.035)',
        transition: 'border-color 180ms ease, transform 180ms ease, box-shadow 180ms ease',
        '&:hover': {
          transform: 'translateY(-2px)',
          borderColor: style.strip,
          boxShadow: '0 10px 24px rgba(13, 36, 48, 0.09)',
        },
      }}
    >
      <Box sx={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, background: style.strip }} />
      <Stack spacing={0.65} sx={{ height: '100%', pl: 0.35 }}>
        <Stack direction="row" spacing={0.75} justifyContent="space-between" alignItems="flex-start">
          <Box sx={{ minWidth: 0, pr: 0.25 }}>
            <Typography
              component="h3"
              noWrap
              title={card.title}
              sx={{ color: '#243f4a', fontSize: 13.5, lineHeight: 1.25, fontWeight: 900 }}
            >
              {card.title}
            </Typography>
            <Typography
              noWrap
              title={card.titleEn}
              sx={{ mt: 0.25, color: '#72818a', fontSize: 10.5, lineHeight: 1.25, fontWeight: 650 }}
            >
              {card.titleEn}
            </Typography>
          </Box>
          <Chip
            size="small"
            label={card.levelLabel}
            sx={{
              flexShrink: 0,
              height: 20,
              '& .MuiChip-label': { px: 0.75, fontSize: 10.5 },
              color: style.color,
              borderColor: style.border,
              backgroundColor: style.background,
              fontWeight: 800,
            }}
            variant="outlined"
          />
        </Stack>

        <Stack direction="row" spacing={0.8} alignItems="baseline" sx={{ mt: 'auto' }}>
          <Typography
            variant="h6"
            sx={{
              fontFamily: '"IBM Plex Sans", "Noto Sans TC", sans-serif',
              fontWeight: 850,
              color: style.color,
              lineHeight: 1.1,
              letterSpacing: '-0.035em',
              whiteSpace: 'nowrap',
            }}
          >
            {card.value}
          </Typography>
          <Typography variant="caption" sx={{ color: '#758490' }} noWrap title={card.item}>
            {card.item}
          </Typography>
        </Stack>

        {compactIssue && (
          <Typography variant="caption" sx={{ color: '#667783', fontSize: 10.5 }} noWrap title={compactIssue}>
            {compactIssue}
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}

function RiskAnalysis() {
  const [searchParams] = useSearchParams();
  const requestedPatientId = searchParams.get('patient_id') || '';
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState(requestedPatientId);
  const [riskData, setRiskData] = useState(null);
  const [algorithmCatalog, setAlgorithmCatalog] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const response = await api.get(`${API_CONFIG.ENDPOINTS.PATIENTS}?include_demo=true`);
        const data = await parseApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(data, '病患清單讀取失敗'));
        const list = [...listFromResponse(data)].sort(
          (left, right) => Number(Boolean(right.is_demo_patient)) - Number(Boolean(left.is_demo_patient)),
        );
        setPatients(list);
        if (requestedPatientId && list.some((patient) => String(patient.id) === requestedPatientId)) {
          setPatientId(requestedPatientId);
        }
      } catch (error) {
        setMessage({ type: 'error', text: error.message });
      }
    };
    fetchPatients();
  }, [requestedPatientId]);

  useEffect(() => {
    const fetchAlgorithmCatalog = async () => {
      try {
        const response = await api.get(API_CONFIG.ENDPOINTS.RISK_ALGORITHMS);
        const data = await parseApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(data, '風險模型目錄讀取失敗'));
        setAlgorithmCatalog(data);
      } catch (error) {
        setMessage({ type: 'error', text: error.message });
      }
    };
    fetchAlgorithmCatalog();
  }, []);

  const selectedPatient = patients.find((patient) => String(patient.id) === String(patientId));
  const patientSelectValue = selectedPatient ? patientId : '';
  const catalogViewData = useMemo(() => ({
    disease_risk_results: riskData?.disease_risk_results || [],
    algorithm_catalog: riskData?.algorithm_catalog || algorithmCatalog,
  }), [algorithmCatalog, riskData]);
  const riskCards = useMemo(() => normalizeRiskResults(riskData), [riskData]);
  const riskGroups = useMemo(() => groupRiskResults(riskCards), [riskCards]);
  const pendingCards = useMemo(() => normalizePendingModels(catalogViewData), [catalogViewData]);
  const pendingGroups = useMemo(() => groupRiskResults(pendingCards), [pendingCards]);
  const catalogCounts = catalogViewData.algorithm_catalog?.counts || {};
  const executionSummary = riskData?.execution_summary || {};
  const sourceData = riskData?.data_summary?.data || {};
  const visibleSnapshot = Object.entries(sourceData).filter(([key]) => fieldLabels[key]);
  const executableModels = Number(
    executionSummary.executable_models ?? catalogCounts.executable_models ?? riskCards.length ?? 0,
  );
  const calculatedModels = Number(executionSummary.calculated_models ?? riskCards.length ?? 0);
  const resolvedModels = Number(executionSummary.resolved_models ?? calculatedModels);
  const notApplicableModels = Number(executionSummary.not_applicable_models ?? 0);
  const completionRate = executableModels > 0
    ? Math.min(100, Math.round((resolvedModels / executableModels) * 100))
    : 0;
  const attentionModels = riskCards.filter((card) => ['moderate_high', 'high'].includes(card.level)).length;
  const missingModels = riskCards.filter((card) => card.level === 'missing').length;
  const selectedPatientName = selectedPatient
    ? (selectedPatient.demo_label
      || [selectedPatient.first_name, selectedPatient.last_name].filter(Boolean).join(' ')
      || selectedPatient.full_name
      || selectedPatient.id)
    : '尚未選擇病患';

  const calculateRisk = async () => {
    if (!patientId) {
      setMessage({ type: 'error', text: '請先選擇病患' });
      return;
    }

    setLoading(true);
    setMessage(null);
    setRiskData(null);

    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.RISK_ANALYSIS, { patient_id: patientId });
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, '風險分析失敗'));
      setRiskData(data);
      if (data.algorithm_catalog) setAlgorithmCatalog(data.algorithm_catalog);
      setMessage({ type: 'success', text: '後端已完成風險分析' });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      className="page-frame"
      sx={{
        '--risk-ink': '#102f3c',
        '--risk-mint': '#72d6c9',
        '@keyframes riskRise': {
          from: { opacity: 0, transform: 'translateY(10px)' },
          to: { opacity: 1, transform: 'translateY(0)' },
        },
        '@keyframes riskSpin': { to: { transform: 'rotate(360deg)' } },
        '@media (prefers-reduced-motion: reduce)': {
          '& *': { animationDuration: '0.01ms !important', transitionDuration: '0.01ms !important' },
        },
      }}
    >
      <Paper
        component="header"
        elevation={0}
        sx={{
          position: 'relative',
          overflow: 'hidden',
          minHeight: { xs: 260, md: 290 },
          px: { xs: 2.5, sm: 4, md: 5 },
          pt: { xs: 3, md: 4.5 },
          pb: { xs: 7, md: 8 },
          color: '#f7fbfa',
          borderRadius: { xs: 2.5, md: 3.5 },
          background: [
            'radial-gradient(circle at 82% 18%, rgba(114,214,201,.24) 0 1px, transparent 2px)',
            'radial-gradient(circle at 74% 68%, rgba(255,255,255,.11) 0 1px, transparent 2px)',
            'linear-gradient(128deg, #0b2937 0%, #123b48 58%, #17565a 100%)',
          ].join(','),
          backgroundSize: '25px 25px, 38px 38px, auto',
          boxShadow: '0 24px 55px rgba(12, 43, 55, 0.16)',
          '&::after': {
            content: '""',
            position: 'absolute',
            width: 320,
            height: 320,
            right: -90,
            bottom: -210,
            border: '1px solid rgba(151, 232, 220, .24)',
            borderRadius: '50%',
            boxShadow: '0 0 0 36px rgba(151,232,220,.035), 0 0 0 72px rgba(151,232,220,.025)',
          },
        }}
      >
        <Box sx={{ position: 'relative', zIndex: 1, display: 'grid', gap: 3, gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 1fr) auto' }, alignItems: 'end' }}>
          <Box>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
              <Box sx={{ width: 28, height: 1, backgroundColor: 'var(--risk-mint)' }} />
              <Typography variant="overline" sx={{ color: '#a9e3da', letterSpacing: '0.16em', fontWeight: 800 }}>
                RISK WORKSPACE · 風險分析
              </Typography>
            </Stack>
            <Typography component="h1" sx={{ fontSize: { xs: 32, sm: 42, md: 50 }, lineHeight: 1.04, fontWeight: 850, letterSpacing: '-0.045em' }}>
              全身風險圖譜
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
              <PersonOutlineRoundedIcon sx={{ fontSize: 18, color: '#a9e3da' }} />
              <Typography sx={{ color: '#d8e7e7', fontWeight: 650 }}>{selectedPatientName}</Typography>
              {selectedPatient?.is_demo_patient && (
                <Chip label="GOLDEN · SYNTHETIC" size="small" sx={{ color: '#0c343d', bgcolor: '#a9e3da', fontWeight: 900, letterSpacing: '.04em' }} />
              )}
            </Stack>
          </Box>

          <Stack direction="row" spacing={{ xs: 2, sm: 4 }} alignItems="center">
            <Box
              role="img"
              aria-label={`模型完成度 ${completionRate}%`}
              sx={{
                width: 86,
                height: 86,
                borderRadius: '50%',
                display: 'grid',
                placeItems: 'center',
                background: `conic-gradient(#8de1d5 ${completionRate * 3.6}deg, rgba(255,255,255,.14) 0deg)`,
                '&::before': { content: '""', position: 'absolute' },
              }}
            >
              <Box sx={{ width: 72, height: 72, borderRadius: '50%', bgcolor: '#123b48', display: 'grid', placeItems: 'center', textAlign: 'center' }}>
                <Box>
                  <Typography sx={{ fontSize: 23, lineHeight: 1, fontWeight: 900 }}>{completionRate}%</Typography>
                  <Typography sx={{ mt: 0.35, fontSize: 9.5, color: '#afd7d3', letterSpacing: '.08em' }}>COMPLETE</Typography>
                </Box>
              </Box>
            </Box>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, auto)', columnGap: 3, rowGap: 0.3 }}>
              <Typography sx={{ fontSize: 28, fontWeight: 850, lineHeight: 1 }}>{resolvedModels || '—'}</Typography>
              <Typography sx={{ fontSize: 28, fontWeight: 850, lineHeight: 1 }}>{riskGroups.length || '—'}</Typography>
              <Typography variant="caption" sx={{ color: '#afd0d0' }}>已解析模型</Typography>
              <Typography variant="caption" sx={{ color: '#afd0d0' }}>有結果分區</Typography>
            </Box>
          </Stack>
        </Box>
      </Paper>

      <Paper
        elevation={0}
        sx={{
          position: 'relative',
          zIndex: 2,
          mt: { xs: -4.5, md: -5 },
          mx: { xs: 1, sm: 2.5, md: 4 },
          p: { xs: 1.5, md: 2 },
          border: '1px solid #dce6e8',
          borderRadius: 2.5,
          boxShadow: '0 16px 38px rgba(17, 48, 61, 0.12)',
          animation: 'riskRise 420ms ease both',
        }}
      >
        <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr', md: 'minmax(280px, 1.4fr) minmax(220px, .8fr) auto' }, alignItems: 'center' }}>
          <FormControl fullWidth size="small">
            <InputLabel id="risk-patient-label">分析病患</InputLabel>
            <Select labelId="risk-patient-label" label="分析病患" value={patientSelectValue} onChange={(event) => setPatientId(event.target.value)}>
              {patients.map((patient) => (
                <MenuItem key={patient.id} value={patient.id}>
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" sx={{ width: '100%' }}>
                    <span>
                      {patient.is_demo_patient
                        ? (patient.demo_label || 'Golden Patient')
                        : ([patient.first_name, patient.last_name].filter(Boolean).join(' ') || patient.full_name || patient.id)}
                      {' '}· {patient.medical_record_number || patient.id}
                    </span>
                    {patient.is_demo_patient && <Chip size="small" label="DEMO" sx={{ height: 19, bgcolor: '#e5f7f3', color: '#17655f', fontWeight: 900 }} />}
                  </Stack>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Stack direction="row" spacing={1.2} alignItems="center" sx={{ px: { md: 1.5 }, minHeight: 40 }}>
            <DataObjectRoundedIcon sx={{ color: '#39766f', fontSize: 20 }} />
            <Box>
              <Typography variant="caption" sx={{ color: '#7a8992', display: 'block', lineHeight: 1.1 }}>資料策略</Typography>
              <Typography variant="body2" sx={{ color: '#263d48', fontWeight: 800 }}>最新臨床資料 · 自動溯源</Typography>
            </Box>
          </Stack>

          <Button
            variant="contained"
            endIcon={loading ? <RefreshIcon sx={{ animation: 'riskSpin 900ms linear infinite' }} /> : <ArrowForwardRoundedIcon />}
            disabled={!patientId || loading}
            onClick={calculateRisk}
            sx={{ minWidth: 142, minHeight: 42, bgcolor: '#126b65', boxShadow: 'none', '&:hover': { bgcolor: '#0c5753', boxShadow: 'none' } }}
          >
            {loading ? '運算中' : riskData ? '重新分析' : '執行分析'}
          </Button>
        </Box>

        {selectedPatient && (
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1.4, pt: 1.25, borderTop: '1px solid #edf1f2', color: '#637680' }}>
            {selectedPatient.is_demo_patient ? <CheckCircleRoundedIcon sx={{ fontSize: 16, color: '#2c8b73' }} /> : <PersonOutlineRoundedIcon sx={{ fontSize: 16 }} />}
            <Typography variant="caption">
              {selectedPatient.is_demo_patient
                ? '合成展示資料 · 正式資料庫、FHIR 映射與風險引擎完整串接'
                : `MRN ${selectedPatient.medical_record_number || '無資料'} · ${selectedPatient.age ?? '無資料'} 歲`}
            </Typography>
          </Stack>
        )}
      </Paper>

      {message && <Alert severity={message.type} variant="outlined" sx={{ mt: 2, mx: { xs: 1, md: 4 }, borderRadius: 2 }}>{message.text}</Alert>}

      {(riskData || algorithmCatalog) && (
        <Box sx={{ mt: { xs: 3, md: 4 }, mx: { xs: 0.5, md: 0 } }}>
          <Stack spacing={2.5}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'flex-end' }}>
              <Box>
                <Typography variant="overline" sx={{ color: '#39766f', fontWeight: 850, letterSpacing: '.13em' }}>CLINICAL ATLAS</Typography>
                <Typography component="h2" variant="h5" sx={{ color: 'var(--risk-ink)', letterSpacing: '-.025em' }}>
                  {riskData ? '模型結果總覽' : '已核准模型庫'}
                </Typography>
              </Box>
              <Stack direction="row" spacing={2.5} divider={<Divider orientation="vertical" flexItem />}>
                <Box><Typography variant="caption" color="text.secondary">正式模型</Typography><Typography sx={{ fontWeight: 900 }}>{executableModels || 0}</Typography></Box>
                <Box><Typography variant="caption" color="text.secondary">需留意</Typography><Typography sx={{ fontWeight: 900, color: attentionModels ? '#b94c3f' : '#29735f' }}>{attentionModels}</Typography></Box>
                <Box><Typography variant="caption" color="text.secondary">資料不足</Typography><Typography sx={{ fontWeight: 900, color: missingModels ? '#a26918' : '#29735f' }}>{missingModels}</Typography></Box>
              </Stack>
            </Stack>

            {riskData && (
              <Paper
                variant="outlined"
                sx={{
                  px: 2,
                  py: 1.25,
                  borderRadius: 2,
                  borderColor: executionSummary.all_executable_models_resolved ? '#b9dfd3' : '#ead7ac',
                  bgcolor: executionSummary.all_executable_models_resolved ? '#f0faf6' : '#fffaf0',
                }}
              >
                <Stack direction="row" spacing={1.2} alignItems="center">
                  <CheckCircleRoundedIcon sx={{ color: executionSummary.all_executable_models_resolved ? '#2c8b73' : '#a87522' }} />
                  <Typography variant="body2" sx={{ color: '#29434a', fontWeight: 750 }}>
                    {resolvedModels}/{executableModels} 模型已解析
                    {executionSummary.all_executable_models_resolved
                      ? ` · ${calculatedModels} 項產生分數${notApplicableModels ? `，${notApplicableModels} 項不適用` : ''}`
                      : ` · ${missingModels} 項資料不足`}
                  </Typography>
                </Stack>
              </Paper>
            )}

            {!riskData && (
              <Paper variant="outlined" sx={{ p: { xs: 3, md: 4 }, borderRadius: 2.5, borderStyle: 'dashed', borderColor: '#b9cbce', bgcolor: '#f9fcfb', textAlign: 'center' }}>
                <Typography sx={{ color: '#28434c', fontWeight: 850 }}>選擇病患後執行全部 {executableModels || 0} 項正式模型</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>結果會依器官系統自動分區。</Typography>
              </Paper>
            )}

            {riskData && riskCards.length > 0 ? (
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '210px minmax(0, 1fr)' }, gap: { xs: 2, lg: 2.5 }, alignItems: 'start' }}>
                <Paper
                  component="nav"
                  aria-label="風險系統索引"
                  variant="outlined"
                  sx={{
                    position: { lg: 'sticky' },
                    top: { lg: 92 },
                    zIndex: 1,
                    p: 1.25,
                    borderRadius: 2.5,
                    borderColor: '#dbe5e7',
                    backgroundColor: '#f8fbfa',
                  }}
                >
                  <Typography variant="caption" sx={{ display: 'block', px: 1, pt: 0.5, pb: 1, color: '#76868c', fontWeight: 850, letterSpacing: '.08em' }}>
                    系統索引
                  </Typography>
                  <Box sx={{ display: { xs: 'flex', lg: 'grid' }, gap: 0.5, overflowX: { xs: 'auto', lg: 'visible' }, pb: { xs: 0.5, lg: 0 } }}>
                    {riskGroups.map((group) => (
                      <Box
                        key={group.key}
                        component="a"
                        href={`#risk-section-${group.key}`}
                        sx={{
                          flexShrink: 0,
                          display: 'grid',
                          gridTemplateColumns: '34px minmax(0, 1fr) auto',
                          gap: 0.8,
                          alignItems: 'center',
                          minWidth: { xs: 160, lg: 0 },
                          px: 0.9,
                          py: 0.85,
                          color: '#263f49',
                          borderRadius: 1.5,
                          textDecoration: 'none',
                          transition: 'background-color 150ms ease, transform 150ms ease',
                          '&:hover': { backgroundColor: group.wash, transform: { lg: 'translateX(2px)' } },
                          '&:focus-visible': { outline: `3px solid ${group.border}`, outlineOffset: 1 },
                        }}
                      >
                        <Box sx={{ width: 32, height: 28, display: 'grid', placeItems: 'center', borderRadius: 1, bgcolor: group.wash, color: group.accent, fontSize: 10, fontWeight: 900, letterSpacing: '.04em' }}>
                          {group.code}
                        </Box>
                        <Typography variant="caption" noWrap sx={{ fontWeight: 800 }}>{group.title}</Typography>
                        <Typography variant="caption" sx={{ color: group.accent, fontWeight: 900 }}>{group.cards.length}</Typography>
                      </Box>
                    ))}
                  </Box>
                </Paper>

                <Stack spacing={2} sx={{ minWidth: 0 }}>

                {riskGroups.map((group, groupIndex) => (
                  <Box
                    component="section"
                    id={`risk-section-${group.key}`}
                    aria-labelledby={`risk-section-title-${group.key}`}
                    key={group.key}
                    sx={{ scrollMarginTop: 96, animation: `riskRise 420ms ${Math.min(groupIndex, 5) * 55}ms ease both` }}
                  >
                    <Paper variant="outlined" sx={{ overflow: 'hidden', borderColor: '#dce5e7', borderRadius: 2.5, backgroundColor: '#ffffff', boxShadow: '0 8px 28px rgba(18, 51, 63, .045)' }}>
                      <Box
                        sx={{
                          display: 'grid',
                          gridTemplateColumns: { xs: 'auto 1fr', sm: 'auto 1fr auto' },
                          columnGap: 1.4,
                          rowGap: 0.5,
                          alignItems: 'center',
                          px: { xs: 1.4, md: 1.75 },
                          py: 1.1,
                          background: `linear-gradient(90deg, ${group.wash} 0%, #ffffff 60%)`,
                          borderBottom: `1px solid ${group.border}`,
                        }}
                      >
                        <Box
                          aria-hidden="true"
                          sx={{
                            gridRow: { xs: '1 / span 2', sm: 'auto' },
                            width: 40,
                            height: 40,
                            display: 'grid',
                            placeItems: 'center',
                            color: '#ffffff',
                            backgroundColor: group.accent,
                            borderRadius: 1.25,
                            fontFamily: '"IBM Plex Sans", sans-serif',
                            fontSize: 10.5,
                            fontWeight: 900,
                            letterSpacing: '0.08em',
                          }}
                        >
                          {group.code}
                        </Box>
                        <Box sx={{ minWidth: 0 }}>
                          <Typography
                            component="h2"
                            variant="subtitle1"
                            id={`risk-section-title-${group.key}`}
                            sx={{ color: '#173642', fontWeight: 900, lineHeight: 1.2 }}
                          >
                            {group.title}
                          </Typography>
                          <Typography variant="caption" sx={{ color: '#73838b' }}>{group.description}</Typography>
                        </Box>
                        <Chip
                          size="small"
                          label={`${String(groupIndex + 1).padStart(2, '0')} · ${group.cards.length} 項`}
                          sx={{
                            gridColumn: { xs: 2, sm: 'auto' },
                            justifySelf: { xs: 'start', sm: 'end' },
                            color: group.accent,
                            backgroundColor: '#ffffff',
                            border: `1px solid ${group.border}`,
                            fontWeight: 800,
                          }}
                        />
                      </Box>

                      <Box
                        sx={{
                          display: 'grid',
                          gap: 1,
                          gridTemplateColumns: {
                            xs: '1fr',
                            sm: 'repeat(2, minmax(0, 1fr))',
                            lg: 'repeat(3, minmax(0, 1fr))',
                            xl: 'repeat(4, minmax(0, 1fr))',
                          },
                          p: { xs: 1.25, md: 1.5 },
                          backgroundColor: '#fbfcfc',
                        }}
                      >
                        {group.cards.map((card, cardIndex) => (
                          <RiskResultCard key={`${card.id}-${cardIndex}`} card={card} />
                        ))}
                      </Box>
                    </Paper>
                  </Box>
                ))}
                </Stack>
              </Box>
            ) : riskData ? (
              <Alert severity="warning">後端未回傳可顯示的風險結果。</Alert>
            ) : null}

            {pendingCards.length > 0 && (
              <Paper
                component="details"
                variant="outlined"
                sx={{ borderColor: '#e4d8bd', backgroundColor: '#fffcf5', overflow: 'hidden' }}
              >
                <Box
                  component="summary"
                  sx={{
                    cursor: 'pointer',
                    px: { xs: 2, md: 2.5 },
                    py: 2,
                    color: '#6f4d16',
                    fontWeight: 850,
                    '&::marker': { color: '#a87522' },
                  }}
                >
                  模型導入清單 · {pendingCards.length} 項（不屬於病患資料完整度）
                </Box>
                <Divider />
                <Stack spacing={2} sx={{ p: { xs: 2, md: 2.5 } }}>
                  <Typography variant="body2" color="text.secondary">
                    這些模型尚未完成醫院端版本、族群、門檻或來源核准，因此不執行公式、不產生病患分數。
                  </Typography>
                  {pendingGroups.map((group) => (
                    <Box key={`pending-${group.key}`}>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                        <Typography variant="subtitle2" sx={{ color: group.accent, fontWeight: 850 }}>
                          {group.title}
                        </Typography>
                        <Chip size="small" label={`${group.cards.length} 項`} variant="outlined" />
                      </Stack>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                        {group.cards.map((card) => (
                          <Chip
                            key={card.id}
                            label={card.title}
                            size="small"
                            sx={{ color: '#72551f', backgroundColor: '#fff', border: '1px solid #eadfc8' }}
                          />
                        ))}
                      </Box>
                    </Box>
                  ))}
                </Stack>
              </Paper>
            )}

            {visibleSnapshot.length > 0 && (
              <Paper component="details" variant="outlined" sx={{ borderColor: '#dce5e7', borderRadius: 2.5, overflow: 'hidden' }}>
                <Box component="summary" sx={{ cursor: 'pointer', px: 2, py: 1.5, color: '#29434a', fontWeight: 850, '&::marker': { color: '#39766f' } }}>
                  輸入資料快照 · {visibleSnapshot.length} 項
                </Box>
                <Divider />
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', sm: 'repeat(3, minmax(0, 1fr))', lg: 'repeat(6, minmax(0, 1fr))' },
                    bgcolor: '#fbfcfc',
                  }}
                >
                    {visibleSnapshot.map(([key, value]) => (
                      <Box key={key} sx={{ px: 1.5, py: 1.25, borderRight: '1px solid #edf1f2', borderBottom: '1px solid #edf1f2' }}>
                        <Typography variant="caption" sx={{ color: '#7a8992', display: 'block' }}>{fieldLabels[key]}</Typography>
                        <Typography variant="body2" sx={{ color: '#243c47', fontWeight: 850 }}>{valueOrEmpty(value)}</Typography>
                      </Box>
                    ))}
                </Box>
              </Paper>
            )}
          </Stack>
        </Box>
      )}
    </Box>
  );
}

export default RiskAnalysis;
