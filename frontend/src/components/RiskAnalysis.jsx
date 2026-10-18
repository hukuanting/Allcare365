import React, { lazy, Suspense, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import Alert from '@mui/material/Alert';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
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
import { RouteErrorBoundary } from './RouteExperience';
const DiseaseNetwork = lazy(() => import('./DiseaseNetwork'));
import { Link as RouterLink } from 'react-router-dom';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage, listFromResponse } from '../utils/apiData';
import { countValue } from '../utils/numericDisplay';

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
  ever_smoker: '曾有吸菸史',
  hba1c: 'HbA1c',
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

Object.assign(fieldLabels, {
  "ldl_cholesterol": "LDL 膽固醇",
  "ferritin": "鐵蛋白",
  "fasting_insulin": "空腹胰島素",
  "type_iv_collagen_7s": "第四型膠原蛋白 7S",
  "gamma_globulin": "γ 球蛋白",
  "vascular_risk_factor_count": "血管危險因子數",
  "family_history_dementia": "失智症家族史",
  "east_asian": "東亞族群狀態",
  "load_low_hdl_c": "LOAD 低 HDL 狀態",
  "load_high_whr": "LOAD 高腰臀比狀態",
  "load_ethnicity": "LOAD 原研究族群",
  "urine_albumin_creatinine_ratio": "尿白蛋白／肌酸酐比",
  "cimt_um": "頸動脈內膜中層厚度",
  "bcra_population": "BCRA 發生率參考族群",
  "breast_cancer_or_dcis_history": "乳癌或原位乳癌病史",
  "lcis_history": "小葉原位癌病史",
  "brca_mutation": "BRCA 致病變異狀態",
  "atypical_hyperplasia": "非典型乳房增生",
  "age_at_menarche": "初經年齡",
  "age_at_first_live_birth": "首次活產年齡",
  "number_of_breast_biopsies": "乳房切片次數",
  "first_degree_relatives_with_breast_cancer": "乳癌一等親人數",
  "diabetes_medication": "糖尿病用藥類別",
  "regular_pickled_food": "每週至少三次醃製食品",
  "regular_fried_food": "每週至少三次油炸食品",
  "h_pylori_igg_eiu": "幽門螺旋桿菌 IgG（EIU）",
  "pepsinogen_i_ii_ratio": "胃蛋白酶原 I／II 比",
  "gastrin_17_pmol_l": "胃泌素 17"
});

const snapshotUnits = { systolic_bp: 'mmHg', diastolic_bp: 'mmHg', fasting_glucose: 'mg/dL', hba1c: '%', bmi: 'kg/m²', waist_circumference: 'cm', total_cholesterol: 'mg/dL', hdl_cholesterol: 'mg/dL', triglycerides: 'mg/dL', egfr: 'mL/min/1.73m²', ferritin: 'ng/mL', fasting_insulin: 'µIU/mL', type_iv_collagen_7s: 'ng/mL', gamma_globulin: 'g/dL', ldl_cholesterol: 'mg/dL', urine_albumin_creatinine_ratio: 'mg/g', cimt_um: 'µm', h_pylori_igg_eiu: 'EIU', gastrin_17_pmol_l: 'pmol/L' };
const snapshotEnums = { diabetes_medication: { none: '未用藥', oral: '口服藥', insulin: '胰島素' }, load_ethnicity: { white: '白人', black: '黑人', hispanic: 'Hispanic' }, bcra_population: { chinese_american: '華裔美國女性' } };
export const snapshotDisplayValue = (key, value) => {
  const display = snapshotEnums[key]?.[value] || valueOrEmpty(value);
  return value !== null && value !== undefined && value !== '' && snapshotUnits[key] ? `${display} ${snapshotUnits[key]}` : display;
};

const levelLabels = {
  informational: '參考指標',
  not_run: '尚未執行',
  review_required: '模型準備中',
  missing: '資料不足',
  low: '低',
  moderate_low: '中低',
  moderate: '中',
  moderate_high: '中高',
  high: '高',
  not_applicable: '不適用',
};

