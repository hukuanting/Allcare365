import React, { useState, useEffect, useRef } from 'react';
import { api } from '../config/api';
import './HealthDataInput.css';
import './HealthRecords.css';

function HealthRecords() {
  // Patient search and selection
  const [patients, setPatients] = useState([]);
  const [filteredPatients, setFilteredPatients] = useState([]);
  const [patientSearchTerm, setPatientSearchTerm] = useState('');
  const [showPatientDropdown, setShowPatientDropdown] = useState(false);
  const [loadingPatients, setLoadingPatients] = useState(false);

  const [selectedPatient, setSelectedPatient] = useState('');
  const [selectedPatientInfo, setSelectedPatientInfo] = useState(null);

  // Screenings for selected patient
  const [healthScreenings, setHealthScreenings] = useState([]);
  const [selectedScreening, setSelectedScreening] = useState('');
  const [selectedScreeningData, setSelectedScreeningData] = useState(null);
  const [loadingScreening, setLoadingScreening] = useState(false);

  // Errors/messages
  const [error, setError] = useState('');

  // Refs for dropdown handling
  const patientSearchRef = useRef(null);
  const dropdownRef = useRef(null);
  const debouncedSearch = useRef(null);

  useEffect(() => {
    // click outside to close dropdown
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target) &&
          patientSearchRef.current && !patientSearchRef.current.contains(event.target)) {
        setShowPatientDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter patients client-side as user types; load from API when >= 2 chars (debounced)
  useEffect(() => {
    if (patientSearchTerm.trim() === '') {
      setFilteredPatients([]);
      return;
    }
    const searchLower = patientSearchTerm.toLowerCase();
    const filtered = patients.filter(p => {
      const fullName = `${p.first_name} ${p.last_name}`.toLowerCase();
      const pid = (p.patient_id || p.medical_record_number || '').toLowerCase();
      return fullName.includes(searchLower) || pid.includes(searchLower) ||
             p.first_name.toLowerCase().includes(searchLower) || p.last_name.toLowerCase().includes(searchLower);
    });
    setFilteredPatients(filtered.slice(0, 10));
  }, [patientSearchTerm, patients]);

  const fetchPatients = async (term = '') => {
    try {
      setLoadingPatients(true);
      const searchParam = term ? `?search=${encodeURIComponent(term)}` : '';
      const response = await api.get(`/api/patients/${searchParam}`);
      if (response.ok) {
        const data = await response.json();
        setPatients(data.results || data || []);
        if (term) setFilteredPatients((data.results || data || []).slice(0, 10));
      }
    } catch (e) {
      console.error('Failed to fetch patients:', e);
    } finally {
      setLoadingPatients(false);
    }
  };

  const handlePatientSearch = (term) => {
    setPatientSearchTerm(term);
    setShowPatientDropdown(true);
    if (debouncedSearch.current) clearTimeout(debouncedSearch.current);
    if (term.trim().length >= 2) {
      debouncedSearch.current = setTimeout(() => fetchPatients(term), 300);
    }
  };

  const selectPatient = (patient) => {
    setSelectedPatient(patient.id);
    setSelectedPatientInfo(patient);
    setPatientSearchTerm(`${patient.first_name} ${patient.last_name} (${patient.patient_id || patient.medical_record_number || patient.id})`);
    setShowPatientDropdown(false);
    setFilteredPatients([]);

    // reset screenings
    setHealthScreenings([]);
    setSelectedScreening('');
    setSelectedScreeningData(null);

    // load screenings for patient
    fetchHealthScreenings(patient.id);
  };

  const clearPatientSelection = () => {
    setSelectedPatient('');
    setSelectedPatientInfo(null);
    setPatientSearchTerm('');
    setShowPatientDropdown(false);
    setFilteredPatients([]);
    setHealthScreenings([]);
    setSelectedScreening('');
    setSelectedScreeningData(null);
  };

  const fetchHealthScreenings = async (patientId) => {
    try {
      const response = await api.get(`/api/health-screening/screenings/?patient_id=${patientId}`);
      if (response.ok) {
        const data = await response.json();
        const screenings = data.results || data || [];
        setHealthScreenings(Array.isArray(screenings) ? screenings : []);
      }
    } catch (e) {
      console.error('Failed to fetch health screenings:', e);
      setHealthScreenings([]);
    }
  };

  const fetchScreeningDetail = async (screeningId) => {
    if (!screeningId) return;
    try {
      setLoadingScreening(true);
      setError('');
      const response = await api.get(`/api/health-screening/screenings/${screeningId}/`);
      if (response.ok) {
        const data = await response.json();
        setSelectedScreeningData(data);
      } else {
        const text = await response.text();
        setError(text || '無法載入健檢資料');
      }
    } catch (e) {
      console.error('Failed to fetch screening detail:', e);
      setError('載入健檢資料時發生錯誤');
    } finally {
      setLoadingScreening(false);
    }
  };

  const handleSelectScreening = (value) => {
    setSelectedScreening(value);
    setSelectedScreeningData(null);
    if (value) fetchScreeningDetail(value);
  };

  // Helpers
  const formatDate = (dateString) => {
    if (!dateString) return '—';
    try { return new Date(dateString).toLocaleDateString('zh-TW'); } catch { return dateString; }
  };
  const fmt = (v, suffix = '') => (v === null || v === undefined || v === '' ? '—' : `${v}${suffix}`);
  const fmtBool = (v) => (v === true ? '是' : v === false ? '否' : '—');

  return (
    <div className="health-records">
      <div className="page-header">
        <h2>健檢記錄查詢</h2>
        <p>搜尋患者，選擇健檢記錄，並查看詳細數據</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Selection */}
      <div className="selection-section">
        <div className="form-group patient-search-group">
          <label htmlFor="patient-search">搜尋患者:</label>
          <div className="patient-search-container" ref={patientSearchRef}>
            <div className="search-input-wrapper">
              <input
                id="patient-search"
                type="text"
                value={patientSearchTerm}
                onChange={(e) => handlePatientSearch(e.target.value)}
                onFocus={() => setShowPatientDropdown(true)}
                placeholder="輸入患者姓名、病歷號或身分證字號..."
                className="patient-search-input"
                autoComplete="off"
              />
              {selectedPatient && (
                <button
                  type="button"
                  onClick={clearPatientSelection}
                  className="clear-selection-btn"
                  title="清除選擇"
                >
                  ×
                </button>
              )}
              {loadingPatients && (
                <div className="search-loading">
                  <span className="loading-spinner"></span>
                </div>
              )}
            </div>

            {showPatientDropdown && filteredPatients.length > 0 && (
              <div className="patient-dropdown" ref={dropdownRef}>
                <div className="dropdown-header">
                  找到 {filteredPatients.length} 位患者 {filteredPatients.length >= 10 && '(顯示前10位)'}
                </div>
                {filteredPatients.map(p => (
                  <div key={p.id} className="patient-option" onClick={() => selectPatient(p)}>
                    <div className="patient-info">
                      <div className="patient-name">{p.first_name} {p.last_name}</div>
                      <div className="patient-details">
                        <span className="patient-id">病歷號: {p.patient_id || p.medical_record_number || 'N/A'}</span>
                        {p.date_of_birth && (
                          <span className="patient-birth">，生日: {new Date(p.date_of_birth).toLocaleDateString('zh-TW')}</span>
                        )}
                        {p.gender && (
                          <span className="patient-gender">，性別: {p.gender === 'M' ? '男' : p.gender === 'F' ? '女' : '其他'}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {showPatientDropdown && patientSearchTerm.trim().length >= 2 && filteredPatients.length === 0 && !loadingPatients && (
              <div className="patient-dropdown">
                <div className="no-results">未找到符合 "{patientSearchTerm}" 的患者</div>
              </div>
            )}

            {showPatientDropdown && patientSearchTerm.trim().length > 0 && patientSearchTerm.trim().length < 2 && (
              <div className="patient-dropdown">
                <div className="search-hint">請輸入至少2個字元進行搜尋</div>
              </div>
            )}
          </div>

          {selectedPatientInfo && (
            <div className="selected-patient-info">
              <h4>已選擇患者:</h4>
              <div className="patient-card">
                <div className="patient-basic-info">
                  <span className="patient-name-display">{selectedPatientInfo.first_name} {selectedPatientInfo.last_name}</span>
                  <span className="patient-id-display">({selectedPatientInfo.patient_id || selectedPatientInfo.medical_record_number || selectedPatientInfo.id})</span>
                </div>
                {selectedPatientInfo.date_of_birth && (
                  <div className="patient-meta">
                    生日: {new Date(selectedPatientInfo.date_of_birth).toLocaleDateString('zh-TW')}
                    {selectedPatientInfo.gender && (
                      <span className="gender-info">，性別: {selectedPatientInfo.gender === 'M' ? '男' : selectedPatientInfo.gender === 'F' ? '女' : '其他'}</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {selectedPatient && (
          <div className="form-group">
            <label htmlFor="screening-select">選擇健康檢查紀錄:</label>
            <select
              id="screening-select"
              value={selectedScreening}
              onChange={(e) => handleSelectScreening(e.target.value)}
              className="screening-select"
            >
              <option value="">請選擇檢查紀錄</option>
              {healthScreenings.map(s => (
                <option key={s.id} value={s.id}>
                  {formatDate(s.screening_date)} - {s.screening_type}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Results */}
      {loadingScreening && <div className="loading">載入中...</div>}

      {selectedScreeningData && (
        <>
          {/* Basic Info */}
          <div className="section-card">
            <h3>基本資訊</h3>
            <table className="info-table">
              <tbody>
                <tr>
                  <td className="label">患者</td>
                  <td className="value">{selectedScreeningData.patient_name || '—'}</td>
                  <td className="label">病歷號</td>
                  <td className="value">{selectedScreeningData.patient_medical_record_number || '—'}</td>
                </tr>
                <tr>
                  <td className="label">檢查日期</td>
                  <td className="value">{formatDate(selectedScreeningData.screening_date)}</td>
                  <td className="label">檢查類型</td>
                  <td className="value">{selectedScreeningData.screening_type || '—'}</td>
                </tr>
                <tr>
                  <td className="label">檢查醫師</td>
                  <td className="value">{selectedScreeningData.provider_name || '—'}</td>
                  <td className="label">檢查時年齡</td>
                  <td className="value">{fmt(selectedScreeningData.age_at_screening, ' 歲')}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Vital Signs - full */}
          <div className="section-card">
            <h3>生命徵象與身體測量</h3>
            <table className="info-table">
              <tbody>
                <tr>
                  <td className="label">身高</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.height_cm, ' cm')}</td>
                  <td className="label">體重</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.weight_kg, ' kg')}</td>
                </tr>
                <tr>
                  <td className="label">BMI</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.bmi)}</td>
                  <td className="label">脈搏</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.pulse_rate_bpm, ' 次/分')}</td>
                </tr>
                <tr>
                  <td className="label">收縮壓</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.systolic_bp_mmhg, ' mmHg')}</td>
                  <td className="label">舒張壓</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.diastolic_bp_mmhg, ' mmHg')}</td>
                </tr>
                <tr>
                  <td className="label">脈壓</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.pulse_pressure_mmhg, ' mmHg')}</td>
                  <td className="label">平均動脈壓</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.mean_arterial_pressure_mmhg, ' mmHg')}</td>
                </tr>
                <tr>
                  <td className="label">中央收縮壓</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.central_systolic_bp_mmhg, ' mmHg')}</td>
                  <td className="label">中央舒張壓</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.central_diastolic_bp_mmhg, ' mmHg')}</td>
                </tr>
                <tr>
                  <td className="label">頸圍</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.neck_circumference_cm, ' cm')}</td>
                  <td className="label">胸圍</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.chest_circumference_cm, ' cm')}</td>
                </tr>
                <tr>
                  <td className="label">腰圍</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.waist_circumference_cm, ' cm')}</td>
                  <td className="label">臀圍</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.hip_circumference_cm, ' cm')}</td>
                </tr>
                <tr>
                  <td className="label">腰臀比</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.waist_hip_ratio)}</td>
                  <td className="label">腰高比</td>
                  <td className="value">{fmt(selectedScreeningData?.vital_signs?.waist_height_ratio)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Laboratory Results - 全面 */}
          <div className="section-card">
            <h3>檢驗數據</h3>
            <table className="info-table">
              <tbody>
                {/* CBC */}
                <tr>
                  <td className="label">RBC</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.rbc_count, ' 10^6/μL')}</td>
                  <td className="label">RDW-CV%</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.rdw_cv_percent, ' %')}</td>
                </tr>
                <tr>
                  <td className="label">WBC</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.wbc_count, ' 10^3/μL')}</td>
                  <td className="label">Platelet</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.platelet_count, ' 10^3/μL')}</td>
                </tr>
                <tr>
                  <td className="label">Monocyte%</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.monocyte_percent, ' %')}</td>
                  <td className="label">Monocyte 絕對值</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.monocyte_absolute, ' ×10^9/L')}</td>
                </tr>

                {/* Glucose metabolism */}
                <tr>
                  <td className="label">空腹血糖</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.fasting_glucose_mgdl, ' mg/dL')}</td>
                  <td className="label">IFG</td>
                  <td className="value">{fmtBool(selectedScreeningData?.laboratory_results?.impaired_fasting_glucose)}</td>
                </tr>
                <tr>
                  <td className="label">HbA1c</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.hba1c_percent, ' %')}</td>
                  <td className="label">估計平均血糖</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.estimated_avg_glucose_mgdl, ' mg/dL')}</td>
                </tr>
                <tr>
                  <td className="label">Insulin</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.insulin_uiu_ml, ' μIU/mL')}</td>
                  <td className="label">HOMA-IR</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.homa_ir)}</td>
                </tr>
                <tr>
                  <td className="label">eGDR</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.egdr)}</td>
                  <td className="label"></td>
                  <td className="value"></td>
                </tr>

                {/* Lipids */}
                <tr>
                  <td className="label">TG</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.triglycerides_mgdl, ' mg/dL')}</td>
                  <td className="label">TC</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.total_cholesterol_mgdl, ' mg/dL')}</td>
                </tr>
                <tr>
                  <td className="label">HDL-C</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.hdl_cholesterol_mgdl, ' mg/dL')}</td>
                  <td className="label">LDL-C</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.ldl_cholesterol_mgdl, ' mg/dL')}</td>
                </tr>
                <tr>
                  <td className="label">非HDL-C</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.non_hdl_cholesterol_mgdl, ' mg/dL')}</td>
                  <td className="label">PLP膽固醇</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.plp_cholesterol_mgdl, ' mg/dL')}</td>
                </tr>
                {/* Calculated Lipid Ratios */}
                <tr>
                  <td className="label">TC/HDL 比</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.tc_hdl_ratio)}</td>
                  <td className="label">LDL/HDL 比</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.ldl_hdl_ratio)}</td>
                </tr>
                <tr>
                  <td className="label">TG/HDL 比</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.tg_hdl_ratio)}</td>
                  <td className="label">非HDL/HDL 比</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.non_hdl_hdl_ratio)}</td>
                </tr>
                <tr>
                  <td className="label">AIP 動脈硬化指數</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.atherogenic_index_plasma)}</td>
                  <td className="label">TyG 指數</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.triglyceride_glucose_index)}</td>
                </tr>
                <tr>
                  <td className="label">TyG-BMI</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.tyg_bmi)}</td>
                  <td className="label"></td>
                  <td className="value"></td>
                </tr>

                {/* Other biomarkers */}
                <tr>
                  <td className="label">尿酸</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.uric_acid_mgdl, ' mg/dL')}</td>
                  <td className="label">同半胱胺酸</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.homocysteine_umol_l, ' μmol/L')}</td>
                </tr>
                <tr>
                  <td className="label">hs-CRP</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.hs_crp_mgdl, ' mg/L')}</td>
                  <td className="label"></td>
                  <td className="value"></td>
                </tr>

                {/* Liver */}
                <tr>
                  <td className="label">ALT/GPT</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.alt_gpt_ul, ' U/L')}</td>
                  <td className="label">AST/GOT</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.ast_got_ul, ' U/L')}</td>
                </tr>
                <tr>
                  <td className="label">AST/ALT 比</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.ast_alt_ratio)}</td>
                  <td className="label">AST ULN 比</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.ast_uln_ratio)}</td>
                </tr>
                <tr>
                  <td className="label">GGT</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.ggt_ul, ' U/L')}</td>
                  <td className="label">總蛋白</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.total_protein_gdl, ' g/dL')}</td>
                </tr>
                <tr>
                  <td className="label">白蛋白</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.albumin_gdl, ' g/dL')}</td>
                  <td className="label">球蛋白</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.globulin_gdl, ' g/dL')}</td>
                </tr>
                <tr>
                  <td className="label">白蛋白/球蛋白 比</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.albumin_globulin_ratio)}</td>
                  <td className="label"></td>
                  <td className="value"></td>
                </tr>

                {/* Kidney */}
                <tr>
                  <td className="label">血清肌酸酐</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.serum_creatinine_mgdl, ' mg/dL')}</td>
                  <td className="label">尿蛋白 (mg/dL)</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.urine_albumin_mgdl, ' mg/dL')}</td>
                </tr>
                <tr>
                  <td className="label">尿肌酸酐 (mg/dL)</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.urine_creatinine_mgdl, ' mg/dL')}</td>
                  <td className="label">尿蛋白/肌酸酐比</td>
                  <td className="value">{fmt(selectedScreeningData?.laboratory_results?.urine_albumin_creatinine_ratio)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Medical History & Lifestyle (擴充) */}
          <div className="section-card">
            <h3>病史與生活習慣</h3>
            <table className="info-table">
              <tbody>
                {/* Medical History */}
                <tr>
                  <td className="label">糖尿病治療中</td>
                  <td className="value">{fmtBool(selectedScreeningData?.medical_history?.diabetes_treated)}</td>
                  <td className="label">高血壓治療中</td>
                  <td className="value">{fmtBool(selectedScreeningData?.medical_history?.hypertension_treated)}</td>
                </tr>
                <tr>
                  <td className="label">高血脂治療中</td>
                  <td className="value">{fmtBool(selectedScreeningData?.medical_history?.hyperlipidemia_treated)}</td>
                  <td className="label">高血壓病史</td>
                  <td className="value">{fmtBool(selectedScreeningData?.medical_history?.hypertension_history)}</td>
                </tr>
                <tr>
                  <td className="label">APOE ε4 陽性</td>
                  <td className="value">{fmtBool(selectedScreeningData?.medical_history?.apoe_e4_positive)}</td>
                  <td className="label"></td>
                  <td className="value"></td>
                </tr>

                {/* Lifestyle */}
                <tr>
                  <td className="label">飲食評分</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.diet_score)}</td>
                  <td className="label">運動評分</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.exercise_score)}</td>
                </tr>
                <tr>
                  <td className="label">運動強度</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.exercise_intensity)}</td>
                  <td className="label">每次運動時間</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.exercise_duration)}</td>
                </tr>
                <tr>
                  <td className="label">目前吸菸</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.is_current_smoker)}</td>
                  <td className="label">曾經吸菸</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.is_former_smoker)}</td>
                </tr>
                <tr>
                  <td className="label">吸菸年數</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.smoking_years, ' 年')}</td>
                  <td className="label">每日菸量</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.cigarettes_per_day, ' 支')}</td>
                </tr>
                <tr>
                  <td className="label">戒菸時間</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.quit_smoking_when)}</td>
                  <td className="label"></td>
                  <td className="value"></td>
                </tr>
                <tr>
                  <td className="label">飲酒狀況</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.drinking_status)}</td>
                  <td className="label">每週飲酒量</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.drinks_per_week)}</td>
                </tr>
                <tr>
                  <td className="label">主要飲酒類型</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.alcohol_type)}</td>
                  <td className="label">目前用藥</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.current_medications)}</td>
                </tr>
                <tr>
                  <td className="label">過敏史</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.allergies)}</td>
                  <td className="label"></td>
                  <td className="value"></td>
                </tr>

                {/* 家族病史 */}
                <tr>
                  <td className="label">家族糖尿病史</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.family_diabetes)}</td>
                  <td className="label">家族高血壓史</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.family_hypertension)}</td>
                </tr>
                <tr>
                  <td className="label">家族心臟病史</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.family_heart_disease)}</td>
                  <td className="label">家族心血管疾病史</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.family_cvd)}</td>
                </tr>
                <tr>
                  <td className="label">家族高血脂史</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.family_hyperlipidemia)}</td>
                  <td className="label">家族中風史</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.family_stroke)}</td>
                </tr>
                <tr>
                  <td className="label">家族癌症史</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.family_cancer)}</td>
                  <td className="label">家族癌症類型</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.family_cancer_type)}</td>
                </tr>
                <tr>
                  <td className="label">其他家族疾病史</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.family_other_diseases)}</td>
                  <td className="label"></td>
                  <td className="value"></td>
                </tr>

                {/* 個人病史詳情 */}
                <tr>
                  <td className="label">個人糖尿病</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.has_diabetes)}</td>
                  <td className="label">個人高血壓</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.has_hypertension)}</td>
                </tr>
                <tr>
                  <td className="label">個人血脂異常</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.has_dyslipidemia)}</td>
                  <td className="label">個人冠心病</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.has_coronary_heart_disease)}</td>
                </tr>
                <tr>
                  <td className="label">糖尿病類型</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.personal_diabetes_type)}</td>
                  <td className="label">糖尿病年數</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.personal_diabetes_years, ' 年')}</td>
                </tr>
                <tr>
                  <td className="label">心臟病類型</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.personal_heart_disease_type)}</td>
                  <td className="label">高血壓年數</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.personal_hypertension_years, ' 年')}</td>
                </tr>
                <tr>
                  <td className="label">高血脂年數</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.personal_hyperlipidemia_years, ' 年')}</td>
                  <td className="label">個人中風史</td>
                  <td className="value">{fmtBool(selectedScreeningData?.lifestyle?.personal_stroke)}</td>
                </tr>
                <tr>
                  <td className="label">其他個人疾病史</td>
                  <td className="value">{fmt(selectedScreeningData?.lifestyle?.personal_other_diseases)}</td>
                  <td className="label"></td>
                  <td className="value"></td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export default HealthRecords;
