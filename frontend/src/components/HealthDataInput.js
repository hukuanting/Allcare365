import React, { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Divider from '@mui/material/Divider';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
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

const today = () => new Date().toISOString().slice(0, 10);

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
  has_diabetes: false,
  has_hypertension: false,
  has_dyslipidemia: false,
  family_history_diabetes: false,
  prediabetes: false,
  dm_treated: false,
  hypertension_treated: false,
  lipid_lowering_treated: false,
  vegetables_daily: false,
  physical_activity_active: false,
  current_smoker: false,
  former_smoker: false,
  moderate_alcohol: false,
  heavy_alcohol: false,
  chd_history: false,
  cvd_history: false,
  pvd_history: false,
};

const numeric = (value) => {
  if (value === '' || value === null || value === undefined) return undefined;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? undefined : parsed;
};

const compact = (obj) => Object.fromEntries(
  Object.entries(obj).filter(([, value]) => value !== '' && value !== null && value !== undefined),
);

const vitalFields = [
  ['body_height', '身高', 'cm'],
  ['body_weight', '體重', 'kg'],
  ['waist_circumference', '腰圍', 'cm'],
  ['hip_circumference', '臀圍', 'cm'],
  ['systolic_blood_pressure', 'SBP', 'mmHg'],
  ['diastolic_blood_pressure', 'DBP', 'mmHg'],
  ['heart_rate', '心率', 'bpm'],
  ['respiratory_rate', '呼吸速率', '/min'],
  ['body_temperature', '體溫', 'C'],
  ['pulse_oximetry', 'SpO2', '%'],
];

const labFields = [
  ['fasting_glucose', 'FPG', 'mg/dL'],
  ['hba1c', 'HbA1c', '%'],
  ['total_cholesterol', 'TC', 'mg/dL'],
  ['hdl_cholesterol', 'HDL', 'mg/dL'],
  ['ldl_cholesterol', 'LDL', 'mg/dL'],
  ['triglycerides', 'TG', 'mg/dL'],
  ['creatinine', 'Creatinine', 'mg/dL'],
  ['urine_albumin_creatinine_ratio', 'UACR', 'mg/g'],
  ['platelet_count', 'Platelet count', '10*3/uL'],
  ['alt_gpt', 'ALT', 'U/L'],
  ['ast_got', 'AST', 'U/L'],
  ['ast_uln', 'AST ULN', 'U/L'],
  ['ggt', 'GGT', 'U/L'],
  ['albumin', 'Albumin', 'g/dL'],
  ['insulin', 'Insulin', 'uIU/mL'],
  ['alcohol_drinks_per_week', '每週酒精量', 'drinks'],
  ['apoe_e4', 'APOE e4', 'count'],
];