const levelStyles = {
  informational: { color: '#475569', background: '#f8fafc', border: '#cbd5e1', strip: '#64748b' },
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

export const modelReferenceUrl = (value) => {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
};

const outcomeLabels = {
  "hepatic_steatosis_screening": "肝脂肪變性篩檢",
  "nafld_cardiovascular_risk": "非酒精性脂肪肝心血管風險",
  "incident_hypertension": "新發高血壓風險",
  "global_vascular_10_year_risk": "十年整體血管風險",
  "coronary_heart_disease_risk": "冠心病風險",
  "major_cardiovascular_event_10_year_risk": "十年主要心血管事件風險",
  "first_hard_ascvd_10_year_risk": "十年首次重大 ASCVD 事件風險",
  "body_mass_index": "身體質量指數",
  "insulin_resistance_index": "胰島素阻抗指數",
  "insulin_sensitivity_index": "胰島素敏感性指數",
  "cardiometabolic_index": "心臟代謝指數",
  "lipid_accumulation_index": "脂質蓄積指數",
  "dementia_5_year_risk": "五年失智風險",
  "mci_to_alzheimer_3_year_score": "三年輕度認知障礙轉阿茲海默症評分",
  "alzheimer_disease_risk_index": "阿茲海默症風險指數",
  "dementia_20_year_risk_score": "二十年失智風險評分",
  "dementia_6_year_screening_score": "六年失智篩檢評分",
  "pulmonary_nodule_malignancy": "肺結節惡性風險",
  "copd_screening_score": "慢性阻塞性肺病篩檢評分",
  "anxiety_symptom_severity": "焦慮症狀嚴重度"
};

const normalizeComputedRiskResult = (result) => {
  const missing = result.missing_data_labels?.length
    ? result.missing_data_labels
    : (result.missing_data || []).map((field) => fieldLabels[field] || field);
  const level = missing.length ? 'missing' : (result.risk_level || 'missing');
  const limitations = Array.isArray(result.limitations) ? result.limitations : [];
  const resultValue = result.algorithm === 'metabolic_syndrome' && ['yes', 'no'].includes(result.risk_percentage)
    ? (result.risk_percentage === 'yes' ? '符合' : '未符合')
    : valueOrEmpty(result.risk_percentage);
  return {
    id: result.id || `${result.algorithm || 'algorithm'}-${result.outcome || 'outcome'}`,
    algorithm: result.algorithm,
    title: result.display_name_zh || result.display_name || result.algorithm_name || result.algorithm || '風險模型',
    titleEn: result.display_name_en || result.algorithm_name || result.display_name || result.algorithm || 'Risk model',
    item: outcomeLabels[result.outcome_label] || result.outcome_label || outcomeLabels[result.outcome] || result.outcome || '風險結果',
    value: missing.length ? '資料不足' : resultValue,
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
    modelVersion: result.model_version || '',
    sourceDocument: result.evidence?.source_document || '',
    referenceUrl: modelReferenceUrl(result.method_uri || result.evidence?.reference),
    timeHorizon: result.evidence?.time_horizon || '',
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
    value: reviewRequired ? '模型準備中' : '尚未執行',
    level,
    levelLabel: levelLabels[level],
    sectionKey: resolveRiskSection(algorithm),
    missing: [],
    limitations: [...clinicalReason, ...issues],
    recommendation: reviewRequired
      ? '此模型尚未啟用。'
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

export const filterRiskResults = (cards, query = '', status = 'all') => {
  const needle = query.trim().toLocaleLowerCase();
  return cards.filter(card => {
    const matchesText = !needle || [card.title, card.titleEn, card.item, card.algorithm]
      .some(value => String(value || '').toLocaleLowerCase().includes(needle));
    const matchesStatus = status === 'all'
      || (status === 'attention' && ['moderate_high', 'high'].includes(card.level))
      || (status === 'missing' && card.level === 'missing')
      || (status === 'not_applicable' && card.applicability === 'not_applicable');
    return matchesText && matchesStatus;
  });
};

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
  const hasDetails = card.missing.length > 0 || card.limitations.length > 0 || card.recommendation || card.review || card.sourceDocument || card.referenceUrl || card.modelVersion;

  return (
    <Paper component="article" aria-label={`${card.title}，${card.titleEn}：${card.item}`}
      variant="outlined" className="risk-result"
      style={{ '--risk-status': style.color, '--risk-strip': style.strip }}>
      <div className="risk-result-heading">
        <div>
          <Typography component="h3" className="risk-result-title">{card.title}</Typography>
          <Typography className="risk-result-english" lang="en">{card.titleEn}</Typography>
        </div>
        <Chip size="small" label={card.levelLabel} variant="outlined" sx={{
          height: 26, flexShrink: 0, fontWeight: 600,
          '& .MuiChip-label': { px: 1, fontSize: 12 },
          color: style.color, borderColor: style.border, backgroundColor: style.background,
        }} />
      </div>
      <div className="risk-result-score">
        <Typography component="p" className="risk-result-value">{card.value}</Typography>
        <Typography component="p" className="risk-result-outcome">{card.item}</Typography>
      </div>
      {card.missing.length > 0 && <p className="risk-result-note">缺少 {card.missing.length} 項輸入資料</p>}
      {hasDetails && <details className="risk-result-details">
        <summary>查看評估細節</summary>
        {card.missing.length > 0 && <div><h4>缺少資料</h4><ul>{card.missing.map((item,index)=><li key={index}>{item}</li>)}</ul></div>}
        {card.limitations.length > 0 && <div><h4>模型限制</h4><ul>{card.limitations.map((item,index)=><li key={index}>{item}</li>)}</ul></div>}
        {card.recommendation && <div><h4>判讀建議</h4><p>{card.recommendation}</p></div>}
        {(card.sourceDocument || card.referenceUrl || card.modelVersion) && <div>
          <h4>模型來源</h4>
          {card.sourceDocument && <p>{card.sourceDocument}</p>}
          {card.timeHorizon && <p>評估期間：{card.timeHorizon}</p>}
          {card.modelVersion && <p>版本：{card.modelVersion}</p>}
          {card.referenceUrl && <a href={card.referenceUrl} target="_blank" rel="noopener noreferrer">閱讀原始參考文獻 ↗</a>}
        </div>}
      </details>}
    </Paper>
  );
}

function RiskAnalysis({ network = false }) {
  const [searchParams] = useSearchParams();
  const requestedPatientId = searchParams.get('patient_id') || '';
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState(requestedPatientId);
  const [riskData, setRiskData] = useState(null);
  const [algorithmCatalog, setAlgorithmCatalog] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const analysisFeedback = useRef(null);
  useEffect(() => {
    if (!loading && message?.type === 'error') analysisFeedback.current?.focus();
  }, [loading, message]);
  const [patientSearch, setPatientSearch] = useState('');
  const patientSearchInput = useRef(null);
  const clearPatientSearch = () => {
    setPatientSearch(''); setPatientId(''); setRiskData(null); setMessage(null);
    patientSearchInput.current?.focus();
  };
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [patientError, setPatientError] = useState('');
  const [patientReload, setPatientReload] = useState(0);
  const analysisRequest = useRef(null);
  const [resultQuery, setResultQuery] = useState('');
  const resultSearchInput = useRef(null);
  const clearResultFilters = () => {
    setResultQuery(''); setResultStatus('all');
    resultSearchInput.current?.focus();
  };
  const [resultStatus, setResultStatus] = useState('all');

  useEffect(() => {
    setResultQuery('');
    setResultStatus('all');
  }, [patientId]);

  useLayoutEffect(() => {
    // Clear a different patient context before paint; paired view links retain the selected patient.
    // View links may synchronise the URL to a patient already selected in this workspace.
    if (String(patientId) === requestedPatientId) return;
    analysisRequest.current?.abort();
    setPatientSearch('');
    setPatientId(requestedPatientId); setRiskData(null); setMessage(null); setLoading(false);
  }, [requestedPatientId]);

  useEffect(() => () => analysisRequest.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();
    setPatientsLoading(true); setPatientError(''); setPatients([]);
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({ include_demo: 'true' });
        if (patientSearch.trim()) params.set('search', patientSearch.trim());
        const response = await api.get(API_CONFIG.ENDPOINTS.PATIENTS + '?' + params, { signal: controller.signal });
        const data = await parseApiResponse(response);
        if (controller.signal.aborted) return;
        if (!response.ok) throw new Error(apiErrorMessage(data, '病患清單讀取失敗'));
        const list = [...listFromResponse(data)];
        if (requestedPatientId && !patientSearch.trim() && !list.some(patient => String(patient.id) === requestedPatientId)) {
          const detail = await api.get(API_CONFIG.ENDPOINTS.PATIENTS + encodeURIComponent(requestedPatientId) + '/', { signal: controller.signal });
          const patient = await parseApiResponse(detail);
          if (controller.signal.aborted) return;
          if (!detail.ok || String(patient?.id) !== requestedPatientId) throw new Error('無法讀取指定病患，請確認存取權限。');
          list.unshift(patient);
        }
        list.sort((left,right) => Number(Boolean(right.is_demo_patient)) - Number(Boolean(left.is_demo_patient)));
        setPatients(list);
      } catch (error) { if (!controller.signal.aborted) setPatientError(error.message); }
      finally { if (!controller.signal.aborted) setPatientsLoading(false); }
    }, patientSearch.trim() ? 300 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [requestedPatientId, patientSearch, patientReload]);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const response = await api.get(API_CONFIG.ENDPOINTS.RISK_ALGORITHMS, { signal: controller.signal });
        const data = await parseApiResponse(response);
        if (controller.signal.aborted) return;
        if (!response.ok) throw new Error(apiErrorMessage(data, '風險模型目錄讀取失敗'));
        setAlgorithmCatalog(data);
      } catch (error) { if (!controller.signal.aborted) setMessage({ type: 'error', text: error.message }); }
    })();
    return () => controller.abort();
  }, []);

  const selectedPatient = patients.find((patient) => String(patient.id) === String(patientId));
  const patientSelectValue = selectedPatient ? patientId : '';
  const catalogViewData = useMemo(() => ({
    disease_risk_results: riskData?.disease_risk_results || [],
    algorithm_catalog: riskData?.algorithm_catalog || algorithmCatalog,
  }), [algorithmCatalog, riskData]);
  const riskCards = useMemo(() => normalizeRiskResults(riskData), [riskData]);
  const visibleCards = useMemo(() => filterRiskResults(riskCards, resultQuery, resultStatus), [riskCards, resultQuery, resultStatus]);
  const riskGroups = useMemo(() => groupRiskResults(visibleCards), [visibleCards]);
  const catalogCounts = catalogViewData.algorithm_catalog?.counts || {};
  const executionSummary = riskData?.execution_summary || {};
  const sourceData = riskData?.data_summary?.data || {};
  const visibleSnapshot = Object.entries(sourceData).filter(([key]) => fieldLabels[key]);
  const executableModels = countValue(executionSummary.executable_models ?? catalogCounts.executable_models);
  const calculatedModels = countValue(executionSummary.calculated_models);
  const resolvedModels = countValue(executionSummary.resolved_models);
  const notApplicableModels = countValue(executionSummary.not_applicable_models);
  const executableLabel = executableModels ?? '未提供';
  const resolvedLabel = resolvedModels ?? '未提供';
  const completionRate = executableModels > 0 && resolvedModels !== null && resolvedModels <= executableModels
    ? Math.round((resolvedModels / executableModels) * 100) : null;
  const allResolved = executionSummary.all_executable_models_resolved === true
    && executableModels !== null && resolvedModels === executableModels;
  const attentionModels = riskCards.filter((card) => ['moderate_high', 'high'].includes(card.level)).length;
  const missingModels = riskCards.filter((card) => card.level === 'missing').length;
  const selectedPatientName = selectedPatient
    ? (selectedPatient.demo_label
      || selectedPatient.full_name
      || [selectedPatient.last_name, selectedPatient.first_name].filter(Boolean).join(' ')
      || selectedPatient.id)
    : '尚未選擇病患';

  const calculateRisk = async () => {
    if (analysisRequest.current && !analysisRequest.current.signal.aborted) return;
    if (!selectedPatient || patientsLoading || loading) {
      setMessage({ type: 'error', text: '請先選擇病患' });
      return;
    }

    analysisRequest.current?.abort();
    const controller = new AbortController();
    analysisRequest.current = controller;
    setLoading(true);
    setMessage(null);
    setRiskData(null);

    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.RISK_ANALYSIS, { patient_id: patientId }, { signal: controller.signal });
      const data = await parseApiResponse(response);
      if (controller.signal.aborted) return;
      if (!response.ok) throw new Error(apiErrorMessage(data, '風險分析失敗'));
      setRiskData(data);
      if (data.algorithm_catalog) setAlgorithmCatalog(data.algorithm_catalog);
      setMessage({ type: 'success', text: '分析已完成，可探索各領域結果與共同資料因子。' });
    } catch (error) {
      if (!controller.signal.aborted) setMessage({ type: 'error', text: error.message });
    } finally {
      if (analysisRequest.current === controller) analysisRequest.current = null;
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  return (
    <Box
      className="page-frame atlas-risk"
      sx={{
        '--risk-ink': '#202d27',
        '--risk-mint': '#a2b99f',
        '@keyframes riskRise': {
          from: { opacity: 0, transform: 'translateY(10px)' },
          to: { opacity: 1, transform: 'translateY(0)' },
        },
        '@keyframes riskSpin': { to: { transform: 'rotate(360deg)' } },
        '@media (prefers-reduced-motion: reduce)': {
          '& *': { animation: 'none !important', transition: 'none !important' },
        },
      }}
    >
      <header className="risk-workspace-heading"><div><span className="atlas-eyebrow">CLINICAL ATLAS / RISK WORKSPACE</span><Typography component="h1" variant="h4">{network ? '疾病網絡' : '全身風險圖譜'}</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>串聯評估結果，探索健康領域與下一步資料。</Typography></div><div className="risk-completion" role="status" aria-live="polite" aria-atomic="true"><span>{loading ? '正在分析' : riskData ? resolvedLabel + ' / ' + executableLabel : '尚未分析'}</span><small>{loading ? '正在整理評估結果與健康領域關聯' : riskData ? (completionRate === null ? '解析比例未提供' : '模型已解析 · ' + completionRate + '%') : selectedPatient ? '病患已選擇，請執行分析' : '選擇病患後執行分析'}</small></div></header>
      <Paper className="work-panel risk-patient-panel">
        <div className="risk-patient-controls">
          <TextField inputRef={patientSearchInput} inputProps={{ 'aria-keyshortcuts': 'Escape' }} helperText="按 Esc 清除搜尋。" onKeyDown={event => { if (event.key === 'Escape' && patientSearch && !loading && !event.nativeEvent.isComposing) { event.preventDefault(); event.stopPropagation(); clearPatientSearch(); } }} InputProps={{ endAdornment: patientSearch ? <InputAdornment position="end"><IconButton aria-label="清除病患搜尋" onClick={clearPatientSearch} disabled={loading} sx={{ width: 44, height: 44 }}><CloseIcon fontSize="small" /></IconButton></InputAdornment> : undefined }} size="small" label="搜尋姓名或 MRN" value={patientSearch} disabled={loading} onChange={event => { setPatientSearch(event.target.value); setPatientId(''); setRiskData(null); setMessage(null); }} />
          <FormControl fullWidth size="small"><InputLabel id="risk-patient-label">分析病患</InputLabel><Select labelId="risk-patient-label" label="分析病患" value={patientSelectValue} disabled={loading || patientsLoading || Boolean(patientError)} onChange={event => { setPatientId(event.target.value); setRiskData(null); setMessage(null); }}>{patients.map(patient => <MenuItem key={patient.id} value={patient.id}>{patient.demo_label || patient.full_name || [patient.last_name,patient.first_name].filter(Boolean).join(' ') || patient.id} · {patient.medical_record_number || patient.id}</MenuItem>)}</Select></FormControl>
          <Button variant="contained" endIcon={loading ? <RefreshIcon sx={{ animation: 'riskSpin 900ms linear infinite' }} /> : <ArrowForwardRoundedIcon />} disabled={!selectedPatient || loading || patientsLoading} onClick={calculateRisk}>{loading ? '運算中' : riskData ? '重新分析' : '執行分析'}</Button>
        </div>
        {patientsLoading && <Typography role="status" variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>正在讀取病患資料…</Typography>}
        {!patientsLoading && !patientError && patients.length === 0 && <Typography role="status" variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>{patientSearch.trim() ? '沒有符合搜尋條件的病患。可調整姓名或 MRN，或清除搜尋。' : '目前沒有可供分析的病患。'}</Typography>}
        {patientError && <Alert severity="error" sx={{ mt: 2 }} action={<Button onClick={() => setPatientReload(value => value + 1)}>重試</Button>}>{patientError}</Alert>}
        {selectedPatient && <div className="risk-patient-identity"><PersonOutlineRoundedIcon fontSize="small" /><Typography variant="body2">{selectedPatientName}</Typography><Typography variant="caption" color="text.secondary">MRN {selectedPatient.medical_record_number || '未提供'} · {selectedPatient.age == null ? '年齡未提供' : selectedPatient.age + ' 歲'}</Typography></div>}
        {selectedPatient?.is_demo_patient && <Alert severity="info" sx={{ mt: 2 }}>合成測試病患</Alert>}
      </Paper>

      {message && <Alert ref={analysisFeedback} tabIndex={-1} role={message.type === 'success' ? 'status' : 'alert'} severity={message.type} variant="outlined" sx={{ mt: 2, mx: { xs: 1, md: 4 }, borderRadius: 2 }}>{message.text}</Alert>}

      <Box sx={{ mt: 2 }}><Button component={RouterLink} to={(network ? '/risk-analysis' : '/disease-network') + (patientId ? '?patient_id=' + encodeURIComponent(patientId) : '')}>{network ? '切換至模型清單' : '探索疾病網絡'} →</Button></Box>
      {network && riskData && <RouteErrorBoundary key={patientId} fallback={<Alert severity="error"><Typography component="p" variant="body2">疾病網絡無法載入。您仍可查看本次分析摘要與模型結果。</Typography><Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1.5 }}><Button component={RouterLink} to={'/risk-analysis?patient_id=' + encodeURIComponent(patientId)}>查看模型清單</Button><Button onClick={() => window.location.reload()}>重新載入頁面</Button></Stack><Typography variant="caption">重新載入後需再次執行分析。</Typography></Alert>}><Suspense fallback={<p role="status">正在建立疾病網絡…</p>}><DiseaseNetwork key={patientId} groups={groupRiskResults(riskCards)} catalog={riskData.algorithm_catalog || algorithmCatalog} snapshot={sourceData} labels={fieldLabels} patientId={patientId} patientName={selectedPatientName} formatValue={snapshotDisplayValue} /></Suspense></RouteErrorBoundary>}
      {!network && (riskData || algorithmCatalog) && (
        <Box sx={{ mt: { xs: 3, md: 4 }, mx: { xs: 0.5, md: 0 } }}>
          <Stack spacing={2.5}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'flex-end' }}>
              <Box>
                <Typography variant="overline" sx={{ color: '#39766f', fontWeight: 850, letterSpacing: '.13em' }}>CLINICAL ATLAS</Typography>
                <Typography component="h2" variant="h5" sx={{ color: 'var(--risk-ink)', letterSpacing: '-.025em' }}>
                  {riskData ? '模型結果總覽' : '風險模型庫'}
                </Typography>
              </Box>
              <Stack direction="row" spacing={2.5} divider={<Divider orientation="vertical" flexItem />}>
                <Box><Typography variant="caption" color="text.secondary">正式模型</Typography><Typography sx={{ fontWeight: 900 }}>{executableLabel}</Typography></Box>
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
                  borderRadius: 1,
                  borderColor: allResolved ? '#b9dfd3' : '#ead7ac',
                  bgcolor: allResolved ? '#f0faf6' : '#fffaf0',
                }}
              >
                <Stack direction="row" spacing={1.2} alignItems="center">
                  <CheckCircleRoundedIcon sx={{ color: allResolved ? '#2c8b73' : '#a87522' }} />
                  <Typography variant="body2" sx={{ color: '#29434a', fontWeight: 750 }}>
                    {resolvedLabel}/{executableLabel} 模型已解析
                    {allResolved
                      ? ` · ${calculatedModels ?? '未提供'} 項產生分數${notApplicableModels ? `，${notApplicableModels} 項不適用` : ''}`
                      : ` · ${missingModels} 項資料不足`}
                  </Typography>
                </Stack>
              </Paper>
            )}

            {!riskData && (
              <Paper variant="outlined" sx={{ p: { xs: 3, md: 4 }, borderRadius: 1, borderStyle: 'dashed', borderColor: '#b9cbce', bgcolor: '#f9fcfb', textAlign: 'center' }}>
                <Typography sx={{ color: '#28434c', fontWeight: 850 }}>{executableModels === null ? '選擇病患後執行風險分析' : '選擇病患後執行全部 ' + executableModels + ' 項正式模型'}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>結果會依器官系統自動分區。</Typography>
              </Paper>
            )}

            {riskData && riskCards.length > 0 && (
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems={{ sm: 'center' }}>
                <TextField inputRef={resultSearchInput} size="small" label="搜尋模型或評估項目" value={resultQuery} onChange={event => setResultQuery(event.target.value)} sx={{ flex: 1 }} />
                <FormControl size="small" sx={{ minWidth: 160 }}>
                  <InputLabel id="risk-result-status-label">結果狀態</InputLabel>
                  <Select labelId="risk-result-status-label" label="結果狀態" value={resultStatus} onChange={event => setResultStatus(event.target.value)}>
                    <MenuItem value="all">全部結果</MenuItem><MenuItem value="attention">需留意</MenuItem><MenuItem value="missing">資料不足</MenuItem><MenuItem value="not_applicable">不適用</MenuItem>
                  </Select>
                </FormControl>
                <Typography variant="caption" color="text.secondary" role="status">顯示 {visibleCards.length} / {riskCards.length} 項</Typography>
              </Stack>
            )}
            {riskData && riskCards.length > 0 && visibleCards.length === 0 && <Alert severity="info" action={<Button onClick={clearResultFilters}>清除篩選</Button>}>沒有符合條件的結果。可調整搜尋或結果狀態。</Alert>}
            {riskData && riskCards.length > 0 ? (
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', lg: '210px minmax(0, 1fr)' }, gap: { xs: 2, lg: 2.5 }, alignItems: 'start' }}>
                <Paper
                  component="nav"
                  aria-label="風險系統索引"
                  variant="outlined"
                  sx={{
                    minWidth: 0,
                    position: { lg: 'sticky' },
                    top: { lg: 92 },
                    zIndex: 1,
                    p: 1.25,
                    borderRadius: 1,
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
                    <Paper variant="outlined" sx={{ overflow: 'hidden', borderColor: '#dce5e7', borderRadius: 1, backgroundColor: '#ffffff', boxShadow: 'none' }}>
                      <Box
                        sx={{
                          display: 'grid',
                          gridTemplateColumns: { xs: 'auto 1fr', sm: 'auto 1fr auto' },
                          columnGap: 1.4,
                          rowGap: 0.5,
                          alignItems: 'center',
                          px: { xs: 1.4, md: 1.75 },
                          py: 1.1,
                          background: group.wash,
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
                            fontFamily: 'var(--atlas-sans)',
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
                          <Typography variant="caption" sx={{ color: 'var(--atlas-muted)' }}>{group.description}</Typography>
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
                          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))',
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
              <Alert severity="warning" action={<Button component={RouterLink} to={'/patients/' + encodeURIComponent(patientId)}>核對病患資料</Button>}>本次分析沒有產生模型結果。可核對病患資料後重新分析。</Alert>
            ) : null}

            {visibleSnapshot.length > 0 && (
              <Paper component="details" variant="outlined" sx={{ borderColor: '#dce5e7', borderRadius: 1, overflow: 'hidden' }}>
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
                      <Box key={key} sx={{ minWidth: 0, overflowWrap: 'anywhere', px: 1.5, py: 1.25, borderRight: '1px solid #edf1f2', borderBottom: '1px solid #edf1f2' }}>
                        <Typography variant="caption" sx={{ color: 'var(--atlas-muted)', display: 'block' }}>{fieldLabels[key]}</Typography>
                        <Typography variant="body2" sx={{ color: '#243c47', fontWeight: 850 }}>{snapshotDisplayValue(key, value)}</Typography>
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
