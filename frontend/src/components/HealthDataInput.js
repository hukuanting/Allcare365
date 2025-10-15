import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './HealthDataInput.css';
import './HealthDataInputSurvey.css';

const initialFormData = {
  // 基本資訊
  patient_id: '',
  screening_date: new Date().toISOString().split('T')[0],
  screening_type: 'annual_physical',
  
  // 基本人口統計學資料
  age: '',
  sex: '',
  height_cm: '',
  weight_kg: '',
  
  // 身體測量
  neck_circumference: '',
  chest_circumference: '',
  waist_circumference: '',
  hip_circumference: '',
  
  // 血液檢查 - 血球計數
  rbc_count: '',
  rdw_cv_percent: '',
  wbc_count: '',
  platelet_count: '',
  monocyte_percent: '',
  
  // 血糖代謝
  fasting_glucose: '',
  ifg: false,
  hba1c: '',
  insulin: '',
  
  // 生命徵象
  pulse_rate: '',
  systolic_bp: '',
  diastolic_bp: '',
  
  // 腎功能
  serum_creatinine: '',
  
  // 血脂
  triglycerides: '',
  total_cholesterol: '',
  hdl_cholesterol: '',
  ldl_cholesterol: '',
  
  // 其他生化指標
  uric_acid: '',
  homocysteine: '',
  hs_crp: '',
  
  // 肝功能
  alt_gpt: '',
  ast_got: '',
  ast_uln: '',
  ggt: '',
  total_protein: '',
  albumin: '',
  
  // 尿液檢查
  urine_albumin: '',
  urine_creatinine: '',
  urine_albumin_creatinine_ratio: '',
  
  // 基因檢測
  apoe_e4: false,
  
  // 病史和生活方式
  diabetes: false,
  hypertension: false,
  smoking_status: 'never',
  alcohol_consumption: 'moderate',
  physical_activity: 'moderate',
  family_history_cvd: false,
  current_medications: '',
  allergies: '',
  
  // 詳細飲食習慣
  daily_vegetables_fruits: '',
  
  // 詳細運動習慣
  exercise_frequency: '',
  exercise_intensity: '',
  exercise_duration: '',
  
  // 詳細抽菸習慣
  smoking_history: 'never',
  cigarettes_per_day: '',
  smoking_years: '',
  quit_smoking_years: '',
  
  // 詳細飲酒習慣
  alcohol_frequency: 'never',
  alcohol_type: '',
  drinks_per_week: '',
  
  // 家族病史
  family_diabetes: false,
  family_heart_disease: false,
  family_hypertension: false,
  family_hyperlipidemia: false,
  family_stroke: false,
  family_cancer: false,
  family_other_diseases: '',
  
  // 個人病史
  personal_diabetes: false,
  personal_diabetes_type: '',
  personal_diabetes_years: '',
  personal_heart_disease: false,
  personal_heart_disease_type: '',
  personal_hypertension: false,
  personal_hypertension_years: '',
  personal_hyperlipidemia: false,
  personal_hyperlipidemia_years: '',
  personal_stroke: false,
  personal_other_diseases: '',
};