function HealthDataInput() {
  const [form, setForm] = useState(initialForm);
  const [patients, setPatients] = useState([]);
  const [loadingPatients, setLoadingPatients] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [lastScreening, setLastScreening] = useState(null);

  useEffect(() => {
    const fetchPatients = async () => {
      setLoadingPatients(true);
      try {
        const response = await api.get(API_CONFIG.ENDPOINTS.PATIENTS);
        const data = await parseApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(data, '病患清單讀取失敗'));
        setPatients(listFromResponse(data));
      } catch (error) {
        setMessage({ type: 'error', text: error.message });
      } finally {
        setLoadingPatients(false);
      }
    };
    fetchPatients();
  }, []);

  const selectedPatient = patients.find((patient) => String(patient.id) === String(form.patient));

  const bmi = useMemo(() => {
    const height = numeric(form.body_height);
    const weight = numeric(form.body_weight);
    if (!height || !weight) return null;
    return (weight / ((height / 100) ** 2)).toFixed(1);
  }, [form.body_height, form.body_weight]);

  const updateField = (field, value) => {
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
    hq: {
      family_history_diabetes: form.family_history_diabetes,
      prediabetes: form.prediabetes,
      dm_treated: form.dm_treated,
      hypertension_treated: form.hypertension_treated,
      lipid_lowering_treated: form.lipid_lowering_treated,
      vegetables_daily: form.vegetables_daily,
      physical_activity_active: form.physical_activity_active,
      current_smoker: form.current_smoker || form.smoking_status === 'current',
      former_smoker: form.former_smoker || form.smoking_status === 'former',
      moderate_alcohol: form.moderate_alcohol || form.alcohol_use === 'moderate',
      heavy_alcohol: form.heavy_alcohol || form.alcohol_use === 'heavy',
      chd_history: form.chd_history,
      cvd_history: form.cvd_history,
      pvd_history: form.pvd_history,
    },
    assessments: compact({
      smoking_status: form.smoking_status,
      alcohol_use: form.alcohol_use,
      physical_activity: form.physical_activity,
      health_concerns: form.health_concerns,
    }),
    problems: {
      has_diabetes: form.has_diabetes,
      has_hypertension: form.has_hypertension,
      has_dyslipidemia: form.has_dyslipidemia,
    },
  });

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage(null);

    if (!form.patient || !form.screening_date) {
      setMessage({ type: 'error', text: '請選擇病患並填寫健檢日期' });
      return;
    }

    setSaving(true);
    try {
      const response = await api.post(API_CONFIG.ENDPOINTS.HEALTH_SCREENINGS, buildPayload());
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, '健檢資料儲存失敗'));

      setLastScreening(data);
      setMessage({ type: 'success', text: '健檢資料已儲存' });
      setForm((current) => ({
        ...initialForm,
        patient: current.patient,
        screening_date: today(),
      }));
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setSaving(false);
    }
  };

  const renderNumberField = (field, label, suffix) => (
    <TextField
      label={label}
      type="number"
      value={form[field]}
      onChange={(event) => updateField(field, event.target.value)}
      InputProps={suffix ? { endAdornment: <Typography variant="caption">{suffix}</Typography> } : undefined}
      fullWidth
    />
  );

  return (
    <Box className="page-frame">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">健檢輸入</Typography>
          <Typography variant="h4">新增健檢資料</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            將臨床量測、檢驗與問卷資料送到後端，作為風險分析與研究 cohort 的來源。
          </Typography>
        </Box>
        {lastScreening?.id && (
          <Button component={RouterLink} to="/risk-analysis" variant="outlined" startIcon={<AnalyticsIcon />}>
            前往風險分析
          </Button>
        )}
      </Box>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Paper component="form" onSubmit={handleSubmit} className="work-panel">
        <Stack spacing={3}>
          <Box>
            <Typography variant="h6">病患與健檢資訊</Typography>
            <Typography variant="body2" color="text.secondary">先選擇後端已有的病患，再輸入本次健檢資料。</Typography>
          </Box>

          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '2fr 1fr 1fr' } }}>
            <FormControl fullWidth>
              <InputLabel id="patient-label">病患</InputLabel>
              <Select
                labelId="patient-label"
                label="病患"
                value={form.patient}
                onChange={(event) => updateField('patient', event.target.value)}
                disabled={loadingPatients}
              >
                {patients.map((patient) => (
                  <MenuItem key={patient.id} value={patient.id}>
                    {[patient.first_name, patient.last_name].filter(Boolean).join(' ') || patient.full_name || patient.id} ({patient.medical_record_number || patient.id})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="健檢日期"
              type="date"
              value={form.screening_date}
              onChange={(event) => updateField('screening_date', event.target.value)}
              InputLabelProps={{ shrink: true }}
              fullWidth
            />

            <TextField
              label="Encounter type"
              value={form.encounter_type}
              onChange={(event) => updateField('encounter_type', event.target.value)}
              fullWidth
            />
          </Box>

          <TextField label="地點" value={form.encounter_location} onChange={(event) => updateField('encounter_location', event.target.value)} fullWidth />

          {selectedPatient && (
            <Alert severity="info" variant="outlined">
              {[selectedPatient.first_name, selectedPatient.last_name].filter(Boolean).join(' ') || selectedPatient.full_name}，MRN {selectedPatient.medical_record_number || '無資料'}，{selectedPatient.age ?? '無資料'} 歲
            </Alert>
          )}

          <Divider />

          <Box>
            <Typography variant="h6">Vital signs</Typography>
            <Typography variant="body2" color="text.secondary">只填寫實際取得的量測值；空白欄位不會送出數值。</Typography>
          </Box>
          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' } }}>
            {vitalFields.map(([field, label, suffix]) => renderNumberField(field, label, suffix))}
          </Box>
          {bmi && <Alert severity="success" variant="outlined">BMI {bmi}</Alert>}

          <Divider />

          <Box>
            <Typography variant="h6">Laboratory results</Typography>
            <Typography variant="body2" color="text.secondary">輸入實際檢驗數值，後端會保留來源資料供後續推導。</Typography>
          </Box>
          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' } }}>
            {labFields.map(([field, label, suffix]) => renderNumberField(field, label, suffix))}
          </Box>

          <Divider />

          <Box>
            <Typography variant="h6">問卷與病史</Typography>
            <Typography variant="body2" color="text.secondary">下列欄位會寫入後端問卷與問題清單結構。</Typography>
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

          <Box sx={{ display: 'grid', gap: 1, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' } }}>
            <FormControlLabel control={<Checkbox checked={form.family_history_diabetes} onChange={(event) => updateField('family_history_diabetes', event.target.checked)} />} label="糖尿病家族史" />
            <FormControlLabel control={<Checkbox checked={form.prediabetes} onChange={(event) => updateField('prediabetes', event.target.checked)} />} label="Prediabetes" />
            <FormControlLabel control={<Checkbox checked={form.dm_treated} onChange={(event) => updateField('dm_treated', event.target.checked)} />} label="糖尿病治療中" />
            <FormControlLabel control={<Checkbox checked={form.hypertension_treated} onChange={(event) => updateField('hypertension_treated', event.target.checked)} />} label="高血壓治療中" />
            <FormControlLabel control={<Checkbox checked={form.lipid_lowering_treated} onChange={(event) => updateField('lipid_lowering_treated', event.target.checked)} />} label="降血脂治療中" />
            <FormControlLabel control={<Checkbox checked={form.vegetables_daily} onChange={(event) => updateField('vegetables_daily', event.target.checked)} />} label="每日蔬菜" />
            <FormControlLabel control={<Checkbox checked={form.physical_activity_active} onChange={(event) => updateField('physical_activity_active', event.target.checked)} />} label="規律活動" />
            <FormControlLabel control={<Checkbox checked={form.current_smoker} onChange={(event) => updateField('current_smoker', event.target.checked)} />} label="目前吸菸" />
            <FormControlLabel control={<Checkbox checked={form.former_smoker} onChange={(event) => updateField('former_smoker', event.target.checked)} />} label="曾經吸菸" />
            <FormControlLabel control={<Checkbox checked={form.moderate_alcohol} onChange={(event) => updateField('moderate_alcohol', event.target.checked)} />} label="中度飲酒" />
            <FormControlLabel control={<Checkbox checked={form.heavy_alcohol} onChange={(event) => updateField('heavy_alcohol', event.target.checked)} />} label="重度飲酒" />
            <FormControlLabel control={<Checkbox checked={form.chd_history} onChange={(event) => updateField('chd_history', event.target.checked)} />} label="CHD history" />
            <FormControlLabel control={<Checkbox checked={form.cvd_history} onChange={(event) => updateField('cvd_history', event.target.checked)} />} label="CVD history" />
            <FormControlLabel control={<Checkbox checked={form.pvd_history} onChange={(event) => updateField('pvd_history', event.target.checked)} />} label="PVD history" />
          </Box>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <FormControlLabel control={<Checkbox checked={form.has_diabetes} onChange={(event) => updateField('has_diabetes', event.target.checked)} />} label="糖尿病" />
            <FormControlLabel control={<Checkbox checked={form.has_hypertension} onChange={(event) => updateField('has_hypertension', event.target.checked)} />} label="高血壓" />
            <FormControlLabel control={<Checkbox checked={form.has_dyslipidemia} onChange={(event) => updateField('has_dyslipidemia', event.target.checked)} />} label="血脂異常" />
          </Stack>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} justifyContent="flex-end">
            <Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={saving}>
              {saving ? '儲存中' : '儲存'}
            </Button>
          </Stack>
        </Stack>
      </Paper>
    </Box>
  );
}

export default HealthDataInput;
