import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import SaveIcon from '@mui/icons-material/Save';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage, listFromResponse } from '../utils/apiData';

const today = () => {
  const date = new Date();
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
};

const initialForm = {
  patient: '',
  screening_date: today(),
  encounter_type: 'annual_physical',
  encounter_location: '',
  body_height: '',
  body_weight: '',
  waist_circumference: '',
  hip_circumference: '',
  systolic_blood_pressure: '',
  diastolic_blood_pressure: '',
  heart_rate: '',
  respiratory_rate: '',
  body_temperature: '',
  pulse_oximetry: '',
  fasting_glucose: '',
  hba1c: '',
  total_cholesterol: '',
  hdl_cholesterol: '',
  ldl_cholesterol: '',
  triglycerides: '',
  creatinine: '',
  urine_albumin_creatinine_ratio: '',
  platelet_count: '',
  alt_gpt: '',
  ast_got: '',
  ast_uln: '',
  ggt: '',
  albumin: '',
  insulin: '',
  alcohol_drinks_per_week: '',
  apoe_e4: '',
  smoking_status: '',
  alcohol_use: '',
  physical_activity: '',
  health_concerns: '',
  has_diabetes: '',
  has_hypertension: '',
  has_dyslipidemia: '',
  family_history_diabetes: '',
  prediabetes: '',
  dm_treated: '',
  hypertension_treated: '',
  lipid_lowering_treated: '',
  vegetables_daily: '',
  physical_activity_active: '',
  chd_history: '',
  cvd_history: '',
  pvd_history: '',
};

const numeric = (value) => {
  if (value === '' || value === null || value === undefined) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
};

const compact = (obj) => Object.fromEntries(
  Object.entries(obj).filter(([, value]) => value !== '' && value !== null && value !== undefined),
);

const vitalFields = [
  ['body_height', '身高', 'cm'],
  ['body_weight', '體重', 'kg'],
  ['waist_circumference', '腰圍', 'cm'],
  ['hip_circumference', '臀圍', 'cm'],
  ['systolic_blood_pressure', '收縮壓 SBP', 'mmHg'],
  ['diastolic_blood_pressure', '舒張壓 DBP', 'mmHg'],
  ['heart_rate', '心率', 'bpm'],
  ['respiratory_rate', '呼吸速率', '/min'],
  ['body_temperature', '體溫', '°C'],
  ['pulse_oximetry', '血氧 SpO2', '%'],
];

const labFields = [
  ['fasting_glucose', '空腹血糖 FPG', 'mg/dL'],
  ['hba1c', 'HbA1c', '%'],
  ['total_cholesterol', '總膽固醇 TC', 'mg/dL'],
  ['hdl_cholesterol', 'HDL', 'mg/dL'],
  ['ldl_cholesterol', 'LDL', 'mg/dL'],
  ['triglycerides', '三酸甘油脂 TG', 'mg/dL'],
  ['creatinine', '肌酸酐', 'mg/dL'],
  ['urine_albumin_creatinine_ratio', 'UACR', 'mg/g'],
  ['platelet_count', '血小板', '10³/µL'],
  ['alt_gpt', 'ALT', 'U/L'],
  ['ast_got', 'AST', 'U/L'],
  ['ast_uln', 'AST 正常上限', 'U/L'],
  ['ggt', 'GGT', 'U/L'],
  ['albumin', '白蛋白', 'g/dL'],
  ['insulin', '胰島素', 'uIU/mL'],
  ['alcohol_drinks_per_week', '每週酒精量', 'drinks'],
  ['apoe_e4', 'APOE e4', 'count'],
];

const questionnaireFields = [
  ['family_history_diabetes', '糖尿病家族史'], ['prediabetes', '糖尿病前期'],
  ['dm_treated', '糖尿病治療中'], ['hypertension_treated', '高血壓治療中'],
  ['lipid_lowering_treated', '降血脂治療中'], ['vegetables_daily', '每日蔬菜'],
  ['physical_activity_active', '規律活動'], ['chd_history', '冠心病病史'],
  ['cvd_history', '心血管疾病病史'], ['pvd_history', '周邊血管疾病病史'],
  ['has_diabetes', '糖尿病'], ['has_hypertension', '高血壓'], ['has_dyslipidemia', '血脂異常'],
];
const knownBoolean = value => value === '' ? undefined : value === 'yes';
const smokingFlag = (value, target) => value === '' ? undefined : value === target;

