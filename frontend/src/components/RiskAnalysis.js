import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../config/api';
import './RiskAnalysis.css';

function RiskAnalysis() {
  const [patients, setPatients] = useState([]);
  const [filteredPatients, setFilteredPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState('');
  const [selectedPatientInfo, setSelectedPatientInfo] = useState(null);
  const [patientSearchTerm, setPatientSearchTerm] = useState('');
  const [showPatientDropdown, setShowPatientDropdown] = useState(false);
  const [riskData, setRiskData] = useState(null);
  const [healthScreenings, setHealthScreenings] = useState([]);
  const [selectedScreening, setSelectedScreening] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingPatients, setLoadingPatients] = useState(false);
  
  const patientSearchRef = useRef(null);
  const dropdownRef = useRef(null);

  useEffect(() => {
    fetchPatients();
  }, []);

  useEffect(() => {
    if (selectedPatient) {
      fetchHealthScreenings(selectedPatient);
    }
  }, [selectedPatient]);

  // 患者搜尋和篩選
  useEffect(() => {
    if (patientSearchTerm.trim() === '') {
      setFilteredPatients([]);
    } else {
      const filtered = patients.filter(patient => {
        const fullName = `${patient.first_name} ${patient.last_name}`.toLowerCase();
        const patientId = (patient.patient_id || patient.medical_record_number || '').toLowerCase();
        const searchLower = patientSearchTerm.toLowerCase();
        
        return fullName.includes(searchLower) || 
               patientId.includes(searchLower) ||
               patient.first_name.toLowerCase().includes(searchLower) ||
               patient.last_name.toLowerCase().includes(searchLower);
      });
      setFilteredPatients(filtered.slice(0, 10)); // 限制顯示前10個結果
    }
  }, [patientSearchTerm, patients]);

  // 點擊外部關閉下拉選單
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target) &&
          patientSearchRef.current && !patientSearchRef.current.contains(event.target)) {
        setShowPatientDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const fetchPatients = async (searchTerm = '') => {
    try {
      setLoadingPatients(true);
      const searchParam = searchTerm ? `?search=${encodeURIComponent(searchTerm)}` : '';
      const response = await api.get(`/api/patients/${searchParam}`);
      if (response.ok) {
        const data = await response.json();
        const patientList = data.results || data;
        setPatients(patientList);
        
        // 如果是搜尋，直接設置篩選結果
        if (searchTerm) {
          setFilteredPatients(patientList.slice(0, 10));
        }
      }
    } catch (error) {
      console.error('Failed to fetch patients:', error);
    } finally {
      setLoadingPatients(false);
    }
  };

  // 延遲搜尋函數
  const debouncedSearch = useRef(null);
  const handlePatientSearch = (searchTerm) => {
    setPatientSearchTerm(searchTerm);
    setShowPatientDropdown(true);
    
    // 清除之前的延遲搜尋
    if (debouncedSearch.current) {
      clearTimeout(debouncedSearch.current);
    }
    
    // 設置新的延遲搜尋
    if (searchTerm.trim().length >= 2) {
      debouncedSearch.current = setTimeout(() => {
        fetchPatients(searchTerm);
      }, 300); // 300ms 延遲
    }
  };

  // 選擇患者
  const selectPatient = (patient) => {
    setSelectedPatient(patient.id);
    setSelectedPatientInfo(patient);
    setPatientSearchTerm(`${patient.first_name} ${patient.last_name} (${patient.patient_id || patient.medical_record_number || patient.id})`);
    setShowPatientDropdown(false);
    setFilteredPatients([]);
    
    // 清空之前的健檢記錄和風險分析
    setHealthScreenings([]);
    setSelectedScreening('');
    setRiskData(null);
  };

  // 清空患者選擇
  const clearPatientSelection = () => {
    setSelectedPatient('');
    setSelectedPatientInfo(null);
    setPatientSearchTerm('');
    setShowPatientDropdown(false);
    setFilteredPatients([]);
    setHealthScreenings([]);
    setSelectedScreening('');
    setRiskData(null);
  };

  const fetchHealthScreenings = async (patientId) => {
    try {
      const response = await api.get(`/api/health-screening/screenings/?patient_id=${patientId}`);
      if (response.ok) {
        const data = await response.json();
        console.log('Health screenings response:', data); // 調試日誌
        // 確保設置為數組
        const screenings = data.results || data || [];
        setHealthScreenings(Array.isArray(screenings) ? screenings : []);
        setSelectedScreening('');
        setRiskData(null);
      }
    } catch (error) {
      console.error('Failed to fetch health screenings:', error);
      setHealthScreenings([]); // 錯誤時設置為空數組
    }
  };

  const calculateRisk = async () => {
    if (!selectedScreening) {
      setMessage('請選擇健康檢查記錄');
      return;
    }

    setLoading(true);
    setMessage('');

    try {
      const response = await api.post(`/api/health-screening/screenings/${selectedScreening}/calculate_comprehensive_risk/`);
      if (response.ok) {
        const data = await response.json();
        console.log('風險分析數據:', data);
        
        // 檢查數據完整性
        if (data.error && data.data_integrity_check === false) {
          // 數據不完整的情況
          setMessage(`❌ 數據不完整，無法進行風險分析

缺少以下必要數據：${data.missing_data.join('、')}

${data.suggestion}

請確保已正確匯入完整的健檢數據後再進行風險分析。`);
          setRiskData(null);
        } else {
          setRiskData(data);
          setMessage('✅ 風險分析計算完成');
        }
      } else {
        const errorData = await response.json();
        setMessage(`❌ 計算失敗: ${errorData.error || '未知錯誤'}`);
      }
    } catch (error) {
      console.error('Risk calculation failed:', error);
      setMessage('❌ 計算失敗，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (category) => {
    switch (category) {
      case '低風險':
        return '#4CAF50';
      case '中低風險':
        return '#8BC34A';
      case '中等風險':
        return '#FF9800';
      case '高風險':
        return '#F44336';
      default:
        return '#9E9E9E';
    }
  };

  const getRiskIcon = (category) => {
    switch (category) {
      case '低風險':
        return '●';
      case '中低風險':
        return '●';
      case '中等風險':
        return '●';
      case '高風險':
        return '●';
      default:
        return '●';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('zh-TW');
  };

  return (
    <div className="risk-analysis">
      <div className="page-header">
        <h2>綜合疾病風險分析</h2>
        <div className="header-actions">
          <Link to="/dashboard" className="header-btn secondary">
            ← 返回儀表板
          </Link>
          <Link to="/health-data-input" className="header-btn primary">
            新增健康數據
          </Link>
        </div>
      </div>
      
      <div className="algorithm-intro">
        <div className="intro-section">
          <h3>疾病風險評估</h3>
          <p>採用三套標準化演算法進行綜合風險分析</p>
        </div>
      </div>
      
      {message && (
        <div className={`message ${message.includes('失敗') || message.includes('錯誤') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}

      {/* 患者選擇區 */}
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
                placeholder="輸入患者姓名、病歷號或身分證號..."
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
                  ✕
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
                {filteredPatients.map(patient => (
                  <div
                    key={patient.id}
                    className="patient-option"
                    onClick={() => selectPatient(patient)}
                  >
                    <div className="patient-info">
                      <div className="patient-name">
                        {patient.first_name} {patient.last_name}
                      </div>
                      <div className="patient-details">
                        <span className="patient-id">
                          病歷號: {patient.patient_id || patient.medical_record_number || 'N/A'}
                        </span>
                        {patient.date_of_birth && (
                          <span className="patient-birth">
                            生日: {new Date(patient.date_of_birth).toLocaleDateString('zh-TW')}
                          </span>
                        )}
                        {patient.gender && (
                          <span className="patient-gender">
                            性別: {patient.gender === 'M' ? '男' : patient.gender === 'F' ? '女' : '其他'}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {showPatientDropdown && patientSearchTerm.trim().length >= 2 && filteredPatients.length === 0 && !loadingPatients && (
              <div className="patient-dropdown">
                <div className="no-results">
                  未找到符合 "{patientSearchTerm}" 的患者
                </div>
              </div>
            )}
            
            {showPatientDropdown && patientSearchTerm.trim().length > 0 && patientSearchTerm.trim().length < 2 && (
              <div className="patient-dropdown">
                <div className="search-hint">
                  請輸入至少2個字符進行搜尋
                </div>
              </div>
            )}
          </div>
          
          {selectedPatientInfo && (
            <div className="selected-patient-info">
              <h4>已選擇患者:</h4>
              <div className="patient-card">
                <div className="patient-basic-info">
                  <span className="patient-name-display">
                    {selectedPatientInfo.first_name} {selectedPatientInfo.last_name}
                  </span>
                  <span className="patient-id-display">
                    ({selectedPatientInfo.patient_id || selectedPatientInfo.medical_record_number || selectedPatientInfo.id})
                  </span>
                </div>
                {selectedPatientInfo.date_of_birth && (
                  <div className="patient-meta">
                    生日: {new Date(selectedPatientInfo.date_of_birth).toLocaleDateString('zh-TW')}
                    {selectedPatientInfo.gender && (
                      <span className="gender-info">
                        ，性別: {selectedPatientInfo.gender === 'M' ? '男' : selectedPatientInfo.gender === 'F' ? '女' : '其他'}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {selectedPatient && (
          <div className="form-group">
            <label htmlFor="screening-select">選擇健康檢查記錄:</label>
            <select
              id="screening-select"
              value={selectedScreening}
              onChange={(e) => setSelectedScreening(e.target.value)}
              className="screening-select"
            >
              <option value="">請選擇檢查記錄</option>
              {healthScreenings.map(screening => (
                <option key={screening.id} value={screening.id}>
                  {formatDate(screening.screening_date)} - {screening.screening_type}
                </option>
              ))}
            </select>
          </div>
        )}

        <button 
          onClick={calculateRisk}
          disabled={!selectedScreening || loading}
          className="calculate-btn"
        >
          {loading ? '計算中...' : '開始風險分析'}
        </button>
      </div>

      {/* 風險分析結果 */}
      {riskData && (
        <div className="risk-analysis-results">
          {/* 風險總覽儀表板 */}
          <div className="risk-dashboard">
            <h3>風險評估總覽</h3>
            <div className="dashboard-grid">
              {riskData.aha_prevent && (
                <>
                  <div className="dashboard-card">
                    <div className="risk-label">心血管疾病 (10年)</div>
                    <div className="risk-value">{riskData.aha_prevent.cvd_10_year.risk_percentage}%</div>
                    <div className="risk-algorithm">AHA PREVENT</div>
                  </div>
                  <div className="dashboard-card">
                    <div className="risk-label">動脈硬化性心血管疾病 (10年)</div>
                    <div className="risk-value">{riskData.aha_prevent.ascvd_10_year.risk_percentage}%</div>
                    <div className="risk-algorithm">AHA PREVENT</div>
                  </div>
                  <div className="dashboard-card">
                    <div className="risk-label">心臟衰竭 (10年)</div>
                    <div className="risk-value">{riskData.aha_prevent.heart_failure_10_year.risk_percentage}%</div>
                    <div className="risk-algorithm">AHA PREVENT</div>
                  </div>
                </>
              )}
              {riskData.framingham_diabetes && (
                <div className="dashboard-card">
                  <div className="risk-label">糖尿病 (8年)</div>
                  <div className="risk-value">{riskData.framingham_diabetes.diabetes_risk.risk_percentage}</div>
                  <div className="risk-algorithm">Framingham</div>
                </div>
              )}
              {riskData.chinese_health_diabetes && (
                <div className="dashboard-card">
                  <div className="risk-label">糖尿病 (中國健檢)</div>
                  <div className="risk-value">{riskData.chinese_health_diabetes.diabetes_risk.risk_percentage}</div>
                  <div className="risk-algorithm">CH_DM</div>
                </div>
              )}
            </div>
          </div>

          {/* 患者基本資訊表格 */}
          <div className="patient-summary">
            <h3>患者基本資訊</h3>
            <table className="info-table">
              <tbody>
                <tr>
                  <td className="label">年齡</td>
                  <td className="value">{riskData.patient_info.age} 歲</td>
                  <td className="label">性別</td>
                  <td className="value">{riskData.patient_info.gender}</td>
                </tr>
                <tr>
                  <td className="label">BMI</td>
                  <td className="value">{riskData.patient_info.bmi}</td>
                  <td className="label">eGFR</td>
                  <td className="value">{riskData.patient_info.egfr} mL/min/1.73m²</td>
                </tr>
                <tr>
                  <td className="label">總膽固醇</td>
                  <td className="value">{riskData.patient_info.total_cholesterol} mg/dL</td>
                  <td className="label">HDL膽固醇</td>
                  <td className="value">{riskData.patient_info.hdl_cholesterol} mg/dL</td>
                </tr>
                <tr>
                  <td className="label">收縮壓</td>
                  <td className="value">{riskData.patient_info.systolic_bp} mmHg</td>
                  <td className="label">舒張壓</td>
                  <td className="value">{riskData.patient_info.diastolic_bp} mmHg</td>
                </tr>
                <tr>
                  <td className="label">糖尿病</td>
                  <td className="value">{riskData.patient_info.has_diabetes ? '是' : '否'}</td>
                  <td className="label">吸菸</td>
                  <td className="value">{riskData.patient_info.is_smoker ? '是' : '否'}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* AHA PREVENT 風險分析結果 */}
          {riskData.aha_prevent && (
            <div className="risk-section">
              <h3>AHA PREVENT 心血管風險評估</h3>
              <table className="risk-table">
                <thead>
                  <tr>
                    <th>風險類型</th>
                    <th>時間範圍</th>
                    <th>風險百分比</th>
                    <th>演算法</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>心血管疾病</td>
                    <td>10年</td>
                    <td className="risk-percentage">{riskData.aha_prevent.cvd_10_year.risk_percentage}%</td>
                    <td>AHA PREVENT</td>
                  </tr>
                  <tr>
                    <td>動脈硬化性心血管疾病</td>
                    <td>10年</td>
                    <td className="risk-percentage">{riskData.aha_prevent.ascvd_10_year.risk_percentage}%</td>
                    <td>AHA PREVENT</td>
                  </tr>
                  <tr>
                    <td>心臟衰竭</td>
                    <td>10年</td>
                    <td className="risk-percentage">{riskData.aha_prevent.heart_failure_10_year.risk_percentage}%</td>
                    <td>AHA PREVENT</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Framingham Heart Study 糖尿病風險分析結果 */}
          {riskData.framingham_diabetes && (
            <div className="risk-section">
              <h3>Framingham Heart Study 糖尿病風險評估</h3>
              <table className="risk-table">
                <thead>
                  <tr>
                    <th>風險類型</th>
                    <th>時間範圍</th>
                    <th>風險百分比</th>
                    <th>演算法</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>糖尿病發病風險</td>
                    <td>8年</td>
                    <td className="risk-percentage">{riskData.framingham_diabetes.diabetes_risk.risk_percentage}</td>
                    <td>Framingham</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* CH_DM 中國健檢糖尿病風險分析結果 */}
          {riskData.chinese_health_diabetes && (
            <div className="risk-section">
              <h3>CH_DM 中國健檢糖尿病風險評估</h3>
              <table className="risk-table">
                <thead>
                  <tr>
                    <th>風險類型</th>
                    <th>時間範圍</th>
                    <th>風險百分比</th>
                    <th>演算法</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>糖尿病新發病風險</td>
                    <td>糖尿病新發病風險</td>
                    <td className="risk-percentage">{riskData.chinese_health_diabetes.diabetes_risk.risk_percentage}</td>
                    <td>CH_DM</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* 報告操作 */}
          <div className="report-actions">
            <button className="action-btn primary" onClick={() => window.print()}>
              列印報告
            </button>
            <button className="action-btn secondary">
              匯出報告
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default RiskAnalysis;