function HealthDataInput() {
  const [formData, setFormData] = useState(initialFormData);
  
  const [patients, setPatients] = useState([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [calculatedBMI, setCalculatedBMI] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});

  useEffect(() => {
    fetchPatients();
  }, []);

  useEffect(() => {
    // 自動計算BMI
    if (formData.height_cm && formData.weight_kg) {
      const height_m = parseFloat(formData.height_cm) / 100;
      const weight = parseFloat(formData.weight_kg);
      if (height_m > 0 && weight > 0) {
        const bmi = weight / (height_m * height_m);
        setCalculatedBMI(bmi.toFixed(1));
      }
    } else {
      setCalculatedBMI(null);
    }
  }, [formData.height_cm, formData.weight_kg]);

  const fetchPatients = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8000/api/patients/', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setPatients(data.results || data);
      }
    } catch (error) {
      console.error('Failed to fetch patients:', error);
    }
  };

  const validateForm = () => {
    const errors = {};
    
    if (!formData.patient_id) {
      errors.patient_id = '請選擇患者';
    }
    
    if (!formData.screening_date) {
      errors.screening_date = '請選擇檢查日期';
    }
    
    // 基本生命徵象驗證
    if (formData.height_cm && (formData.height_cm < 50 || formData.height_cm > 250)) {
      errors.height_cm = '身高應在50-250cm之間';
    }
    
    if (formData.weight_kg && (formData.weight_kg < 20 || formData.weight_kg > 300)) {
      errors.weight_kg = '體重應在20-300kg之間';
    }
    
    if (formData.systolic_bp && (formData.systolic_bp < 70 || formData.systolic_bp > 250)) {
      errors.systolic_bp = '收縮壓應在70-250mmHg之間';
    }
    
    if (formData.diastolic_bp && (formData.diastolic_bp < 40 || formData.diastolic_bp > 150)) {
      errors.diastolic_bp = '舒張壓應在40-150mmHg之間';
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({ 
      ...formData, 
      [name]: type === 'checkbox' ? checked : value 
    });
    
    // 當選擇患者時，自動計算年齡
    if (name === 'patient_id' && value) {
      const selectedPatient = patients.find(patient => patient.id === value);
      if (selectedPatient && selectedPatient.date_of_birth) {
        const birthDate = new Date(selectedPatient.date_of_birth);
        const today = new Date();
        let age = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();
        
        // 如果還沒到生日，年齡減1
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
          age--;
        }
        
        setFormData(prevData => ({
          ...prevData,
          [name]: type === 'checkbox' ? checked : value,
          age: age.toString()
        }));
      }
    }
    
    // 清除相關的驗證錯誤
    if (validationErrors[name]) {
      setValidationErrors({
        ...validationErrors,
        [name]: undefined
      });
    }
  };

      const handleSubmit = async (e) => {
        e.preventDefault();
    
    if (!validateForm()) {
      setMessage('請修正表單錯誤後再提交');
      return;
    }
    
    setLoading(true);
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      setMessage('請先登入系統');
      setLoading(false);
      return;
    }

    try {
      // 準備提交數據 - 按照後端API期望的格式重構
      const submitData = {
        // 基本信息
        patient: formData.patient_id, // 患者ID是UUID字符串，不需要轉換為數字
        screening_date: formData.screening_date,
        screening_type: formData.screening_type || 'annual_physical', // 提供默認值
        notes: formData.notes || '', // 提供默認值
      };

      // 驗證必需字段
      if (!submitData.patient) {
        setMessage('請選擇有效的患者');
        setLoading(false);
        return;
      }

      if (!submitData.screening_date) {
        setMessage('請選擇檢查日期');
        setLoading(false);
        return;
      }

      // 生命徵象數據
      const vitalSignsData = {};
      if (formData.height_cm) vitalSignsData.height_cm = parseFloat(formData.height_cm);
      if (formData.weight_kg) vitalSignsData.weight_kg = parseFloat(formData.weight_kg);
      if (formData.neck_circumference) vitalSignsData.neck_circumference_cm = parseFloat(formData.neck_circumference);
      if (formData.chest_circumference) vitalSignsData.chest_circumference_cm = parseFloat(formData.chest_circumference);
      if (formData.waist_circumference) vitalSignsData.waist_circumference_cm = parseFloat(formData.waist_circumference);
      if (formData.hip_circumference) vitalSignsData.hip_circumference_cm = parseFloat(formData.hip_circumference);
      if (formData.pulse_rate) vitalSignsData.pulse_rate_bpm = parseInt(formData.pulse_rate);
      if (formData.systolic_bp) vitalSignsData.systolic_bp_mmhg = parseInt(formData.systolic_bp);
      if (formData.diastolic_bp) vitalSignsData.diastolic_bp_mmhg = parseInt(formData.diastolic_bp);
      
      if (Object.keys(vitalSignsData).length > 0) {
        submitData.vital_signs = vitalSignsData;
      }

      // 實驗室結果數據
      const laboratoryData = {};
      // 血球計數
      if (formData.rbc_count) laboratoryData.rbc_count = parseFloat(formData.rbc_count);
      if (formData.rdw_cv_percent) laboratoryData.rdw_cv_percent = parseFloat(formData.rdw_cv_percent);
      if (formData.wbc_count) laboratoryData.wbc_count = parseFloat(formData.wbc_count);
      if (formData.platelet_count) laboratoryData.platelet_count = parseInt(formData.platelet_count);
      if (formData.monocyte_percent) laboratoryData.monocyte_percent = parseFloat(formData.monocyte_percent);
      
      // 血糖代謝
      if (formData.fasting_glucose) laboratoryData.fasting_glucose_mgdl = parseFloat(formData.fasting_glucose);
      if (formData.ifg !== undefined) laboratoryData.impaired_fasting_glucose = formData.ifg;
      if (formData.hba1c) laboratoryData.hba1c_percent = parseFloat(formData.hba1c);
      if (formData.insulin) laboratoryData.insulin_uiu_ml = parseFloat(formData.insulin);
      
      // 腎功能
      if (formData.serum_creatinine) laboratoryData.serum_creatinine_mgdl = parseFloat(formData.serum_creatinine);
      
      // 血脂
      if (formData.triglycerides) laboratoryData.triglycerides_mgdl = parseFloat(formData.triglycerides);
      if (formData.total_cholesterol) laboratoryData.total_cholesterol_mgdl = parseFloat(formData.total_cholesterol);
      if (formData.hdl_cholesterol) laboratoryData.hdl_cholesterol_mgdl = parseFloat(formData.hdl_cholesterol);
      if (formData.ldl_cholesterol) laboratoryData.ldl_cholesterol_mgdl = parseFloat(formData.ldl_cholesterol);
      
      // 其他生化指標
      if (formData.uric_acid) laboratoryData.uric_acid_mgdl = parseFloat(formData.uric_acid);
      if (formData.homocysteine) laboratoryData.homocysteine_umol_l = parseFloat(formData.homocysteine);
      if (formData.hs_crp) laboratoryData.hs_crp_mgdl = parseFloat(formData.hs_crp);
      
      // 肝功能
      if (formData.alt_gpt) laboratoryData.alt_gpt_ul = parseFloat(formData.alt_gpt);
      if (formData.ast_got) laboratoryData.ast_got_ul = parseFloat(formData.ast_got);
      if (formData.ast_uln) laboratoryData.ast_uln_ratio = parseFloat(formData.ast_uln);
      if (formData.ggt) laboratoryData.ggt_ul = parseFloat(formData.ggt);
      if (formData.total_protein) laboratoryData.total_protein_gdl = parseFloat(formData.total_protein);
      if (formData.albumin) laboratoryData.albumin_gdl = parseFloat(formData.albumin);
      
      // 尿液檢查
      if (formData.urine_albumin) laboratoryData.urine_albumin_mgdl = parseFloat(formData.urine_albumin);
      if (formData.urine_creatinine) laboratoryData.urine_creatinine_mgdl = parseFloat(formData.urine_creatinine);
      if (formData.urine_albumin_creatinine_ratio) laboratoryData.urine_albumin_creatinine_ratio = parseFloat(formData.urine_albumin_creatinine_ratio);
      
      if (Object.keys(laboratoryData).length > 0) {
        submitData.laboratory_results = laboratoryData;
      }

      // 病史數據
      const medicalHistoryData = {};
      if (formData.apoe_e4 !== undefined) medicalHistoryData.apoe_e4_positive = formData.apoe_e4;
      
      if (Object.keys(medicalHistoryData).length > 0) {
        submitData.medical_history = medicalHistoryData;
      }

      // 生活方式數據 - 包含詳細問卷資料
      const lifestyleData = {};
      
      // 飲食習慣
      if (formData.daily_vegetables_fruits) {
        lifestyleData.diet_score = formData.daily_vegetables_fruits;
      }
      
      // 運動習慣
      if (formData.exercise_frequency) {
        lifestyleData.exercise_score = formData.exercise_frequency;
      }
      
      // NEW: 詳細運動習慣
      if (formData.exercise_intensity) {
        lifestyleData.exercise_intensity = formData.exercise_intensity;
      }
      if (formData.exercise_duration) {
        lifestyleData.exercise_duration = formData.exercise_duration;
      }
      
      // 抽菸習慣 - 確保布爾值正確設置
      lifestyleData.is_current_smoker = formData.smoking_history === 'current';
      lifestyleData.is_former_smoker = formData.smoking_history === 'former';
      
      if (formData.cigarettes_per_day) {
        lifestyleData.cigarettes_per_day = parseInt(formData.cigarettes_per_day);
      }
      
      if (formData.smoking_years) {
        lifestyleData.smoking_years = parseInt(formData.smoking_years);
      }
      
      // 飲酒習慣
      if (formData.alcohol_frequency) {
        lifestyleData.drinking_status = formData.alcohol_frequency;
      }
      
      if (formData.drinks_per_week) {
        lifestyleData.drinks_per_week = parseInt(formData.drinks_per_week);
      }
      
      // NEW: 飲酒類型
      if (formData.alcohol_type) {
        lifestyleData.alcohol_type = formData.alcohol_type;
      }
      
      // 家族病史 - 確保布爾值正確轉換
      if (formData.family_diabetes !== undefined && formData.family_diabetes !== '') {
        lifestyleData.family_diabetes = Boolean(formData.family_diabetes);
      }
      if (formData.family_heart_disease !== undefined && formData.family_heart_disease !== '') {
        lifestyleData.family_heart_disease = Boolean(formData.family_heart_disease);
      }
      if (formData.family_hypertension !== undefined && formData.family_hypertension !== '') {
        lifestyleData.family_hypertension = Boolean(formData.family_hypertension);
      }
      if (formData.family_cancer !== undefined && formData.family_cancer !== '') {
        lifestyleData.family_cancer = Boolean(formData.family_cancer);
      }
      
      // NEW: 新增家族病史欄位
      if (formData.family_hyperlipidemia !== undefined && formData.family_hyperlipidemia !== '') {
        lifestyleData.family_hyperlipidemia = Boolean(formData.family_hyperlipidemia);
      }
      if (formData.family_stroke !== undefined && formData.family_stroke !== '') {
        lifestyleData.family_stroke = Boolean(formData.family_stroke);
      }
      if (formData.family_other_diseases) {
        lifestyleData.family_other_diseases = formData.family_other_diseases;
      }
      
      // 個人病史 - 確保布爾值正確轉換
      if (formData.personal_diabetes !== undefined && formData.personal_diabetes !== '') {
        lifestyleData.has_diabetes = Boolean(formData.personal_diabetes);
      }
      if (formData.personal_heart_disease !== undefined && formData.personal_heart_disease !== '') {
        lifestyleData.has_coronary_heart_disease = Boolean(formData.personal_heart_disease);
      }
      if (formData.personal_hypertension !== undefined && formData.personal_hypertension !== '') {
        lifestyleData.has_hypertension = Boolean(formData.personal_hypertension);
      }
      if (formData.personal_hyperlipidemia !== undefined && formData.personal_hyperlipidemia !== '') {
        lifestyleData.has_dyslipidemia = Boolean(formData.personal_hyperlipidemia);
      }
      
      // NEW: 詳細個人病史
      if (formData.personal_diabetes_type) {
        lifestyleData.personal_diabetes_type = formData.personal_diabetes_type;
      }
      if (formData.personal_diabetes_years) {
        lifestyleData.personal_diabetes_years = parseFloat(formData.personal_diabetes_years);
      }
      if (formData.personal_heart_disease_type) {
        lifestyleData.personal_heart_disease_type = formData.personal_heart_disease_type;
      }
      if (formData.personal_hypertension_years) {
        lifestyleData.personal_hypertension_years = parseFloat(formData.personal_hypertension_years);
      }
      if (formData.personal_hyperlipidemia_years) {
        lifestyleData.personal_hyperlipidemia_years = parseFloat(formData.personal_hyperlipidemia_years);
      }
      if (formData.personal_stroke !== undefined && formData.personal_stroke !== '') {
        lifestyleData.personal_stroke = Boolean(formData.personal_stroke);
      }
      if (formData.personal_other_diseases) {
        lifestyleData.personal_other_diseases = formData.personal_other_diseases;
      }
      
      // NEW: 用藥和過敏史
      if (formData.current_medications) {
        lifestyleData.current_medications = formData.current_medications;
      }
      if (formData.allergies) {
        lifestyleData.allergies = formData.allergies;
      }
      
      if (Object.keys(lifestyleData).length > 0) {
        submitData.lifestyle = lifestyleData;
      }

      // 調試信息
      console.log('提交的數據:', JSON.stringify(submitData, null, 2));

      const response = await fetch('http://localhost:8000/api/health-screening/screenings/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(submitData),
      });

      if (response.ok) {
        setMessage('健康檢查數據提交成功！');
        // 重置表單
        setFormData(initialFormData);
        setCalculatedBMI(null);
      } else {
        const errorText = await response.text();
        try {
          const errorData = JSON.parse(errorText);
          console.error('API錯誤響應:', errorData);
          
          // 處理不同類型的錯誤響應
          if (errorData.detail) {
            setMessage(`提交失敗: ${errorData.detail}`);
          } else if (errorData.patient && Array.isArray(errorData.patient)) {
            setMessage(`提交失敗: 患者字段錯誤 - ${errorData.patient.join(', ')}`);
          } else if (errorData.lifestyle && typeof errorData.lifestyle === 'object') {
            // 處理lifestyle字段的錯誤
            const lifestyleErrors = [];
            Object.entries(errorData.lifestyle).forEach(([key, value]) => {
              const errorString = Array.isArray(value) ? value.join(', ') : String(value);
              lifestyleErrors.push(`${key}: ${errorString}`);
            });
            setMessage(`提交失敗: 生活方式數據錯誤 - ${lifestyleErrors.join('; ')}`);
          } else if (typeof errorData === 'object') {
            // 處理嵌套的錯誤信息
            const errorMessages = [];
            
            // 處理頂層錯誤
            Object.entries(errorData).forEach(([field, errors]) => {
              if (typeof errors === 'string') {
                errorMessages.push(`${field}: ${errors}`);
              } else if (Array.isArray(errors)) {
                errorMessages.push(`${field}: ${errors.join(', ')}`);
              } else if (typeof errors === 'object') {
                // 處理嵌套對象中的錯誤
                Object.entries(errors).forEach(([nestedField, nestedErrors]) => {
                  if (Array.isArray(nestedErrors)) {
                    errorMessages.push(`${field}.${nestedField}: ${nestedErrors.join(', ')}`);
                  } else {
                    errorMessages.push(`${field}.${nestedField}: ${nestedErrors}`);
                  }
                });
              }
            });
            
            setMessage(`提交失敗: ${errorMessages.join('; ')}`);
          } else {
            setMessage(`提交失敗: 未知錯誤`);
          }
        } catch (parseError) {
          console.error('解析JSON響應失敗:', parseError);
          console.error('收到的原始響應文本:', errorText);
          setMessage(`提交失敗: 伺服器返回了無效的響應格式 (${response.status})`);
        }
      }
    } catch (error) {
      setMessage(`網路錯誤: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="health-data-input">
      <h2>Health Data Input - 健康檢查資料輸入</h2>
      
      {message && (
        <div className={`message ${message.includes('成功') ? 'success' : 'error'}`}>
          {message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="health-form">
        {/* 基本資訊區 */}
        <div className="form-section">
          <h3>基本資訊</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="patient_id">患者 *</label>
              <select
                id="patient_id"
                name="patient_id"
                value={formData.patient_id}
                onChange={handleChange}
                className={validationErrors.patient_id ? 'error' : ''}
                required
              >
                <option value="">請選擇患者</option>
                {patients.map(patient => (
                  <option key={patient.id} value={patient.id}>
                    {patient.first_name} {patient.last_name} ({patient.patient_id})
                  </option>
                ))}
              </select>
              {validationErrors.patient_id && (
                <span className="error-text">{validationErrors.patient_id}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="screening_date">檢查日期 *</label>
              <input
                type="date"
                id="screening_date"
                name="screening_date"
                value={formData.screening_date}
                onChange={handleChange}
                className={validationErrors.screening_date ? 'error' : ''}
                required
              />
              {validationErrors.screening_date && (
                <span className="error-text">{validationErrors.screening_date}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="screening_type">檢查類型</label>
              <select
                id="screening_type"
                name="screening_type"
                value={formData.screening_type}
                onChange={handleChange}
              >
                <option value="annual_physical">年度健檢</option>
                <option value="preventive_care">預防保健</option>
                <option value="follow_up">追蹤檢查</option>
                <option value="emergency">急診檢查</option>
                <option value="occupational">職業健檢</option>
              </select>
            </div>
          </div>
        </div>

        {/* 基本人口統計學資料 */}
        <div className="form-section">
          <h3>基本人口統計學資料</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="age">年齡 (自動計算)</label>
              <input
                type="number"
                id="age"
                name="age"
                value={formData.age}
                onChange={handleChange}
                placeholder="請先選擇患者"
                min="0"
                max="120"
                readOnly
                className="calculated-field"
              />
              {formData.age && (
                <small className="help-text">
                  根據患者生日自動計算
                </small>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="sex">性別</label>
              <select
                id="sex"
                name="sex"
                value={formData.sex}
                onChange={handleChange}
              >
                <option value="">請選擇</option>
                <option value="M">男性</option>
                <option value="F">女性</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="height_cm">身高 Height (cm)</label>
              <input
                type="number"
                id="height_cm"
                name="height_cm"
                value={formData.height_cm}
                onChange={handleChange}
                placeholder="例: 170"
                min="50"
                max="250"
                step="0.1"
                className={validationErrors.height_cm ? 'error' : ''}
              />
              {validationErrors.height_cm && (
                <span className="error-text">{validationErrors.height_cm}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="weight_kg">體重 Weight (kg)</label>
              <input
                type="number"
                id="weight_kg"
                name="weight_kg"
                value={formData.weight_kg}
                onChange={handleChange}
                placeholder="例: 70"
                min="20"
                max="300"
                step="0.1"
                className={validationErrors.weight_kg ? 'error' : ''}
              />
              {validationErrors.weight_kg && (
                <span className="error-text">{validationErrors.weight_kg}</span>
              )}
            </div>

            {calculatedBMI && (
              <div className="form-group">
                <label>BMI (自動計算)</label>
                <div className="calculated-value">
                  {calculatedBMI} 
                  <span className={`bmi-category ${
                    calculatedBMI < 18.5 ? 'underweight' :
                    calculatedBMI < 24 ? 'normal' :
                    calculatedBMI < 27 ? 'overweight' : 'obese'
                  }`}>
                    {calculatedBMI < 18.5 ? '體重過輕' :
                     calculatedBMI < 24 ? '正常' :
                     calculatedBMI < 27 ? '過重' : '肥胖'}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 身體測量 */}
        <div className="form-section">
          <h3>身體測量</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="neck_circumference">頸圍 Neck C (cm)</label>
              <input
                type="number"
                id="neck_circumference"
                name="neck_circumference"
                value={formData.neck_circumference}
                onChange={handleChange}
                placeholder="例: 35"
                min="20"
                max="60"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="chest_circumference">胸圍 Chest C (cm)</label>
              <input
                type="number"
                id="chest_circumference"
                name="chest_circumference"
                value={formData.chest_circumference}
                onChange={handleChange}
                placeholder="例: 95"
                min="50"
                max="150"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="waist_circumference">腰圍 Waist (cm)</label>
              <input
                type="number"
                id="waist_circumference"
                name="waist_circumference"
                value={formData.waist_circumference}
                onChange={handleChange}
                placeholder="例: 85"
                min="50"
                max="150"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="hip_circumference">臀圍 (cm)</label>
              <input
                type="number"
                id="hip_circumference"
                name="hip_circumference"
                value={formData.hip_circumference}
                onChange={handleChange}
                placeholder="例: 95"
                min="50"
                max="150"
                step="0.1"
              />
            </div>
          </div>
        </div>

        {/* 血液檢查 - 血球計數 */}
        <div className="form-section">
          <h3>血液檢查 - 血球計數</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="rbc_count">RBC (10^6/μL)</label>
              <input
                type="number"
                id="rbc_count"
                name="rbc_count"
                value={formData.rbc_count}
                onChange={handleChange}
                placeholder="例: 4.5"
                min="2"
                max="7"
                step="0.01"
              />
            </div>

            <div className="form-group">
              <label htmlFor="rdw_cv_percent">RDW-CV%</label>
              <input
                type="number"
                id="rdw_cv_percent"
                name="rdw_cv_percent"
                value={formData.rdw_cv_percent}
                onChange={handleChange}
                placeholder="例: 13.5"
                min="10"
                max="20"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="wbc_count">WBC 10(3) ul</label>
              <input
                type="number"
                id="wbc_count"
                name="wbc_count"
                value={formData.wbc_count}
                onChange={handleChange}
                placeholder="例: 7.5"
                min="2"
                max="20"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="platelet_count">Platelet (10^3/μL)</label>
              <input
                type="number"
                id="platelet_count"
                name="platelet_count"
                value={formData.platelet_count}
                onChange={handleChange}
                placeholder="例: 250"
                min="50"
                max="800"
              />
            </div>

            <div className="form-group">
              <label htmlFor="monocyte_percent">Monocyte%</label>
              <input
                type="number"
                id="monocyte_percent"
                name="monocyte_percent"
                value={formData.monocyte_percent}
                onChange={handleChange}
                placeholder="例: 6.5"
                min="0"
                max="20"
                step="0.1"
              />
            </div>
          </div>
        </div>

        {/* 血糖代謝 */}
        <div className="form-section">
          <h3>血糖代謝</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="fasting_glucose">空腹血糖 (mg/dL)</label>
              <input
                type="number"
                id="fasting_glucose"
                name="fasting_glucose"
                value={formData.fasting_glucose}
                onChange={handleChange}
                placeholder="例: 100"
                min="50"
                max="500"
              />
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="ifg"
                  checked={formData.ifg}
                  onChange={handleChange}
                />
                IFG (空腹血糖異常)
              </label>
            </div>

            <div className="form-group">
              <label htmlFor="hba1c">HbA1C (%)</label>
              <input
                type="number"
                id="hba1c"
                name="hba1c"
                value={formData.hba1c}
                onChange={handleChange}
                placeholder="例: 5.5"
                min="3"
                max="20"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="insulin">Insulin (μIU/mL)</label>
              <input
                type="number"
                id="insulin"
                name="insulin"
                value={formData.insulin}
                onChange={handleChange}
                placeholder="例: 10.5"
                min="0"
                max="100"
                step="0.1"
              />
            </div>
          </div>
        </div>

        {/* 生命徵象 */}
        <div className="form-section">
          <h3>生命徵象</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="pulse_rate">Pulse Rate (bpm)</label>
              <input
                type="number"
                id="pulse_rate"
                name="pulse_rate"
                value={formData.pulse_rate}
                onChange={handleChange}
                placeholder="例: 72"
                min="30"
                max="200"
              />
            </div>

            <div className="form-group">
              <label htmlFor="systolic_bp">BP, Systolic (mmHg)</label>
              <input
                type="number"
                id="systolic_bp"
                name="systolic_bp"
                value={formData.systolic_bp}
                onChange={handleChange}
                placeholder="例: 120"
                min="70"
                max="250"
                className={validationErrors.systolic_bp ? 'error' : ''}
              />
              {validationErrors.systolic_bp && (
                <span className="error-text">{validationErrors.systolic_bp}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="diastolic_bp">BP, Diastolic (mmHg)</label>
              <input
                type="number"
                id="diastolic_bp"
                name="diastolic_bp"
                value={formData.diastolic_bp}
                onChange={handleChange}
                placeholder="例: 80"
                min="40"
                max="150"
                className={validationErrors.diastolic_bp ? 'error' : ''}
              />
              {validationErrors.diastolic_bp && (
                <span className="error-text">{validationErrors.diastolic_bp}</span>
              )}
            </div>
          </div>
        </div>

        {/* 腎功能檢查 */}
        <div className="form-section">
          <h3>腎功能檢查</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="serum_creatinine">血清肌酸酐 Scr (mg/dL)</label>
              <input
                type="number"
                id="serum_creatinine"
                name="serum_creatinine"
                value={formData.serum_creatinine}
                onChange={handleChange}
                placeholder="例: 1.0"
                min="0.1"
                max="10"
                step="0.01"
              />
            </div>
          </div>
        </div>

        {/* 血脂檢查 */}
        <div className="form-section">
          <h3>血脂檢查</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="triglycerides">TG 三酸甘油脂 (mg/dL)</label>
              <input
                type="number"
                id="triglycerides"
                name="triglycerides"
                value={formData.triglycerides}
                onChange={handleChange}
                placeholder="例: 150"
                min="20"
                max="1000"
              />
            </div>

            <div className="form-group">
              <label htmlFor="total_cholesterol">TC 總膽固醇 (mg/dL)</label>
              <input
                type="number"
                id="total_cholesterol"
                name="total_cholesterol"
                value={formData.total_cholesterol}
                onChange={handleChange}
                placeholder="例: 200"
                min="50"
                max="500"
              />
            </div>

            <div className="form-group">
              <label htmlFor="hdl_cholesterol">HDL-C (mg/dL)</label>
              <input
                type="number"
                id="hdl_cholesterol"
                name="hdl_cholesterol"
                value={formData.hdl_cholesterol}
                onChange={handleChange}
                placeholder="例: 50"
                min="10"
                max="150"
              />
            </div>

            <div className="form-group">
              <label htmlFor="ldl_cholesterol">LDL-C (mg/dL)</label>
              <input
                type="number"
                id="ldl_cholesterol"
                name="ldl_cholesterol"
                value={formData.ldl_cholesterol}
                onChange={handleChange}
                placeholder="例: 120"
                min="20"
                max="400"
              />
            </div>
          </div>
        </div>

        {/* 其他生化指標 */}
        <div className="form-section">
          <h3>其他生化指標</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="uric_acid">uric acid (mg/dL)</label>
              <input
                type="number"
                id="uric_acid"
                name="uric_acid"
                value={formData.uric_acid}
                onChange={handleChange}
                placeholder="例: 6.5"
                min="1"
                max="15"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="homocysteine">Hcy (μmol/L)</label>
              <input
                type="number"
                id="homocysteine"
                name="homocysteine"
                value={formData.homocysteine}
                onChange={handleChange}
                placeholder="例: 12.5"
                min="1"
                max="50"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="hs_crp">hsCRP, mg/L</label>
              <input
                type="number"
                id="hs_crp"
                name="hs_crp"
                value={formData.hs_crp}
                onChange={handleChange}
                placeholder="例: 1.5"
                min="0"
                max="20"
                step="0.01"
              />
            </div>
          </div>
        </div>

        {/* 肝功能檢查 */}
        <div className="form-section">
          <h3>肝功能檢查</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="alt_gpt">ALT/GPT (U/L)</label>
              <input
                type="number"
                id="alt_gpt"
                name="alt_gpt"
                value={formData.alt_gpt}
                onChange={handleChange}
                placeholder="例: 25"
                min="0"
                max="500"
              />
            </div>

            <div className="form-group">
              <label htmlFor="ast_got">AST/GOT (U/L)</label>
              <input
                type="number"
                id="ast_got"
                name="ast_got"
                value={formData.ast_got}
                onChange={handleChange}
                placeholder="例: 30"
                min="0"
                max="500"
              />
            </div>

            <div className="form-group">
              <label htmlFor="ast_uln">AST ULN</label>
              <input
                type="number"
                id="ast_uln"
                name="ast_uln"
                value={formData.ast_uln}
                onChange={handleChange}
                placeholder="例: 1.2"
                min="0"
                max="10"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="ggt">GGT (U/L)</label>
              <input
                type="number"
                id="ggt"
                name="ggt"
                value={formData.ggt}
                onChange={handleChange}
                placeholder="例: 35"
                min="0"
                max="500"
              />
            </div>

            <div className="form-group">
              <label htmlFor="total_protein">TotalProtein (g/dL)</label>
              <input
                type="number"
                id="total_protein"
                name="total_protein"
                value={formData.total_protein}
                onChange={handleChange}
                placeholder="例: 7.2"
                min="3"
                max="12"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="albumin">Albumin (g/dL)</label>
              <input
                type="number"
                id="albumin"
                name="albumin"
                value={formData.albumin}
                onChange={handleChange}
                placeholder="例: 4.2"
                min="1"
                max="8"
                step="0.1"
              />
            </div>
          </div>
        </div>

        {/* 尿液檢查 */}
        <div className="form-section">
          <h3>尿液檢查</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="urine_albumin">Urine Albumin (mg/dl)</label>
              <input
                type="number"
                id="urine_albumin"
                name="urine_albumin"
                value={formData.urine_albumin}
                onChange={handleChange}
                placeholder="例: 15.5"
                min="0"
                max="1000"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="urine_creatinine">Urine creatinine (mg/dL)</label>
              <input
                type="number"
                id="urine_creatinine"
                name="urine_creatinine"
                value={formData.urine_creatinine}
                onChange={handleChange}
                placeholder="例: 120.5"
                min="0"
                max="500"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="urine_albumin_creatinine_ratio">Urinary albumin to creatinine ratio</label>
              <input
                type="number"
                id="urine_albumin_creatinine_ratio"
                name="urine_albumin_creatinine_ratio"
                value={formData.urine_albumin_creatinine_ratio}
                onChange={handleChange}
                placeholder="例: 12.8"
                min="0"
                max="1000"
                step="0.1"
              />
            </div>
          </div>
        </div>

        {/* 基因檢測 */}
        <div className="form-section">
          <h3>基因檢測</h3>
          <div className="form-grid">
            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="apoe_e4"
                  checked={formData.apoe_e4}
                  onChange={handleChange}
                />
                APOE ε4 陽性
              </label>
            </div>
          </div>
        </div>

        {/* 飲食習慣調查 */}
        <div className="form-section">
          <h3>飲食習慣調查</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="daily_vegetables_fruits">每日蔬果攝取量</label>
              <select
                id="daily_vegetables_fruits"
                name="daily_vegetables_fruits"
                value={formData.daily_vegetables_fruits}
                onChange={handleChange}
              >
                <option value="">請選擇</option>
                <option value="0">0份蔬果 (幾乎不吃)</option>
                <option value="1">1份蔬果</option>
                <option value="2">2份蔬果</option>
                <option value="3">3份蔬果</option>
                <option value="4">4份蔬果</option>
                <option value="5">5份蔬果 (建議量)</option>
                <option value="6">6份蔬果</option>
                <option value="7">7份蔬果</option>
                <option value="8+">8份以上蔬果</option>
              </select>
              <small>建議每日至少5份蔬果 (1份約等於1個拳頭大小)</small>
            </div>
          </div>
        </div>

        {/* 運動習慣調查 */}
        <div className="form-section">
          <h3>運動習慣調查</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="exercise_frequency">運動頻率</label>
              <select
                id="exercise_frequency"
                name="exercise_frequency"
                value={formData.exercise_frequency}
                onChange={handleChange}
              >
                <option value="">請選擇</option>
                <option value="never">從不運動</option>
                <option value="rarely">很少運動 (每月1-2次)</option>
                <option value="sometimes">偶爾運動 (每週1次)</option>
                <option value="regularly">規律運動 (每週2-3次)</option>
                <option value="regularly">經常運動 (每週4-5次)</option>
                <option value="regularly">每日運動</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="exercise_intensity">運動強度</label>
              <select
                id="exercise_intensity"
                name="exercise_intensity"
                value={formData.exercise_intensity}
                onChange={handleChange}
              >
                <option value="">請選擇</option>
                <option value="light">輕度運動 (散步、伸展)</option>
                <option value="moderate">中度運動 (快走、游泳、騎車)</option>
                <option value="vigorous">高強度運動 (跑步、球類運動)</option>
                <option value="intense">劇烈運動 (競技運動、重訓)</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="exercise_duration">每次運動時間</label>
              <select
                id="exercise_duration"
                name="exercise_duration"
                value={formData.exercise_duration}
                onChange={handleChange}
              >
                <option value="">請選擇</option>
                <option value="<15">少於15分鐘</option>
                <option value="15-30">15-30分鐘</option>
                <option value="30-60">30-60分鐘</option>
                <option value="60-90">60-90分鐘</option>
                <option value=">90">超過90分鐘</option>
              </select>
            </div>
          </div>
        </div>

        {/* 抽菸習慣調查 */}
        <div className="form-section">
          <h3>抽菸習慣調查</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="smoking_history">抽菸狀況</label>
              <select
                id="smoking_history"
                name="smoking_history"
                value={formData.smoking_history}
                onChange={handleChange}
              >
                <option value="never">從未抽菸</option>
                <option value="former">已戒菸</option>
                <option value="current">目前抽菸</option>
                <option value="occasional">偶爾抽菸</option>
              </select>
            </div>

            {(formData.smoking_history === 'current' || formData.smoking_history === 'occasional') && (
              <>
                <div className="form-group">
                  <label htmlFor="cigarettes_per_day">每日抽菸量 (支)</label>
                  <input
                    type="number"
                    id="cigarettes_per_day"
                    name="cigarettes_per_day"
                    value={formData.cigarettes_per_day}
                    onChange={handleChange}
                    placeholder="例: 10"
                    min="0"
                    max="100"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="smoking_years">抽菸年數</label>
                  <input
                    type="number"
                    id="smoking_years"
                    name="smoking_years"
                    value={formData.smoking_years}
                    onChange={handleChange}
                    placeholder="例: 5"
                    min="0"
                    max="80"
                  />
                </div>
              </>
            )}

            {formData.smoking_history === 'former' && (
              <div className="form-group">
                <label htmlFor="quit_smoking_years">戒菸多久 (年)</label>
                <input
                  type="number"
                  id="quit_smoking_years"
                  name="quit_smoking_years"
                  value={formData.quit_smoking_years}
                  onChange={handleChange}
                  placeholder="例: 2"
                  min="0"
                  max="50"
                  step="0.1"
                />
              </div>
            )}
          </div>
        </div>

        {/* 飲酒習慣調查 */}
        <div className="form-section">
          <h3>飲酒習慣調查</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="alcohol_frequency">飲酒頻率</label>
              <select
                id="alcohol_frequency"
                name="alcohol_frequency"
                value={formData.alcohol_frequency}
                onChange={handleChange}
              >
                <option value="never">從不飲酒</option>
                <option value="rarely">很少飲酒 (每月1-2次)</option>
                <option value="sometimes">偶爾飲酒 (每週1次)</option>
                <option value="regularly">規律飲酒 (每週2-3次)</option>
                <option value="frequently">經常飲酒 (每週4-5次)</option>
                <option value="daily">每日飲酒</option>
              </select>
            </div>

            {formData.alcohol_frequency !== 'never' && (
              <>
                <div className="form-group">
                  <label htmlFor="alcohol_type">主要飲酒類型</label>
                  <select
                    id="alcohol_type"
                    name="alcohol_type"
                    value={formData.alcohol_type}
                    onChange={handleChange}
                  >
                    <option value="">請選擇</option>
                    <option value="beer">啤酒</option>
                    <option value="wine">葡萄酒</option>
                    <option value="spirits">烈酒</option>
                    <option value="mixed">混合飲用</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="drinks_per_week">每週飲酒量 (標準杯)</label>
                  <input
                    type="number"
                    id="drinks_per_week"
                    name="drinks_per_week"
                    value={formData.drinks_per_week}
                    onChange={handleChange}
                    placeholder="例: 3"
                    min="0"
                    max="50"
                    step="0.5"
                  />
                  <small>1標準杯 = 1罐啤酒 = 1杯紅酒 = 1小杯烈酒</small>
                </div>
              </>
            )}
          </div>
        </div>

        {/* 家族病史調查 */}
        <div className="form-section">
          <h3>家族病史調查</h3>
          <div className="form-grid">
            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="family_diabetes"
                  checked={formData.family_diabetes}
                  onChange={handleChange}
                />
                家族糖尿病史 (父母、兄弟姊妹)
              </label>
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="family_heart_disease"
                  checked={formData.family_heart_disease}
                  onChange={handleChange}
                />
                家族心臟病史 (冠心病、心肌梗塞)
              </label>
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="family_hypertension"
                  checked={formData.family_hypertension}
                  onChange={handleChange}
                />
                家族高血壓史
              </label>
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="family_hyperlipidemia"
                  checked={formData.family_hyperlipidemia}
                  onChange={handleChange}
                />
                家族高血脂史
              </label>
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="family_stroke"
                  checked={formData.family_stroke}
                  onChange={handleChange}
                />
                家族中風史
              </label>
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="family_cancer"
                  checked={formData.family_cancer}
                  onChange={handleChange}
                />
                家族癌症史
              </label>
            </div>

            <div className="form-group">
              <label htmlFor="family_other_diseases">其他家族疾病史</label>
              <textarea
                id="family_other_diseases"
                name="family_other_diseases"
                value={formData.family_other_diseases}
                onChange={handleChange}
                placeholder="請描述其他重要的家族疾病史..."
                rows="2"
              />
            </div>
          </div>
        </div>

        {/* 個人病史調查 */}
        <div className="form-section">
          <h3>個人病史調查</h3>
          <div className="form-grid">
            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="personal_diabetes"
                  checked={formData.personal_diabetes}
                  onChange={handleChange}
                />
                個人糖尿病史
              </label>
            </div>

            {formData.personal_diabetes && (
              <>
                <div className="form-group">
                  <label htmlFor="personal_diabetes_type">糖尿病類型</label>
                  <select
                    id="personal_diabetes_type"
                    name="personal_diabetes_type"
                    value={formData.personal_diabetes_type}
                    onChange={handleChange}
                  >
                    <option value="">請選擇</option>
                    <option value="type1">第一型糖尿病</option>
                    <option value="type2">第二型糖尿病</option>
                    <option value="gestational">妊娠糖尿病</option>
                    <option value="other">其他類型</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="personal_diabetes_years">患病年數</label>
                  <input
                    type="number"
                    id="personal_diabetes_years"
                    name="personal_diabetes_years"
                    value={formData.personal_diabetes_years}
                    onChange={handleChange}
                    placeholder="例: 3"
                    min="0"
                    max="80"
                    step="0.1"
                  />
                </div>
              </>
            )}

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="personal_heart_disease"
                  checked={formData.personal_heart_disease}
                  onChange={handleChange}
                />
                個人心臟病史
              </label>
            </div>

            {formData.personal_heart_disease && (
              <div className="form-group">
                <label htmlFor="personal_heart_disease_type">心臟病類型</label>
                <select
                  id="personal_heart_disease_type"
                  name="personal_heart_disease_type"
                  value={formData.personal_heart_disease_type}
                  onChange={handleChange}
                >
                  <option value="">請選擇</option>
                  <option value="coronary">冠心病</option>
                  <option value="myocardial">心肌梗塞</option>
                  <option value="arrhythmia">心律不整</option>
                  <option value="valve">心瓣膜疾病</option>
                  <option value="other">其他心臟疾病</option>
                </select>
              </div>
            )}

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="personal_hypertension"
                  checked={formData.personal_hypertension}
                  onChange={handleChange}
                />
                個人高血壓史
              </label>
            </div>

            {formData.personal_hypertension && (
              <div className="form-group">
                <label htmlFor="personal_hypertension_years">高血壓患病年數</label>
                <input
                  type="number"
                  id="personal_hypertension_years"
                  name="personal_hypertension_years"
                  value={formData.personal_hypertension_years}
                  onChange={handleChange}
                  placeholder="例: 2"
                  min="0"
                  max="80"
                  step="0.1"
                />
              </div>
            )}

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="personal_hyperlipidemia"
                  checked={formData.personal_hyperlipidemia}
                  onChange={handleChange}
                />
                個人高血脂史
              </label>
            </div>

            {formData.personal_hyperlipidemia && (
              <div className="form-group">
                <label htmlFor="personal_hyperlipidemia_years">高血脂患病年數</label>
                <input
                  type="number"
                  id="personal_hyperlipidemia_years"
                  name="personal_hyperlipidemia_years"
                  value={formData.personal_hyperlipidemia_years}
                  onChange={handleChange}
                  placeholder="例: 1"
                  min="0"
                  max="80"
                  step="0.1"
                />
              </div>
            )}

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="personal_stroke"
                  checked={formData.personal_stroke}
                  onChange={handleChange}
                />
                個人中風史
              </label>
            </div>

            <div className="form-group">
              <label htmlFor="personal_other_diseases">其他個人疾病史</label>
              <textarea
                id="personal_other_diseases"
                name="personal_other_diseases"
                value={formData.personal_other_diseases}
                onChange={handleChange}
                placeholder="請描述其他重要的個人疾病史..."
                rows="2"
              />
            </div>
          </div>
        </div>

        {/* 用藥和過敏史 */}
        <div className="form-section">
          <h3>用藥和過敏史</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="current_medications">目前用藥</label>
              <textarea
                id="current_medications"
                name="current_medications"
                value={formData.current_medications}
                onChange={handleChange}
                placeholder="請列出目前正在服用的藥物 (包括保健食品)..."
                rows="3"
              />
            </div>

            <div className="form-group">
              <label htmlFor="allergies">過敏史</label>
              <textarea
                id="allergies"
                name="allergies"
                value={formData.allergies}
                onChange={handleChange}
                placeholder="請列出已知的藥物、食物或其他過敏反應..."
                rows="3"
              />
            </div>
          </div>
        </div>

        <div className="form-actions">
          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? '提交中...' : '提交健康數據'}
          </button>
          <Link to="/dashboard" className="cancel-btn">
            返回儀表板
          </Link>
          <Link to="/risk-analysis" className="next-btn">
            查看風險分析 →
          </Link>
        </div>
      </form>
    </div>
  );
}

export default HealthDataInput;