function HealthDataInput() {
  const [searchParams] = useSearchParams();
  const requestedPatient = searchParams.get('patient_id') || '';
  const [form, setForm] = useState(() => ({ ...initialForm, screening_date: today(), patient: '' }));
  const [patients, setPatients] = useState([]);
  const [loadingPatients, setLoadingPatients] = useState(false);
  const [saving, setSaving] = useState(false);
  const saveLock = useRef(false);
  const saveContext = useRef(0);
  const saveFeedback = useRef(null);
  const [message, setMessage] = useState(null);
  const [lastScreening, setLastScreening] = useState(null);
  const [patientSearch, setPatientSearch] = useState('');
  const [patientLoadError, setPatientLoadError] = useState('');
  const [patientReload, setPatientReload] = useState(0);

  useEffect(() => {
    if (message) saveFeedback.current?.focus();
  }, [message]);

  useLayoutEffect(() => {
    // Reset the previous patient draft before the new route is painted.
    saveLock.current = false;
    setSaving(false);
    setForm({ ...initialForm, screening_date: today(), patient: '' });
    setPatientSearch('');
    setLastScreening(null);
    setMessage(null);
    return () => { saveContext.current += 1; };
  }, [requestedPatient]);

  useEffect(() => {
    const controller = new AbortController();
    setLoadingPatients(true);
    setPatientLoadError('');
    setPatients([]);
    const load = async () => {
      try {
        const endpoint = requestedPatient
          ? API_CONFIG.ENDPOINTS.PATIENTS + encodeURIComponent(requestedPatient) + '/'
          : API_CONFIG.ENDPOINTS.PATIENTS + (patientSearch.trim() ? '?search=' + encodeURIComponent(patientSearch.trim()) : '');
        const response = await api.get(endpoint, { signal: controller.signal });
        const data = await parseApiResponse(response);
        if (controller.signal.aborted) return;
        if (!response.ok) throw new Error(apiErrorMessage(data, '無法讀取病患資料，請稍後重試。'));
        if (requestedPatient && String(data?.id) !== requestedPatient) throw new Error('病患資料不符，請返回病歷重新開啟。');
        setPatients(requestedPatient ? [data] : listFromResponse(data));
        if (requestedPatient) setForm(current => ({ ...current, patient: String(data.id) }));
      } catch (error) {
        if (!controller.signal.aborted) setPatientLoadError(error.message);
      } finally {
        if (!controller.signal.aborted) setLoadingPatients(false);
      }
    };
    const timer = setTimeout(load, !requestedPatient && patientSearch.trim() ? 300 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [requestedPatient, patientSearch, patientReload]);

  const selectedPatient = patients.find((patient) => String(patient.id) === String(form.patient));

  const bmi = useMemo(() => {
    const height = numeric(form.body_height);
    const weight = numeric(form.body_weight);
    if (!(height > 0) || !(weight > 0)) return null;
    const value = weight / ((height / 100) ** 2);
    return Number.isFinite(value) ? value.toFixed(1) : null;
  }, [form.body_height, form.body_weight]);

  const updateField = (field, value) => {
    if (field === 'patient') {
      if (String(value) === String(form.patient)) return;
      setForm({ ...initialForm, screening_date: today(), patient: value });
      setLastScreening(null);
      setMessage(null);
      return;
    }
    setForm((current) => ({ ...current, [field]: value }));
  };

  const buildPayload = () => ({
    patient: form.patient,
    screening_date: form.screening_date,
    encounter_type: form.encounter_type,
    encounter_location: form.encounter_location,
    vital_signs: compact({
      body_height: numeric(form.body_height),
      body_weight: numeric(form.body_weight),
      systolic_blood_pressure: numeric(form.systolic_blood_pressure),
      diastolic_blood_pressure: numeric(form.diastolic_blood_pressure),
      heart_rate: numeric(form.heart_rate),
      respiratory_rate: numeric(form.respiratory_rate),
      body_temperature: numeric(form.body_temperature),
      pulse_oximetry: numeric(form.pulse_oximetry),
    }),
    a1_key_in: compact({
      waist_circumference: numeric(form.waist_circumference),
      hip_circumference: numeric(form.hip_circumference),
      alcohol_drinks_per_week: numeric(form.alcohol_drinks_per_week),
      apoe_e4: numeric(form.apoe_e4),
    }),
    laboratory_results: compact({
      fasting_glucose: numeric(form.fasting_glucose),
      hba1c: numeric(form.hba1c),
      total_cholesterol: numeric(form.total_cholesterol),
      hdl_cholesterol: numeric(form.hdl_cholesterol),
      ldl_cholesterol: numeric(form.ldl_cholesterol),
      triglycerides: numeric(form.triglycerides),
      creatinine: numeric(form.creatinine),
      urine_albumin_creatinine_ratio: numeric(form.urine_albumin_creatinine_ratio),
      platelet_count: numeric(form.platelet_count),
      alt_gpt: numeric(form.alt_gpt),
      ast_got: numeric(form.ast_got),
      ast_uln: numeric(form.ast_uln),
      ggt: numeric(form.ggt),
      albumin: numeric(form.albumin),
      insulin: numeric(form.insulin),
    }),
    hq: compact({
      family_history_diabetes: knownBoolean(form.family_history_diabetes),
      prediabetes: knownBoolean(form.prediabetes),
      dm_treated: knownBoolean(form.dm_treated),
      hypertension_treated: knownBoolean(form.hypertension_treated),
      lipid_lowering_treated: knownBoolean(form.lipid_lowering_treated),
      vegetables_daily: knownBoolean(form.vegetables_daily),
      physical_activity_active: knownBoolean(form.physical_activity_active),
      current_smoker: smokingFlag(form.smoking_status, 'current'),
      former_smoker: smokingFlag(form.smoking_status, 'former'),
      moderate_alcohol: smokingFlag(form.alcohol_use, 'moderate'),
      heavy_alcohol: smokingFlag(form.alcohol_use, 'heavy'),
      chd_history: knownBoolean(form.chd_history),
      cvd_history: knownBoolean(form.cvd_history),
      pvd_history: knownBoolean(form.pvd_history),
    }),
    assessments: compact({
      smoking_status: form.smoking_status,
      alcohol_use: form.alcohol_use,
      physical_activity: form.physical_activity,
      health_concerns: form.health_concerns,
    }),
    problems: compact({
      has_diabetes: knownBoolean(form.has_diabetes),
      has_hypertension: knownBoolean(form.has_hypertension),
      has_dyslipidemia: knownBoolean(form.has_dyslipidemia),
    }),
  });

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (saveLock.current) return;
    setMessage(null);

    if (!selectedPatient || !form.screening_date || loadingPatients) {
      setMessage({ type: 'error', text: '請選擇病患並填寫健檢日期' });
      return;
    }

    saveLock.current = true;
    const context = saveContext.current;
    setSaving(true);
    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.HEALTH_SCREENINGS, buildPayload());
      const data = await parseApiResponse(response);
      if (context !== saveContext.current) return;
      if (!response.ok) throw new Error(apiErrorMessage(data, '健檢資料儲存失敗'));

      setLastScreening({ ...data, patient: form.patient });
      setMessage({ type: 'success', text: '健檢資料已儲存' });
      setForm((current) => ({
        ...initialForm,
        patient: current.patient,
        screening_date: today(),
      }));
    } catch (error) {
      if (context === saveContext.current) setMessage({ type: 'error', text: error.message });
    } finally {
      if (context === saveContext.current) {
        saveLock.current = false;
        setSaving(false);
      }
    }
  };

  const renderNumberField = (field, label, suffix) => (
    <TextField
      key={field}
      label={label}
      type="number"
      inputProps={{ step: 'any', inputMode: 'decimal', 'aria-describedby': suffix ? 'intake-unit-' + field : undefined }}
      value={form[field]}
      onChange={(event) => updateField(field, event.target.value)}
      InputProps={suffix ? { endAdornment: <Typography id={'intake-unit-' + field} variant="caption">{suffix}</Typography> } : undefined}
      fullWidth
    />
  );

  return (
    <Box className="page-frame atlas-intake">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">健檢輸入</Typography>
          <Typography component="h1" variant="h4">新增健檢資料</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            記錄這一次的量測與檢驗，為下一次照護保留完整脈絡。
          </Typography>
        </Box>

      </Box>


      {patientLoadError && <Alert severity="error" sx={{ mb: 2 }} action={<Button disabled={loadingPatients} onClick={() => setPatientReload(value => value + 1)}>重試</Button>}>{patientLoadError}</Alert>}
      <nav className="intake-section-nav" aria-label="健檢表單分區"><a href="#intake-patient">01 病患資訊</a><a href="#intake-vitals">02 身體量測</a><a href="#intake-labs">03 檢驗數值</a><a href="#intake-history">04 問卷病史</a></nav>
      <Paper component="form" onSubmit={handleSubmit} className="work-panel" aria-label="新增健檢資料" aria-busy={saving}>
        <fieldset className="intake-fieldset" disabled={saving}>
        <legend className="intake-visually-hidden">新增健檢資料</legend>
        <Stack spacing={3}>
          <Box>
            <Typography component="h2" id="intake-patient" tabIndex={-1} variant="h6">01 / 病患與健檢資訊</Typography>
            <Typography variant="body2" color="text.secondary">確認病患身分，再開始記錄本次健檢。</Typography>
          </Box>

          {!requestedPatient && <TextField label="搜尋病患姓名或 MRN" value={patientSearch} onChange={event => { setPatientSearch(event.target.value); updateField('patient', ''); setPatients([]); }} size="small" fullWidth helperText="輸入姓名或病歷號碼，搜尋授權範圍內的病患。" />}
          <Typography variant="caption" role="status" color="text.secondary">{loadingPatients ? '正在讀取病患…' : patientLoadError ? '病患資料尚未載入' : patients.length ? selectedPatient ? '已選擇病患，請確認身分資訊' : '請選擇本次健檢的病患' : '目前沒有符合的病患'}</Typography>
          {selectedPatient && (
            <div className="intake-patient-identity" role="group" aria-label="本次健檢病患">
              <div className="intake-patient-name"><span className="atlas-eyebrow">本次健檢病患</span><strong>{selectedPatient.full_name || [selectedPatient.last_name, selectedPatient.first_name].filter(Boolean).join(' ') || '姓名未提供'}</strong></div>
              <dl><div><dt>MRN</dt><dd>{selectedPatient.medical_record_number || '未提供'}</dd></div><div><dt>年齡</dt><dd>{selectedPatient.age == null ? '未提供' : selectedPatient.age + ' 歲'}</dd></div></dl>
            </div>
          )}

          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '2fr 1fr 1fr' } }}>
            <FormControl fullWidth>
              <InputLabel id="patient-label">病患</InputLabel>
              <Select
                labelId="patient-label"
                inputProps={{ 'aria-describedby': !requestedPatient ? 'intake-patient-switch-note' : undefined }}
                label="病患"
                value={form.patient}
                onChange={(event) => updateField('patient', event.target.value)}
                disabled={loadingPatients || Boolean(patientLoadError) || Boolean(requestedPatient)}
              >
                {patients.map((patient) => (
                  <MenuItem key={patient.id} value={patient.id}>
                    {patient.full_name || [patient.last_name, patient.first_name].filter(Boolean).join(' ') || patient.id} ({patient.medical_record_number || patient.id})
                  </MenuItem>
                ))}
              </Select>
              {!requestedPatient && <Typography id="intake-patient-switch-note" variant="caption" color="text.secondary" sx={{ mt: 0.75 }}>切換病患會清除本次未儲存的資料。</Typography>}
            </FormControl>

            <TextField
              label="健檢日期"
              required
              type="date"
              value={form.screening_date}
              onChange={(event) => updateField('screening_date', event.target.value)}
              InputLabelProps={{ shrink: true }}
              fullWidth
            />

            <TextField
              label="就診類型"
              value={form.encounter_type === 'annual_physical' ? '年度健檢' : form.encounter_type}
              onChange={(event) => updateField('encounter_type', event.target.value === '年度健檢' ? 'annual_physical' : event.target.value)}
              fullWidth
            />
          </Box>

          <TextField label="地點" value={form.encounter_location} onChange={(event) => updateField('encounter_location', event.target.value)} fullWidth />


          <Divider />

          <Box>
            <Typography component="h2" id="intake-vitals" tabIndex={-1} variant="h6">02 / 身體量測</Typography>
            <Typography variant="body2" color="text.secondary">只填寫實際取得的量測值；空白欄位不會送出數值。</Typography>
          </Box>
          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' } }}>
            {vitalFields.map(([field, label, suffix]) => renderNumberField(field, label, suffix))}
          </Box>
          {bmi && <div className="intake-derived-measure"><span>BMI</span><output aria-label="計算 BMI">{bmi}</output><span className="intake-derived-note">由身高與體重計算</span></div>}

          <Divider />

          <Box>
            <Typography component="h2" id="intake-labs" tabIndex={-1} variant="h6">03 / 檢驗數值</Typography>
            <Typography variant="body2" color="text.secondary">依檢驗報告輸入數值，請確認單位一致。未取得的數值請留白。</Typography>
          </Box>
          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' } }}>
            {labFields.map(([field, label, suffix]) => renderNumberField(field, label, suffix))}
          </Box>

          <Divider />

          <Box>
            <Typography component="h2" id="intake-history" tabIndex={-1} variant="h6">04 / 問卷與病史</Typography>
            <Typography variant="body2" color="text.secondary">只記錄已確認的答案。未填寫的項目不會視為否。</Typography>
          </Box>

          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' } }}>
            <TextField select label="吸菸狀態" value={form.smoking_status} onChange={(event) => updateField('smoking_status', event.target.value)} fullWidth>
              <MenuItem value="">未填寫</MenuItem>
              <MenuItem value="never">從未吸菸</MenuItem>
              <MenuItem value="former">曾經吸菸</MenuItem>
              <MenuItem value="current">目前吸菸</MenuItem>
            </TextField>
            <TextField select label="飲酒狀態" value={form.alcohol_use} onChange={(event) => updateField('alcohol_use', event.target.value)} fullWidth>
              <MenuItem value="">未填寫</MenuItem>
              <MenuItem value="none">無</MenuItem>
              <MenuItem value="moderate">中度</MenuItem>
              <MenuItem value="heavy">重度</MenuItem>
            </TextField>
            <TextField select label="身體活動" value={form.physical_activity} onChange={(event) => updateField('physical_activity', event.target.value)} fullWidth>
              <MenuItem value="">未填寫</MenuItem>
              <MenuItem value="low">低</MenuItem>
              <MenuItem value="moderate">中</MenuItem>
              <MenuItem value="high">高</MenuItem>
            </TextField>
          </Box>

          <TextField label="健康關注事項" value={form.health_concerns} onChange={(event) => updateField('health_concerns', event.target.value)} multiline minRows={3} fullWidth />

          <div className="intake-question-grid">{questionnaireFields.map(([field, label]) => <TextField key={field} select label={label} value={form[field]} onChange={event => updateField(field, event.target.value)} fullWidth><MenuItem value="">未填寫</MenuItem><MenuItem value="yes">是</MenuItem><MenuItem value="no">否</MenuItem></TextField>)}</div>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} justifyContent="flex-end">
            <Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={saving || loadingPatients || !selectedPatient}>
              {saving ? '儲存中' : '儲存'}
            </Button>
          </Stack>
        </Stack>
        </fieldset>
        {message && <Alert ref={saveFeedback} tabIndex={-1} role={message.type === 'success' ? 'status' : 'alert'} severity={message.type} sx={{ mt: 3 }}>{message.text}</Alert>}
        {lastScreening?.id && (
          <Button component={RouterLink} to={'/risk-analysis?patient_id=' + encodeURIComponent(lastScreening.patient)} variant="outlined" startIcon={<AnalyticsIcon />} sx={{ mt: 2 }}>
            前往風險分析
          </Button>
        )}
      </Paper>
    </Box>
  );
}

export default HealthDataInput;
