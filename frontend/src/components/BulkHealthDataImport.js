import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './BulkHealthDataImport.css';

function BulkHealthDataImport() {
  const [file, setFile] = useState(null);
  const [patients, setPatients] = useState([]);
  const [selectedPatients, setSelectedPatients] = useState([]);
  
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [fieldMapping, setFieldMapping] = useState({});
  const [validationErrors, setValidationErrors] = useState([]);
  const [currentStep, setCurrentStep] = useState(1); // 1: 上傳, 2: 預覽, 3: 映射, 4: 結果

  // FHIR 相關狀態
  const [fhirData, setFhirData] = useState('');
  const [fhirFile, setFhirFile] = useState(null);
  const [fhirDragOver, setFhirDragOver] = useState(false);
  const [fhirProcessing, setFhirProcessing] = useState(false);
  const [fhirResult, setFhirResult] = useState(null);
  const [fhirPreview, setFhirPreview] = useState(null);
  const [importMode, setImportMode] = useState('csv'); // 'csv' 或 'fhir'

  useEffect(() => {
    fetchPatients();
  }, []);

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

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    setResult(null);
    setPreviewData(null);
    setCurrentStep(1);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    
    // 檢查檔案類型
    const allowedTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
    if (!allowedTypes.includes(droppedFile.type)) {
      alert('僅支援 CSV 和 Excel 檔案格式');
      return;
    }
    
    setFile(droppedFile);
    setResult(null);
    setPreviewData(null);
    setCurrentStep(1);
  };

  const parseFile = async () => {
    if (!file) {
      alert('請選擇要上傳的檔案');
      return;
    }

    setUploading(true);
    const token = localStorage.getItem('access_token');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/health-screening/parse-file/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setPreviewData(data);
        setCurrentStep(2);
        setupFieldMapping(data.headers);
      } else {
        const errorData = await response.json();
        alert(`檔案解析失敗: ${errorData.detail || '未知錯誤'}`);
      }
    } catch (error) {
      alert(`網路錯誤: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const setupFieldMapping = (headers) => {
    // H2U CSV格式的欄位映射
    const h2uMapping = {
      'patient_id': ['ID'],
      'screening_date': ['CheckDate'],
      'birth_date': ['BirthDate'],
      'gender': ['SEX'],
      'height_cm': ['Height'],
      'weight_kg': ['Weight'],
      'waist_circumference_cm': ['Waist'],
      'pulse_rate_bpm': ['PulseRate'],
      'systolic_bp': ['SBP'],
      'diastolic_bp': ['DBP'],
      'fasting_glucose': ['FPG'],
      'hba1c': ['HbA1C'],
      'wbc_count': ['WBC'],
      'triglycerides': ['TG'],
      'total_cholesterol': ['TC'],
      'hdl_cholesterol': ['HDL'],
      'ldl_cholesterol': ['LDL'],
      'creatinine': ['Creatinine'],
      'neck_circumference': ['Neck'],
      'hip_circumference': ['Hip'],
      'hypertension_treated': ['HQ_BP_Treat'],
      'is_current_smoker': ['HQ_SMOKE'],
      'has_diabetes': ['HQ_Diabetes'],
      'diabetes_treated': ['HQ_Diabetes_Treat'],
      'has_coronary_heart_disease': ['HQ_CHD'],
      'has_arrhythmia': ['HQ_arrhythmia'],
      'hyperlipidemia_treated': ['HQ_low_fat_Treat'],
      'exercise_score': ['HQ_Exercise']
    };

    const mapping = {};
    Object.keys(h2uMapping).forEach(systemField => {
      const possibleHeaders = h2uMapping[systemField];
      const foundHeader = headers.find(header => possibleHeaders.includes(header));
      if (foundHeader) {
        mapping[systemField] = foundHeader;
      }
    });

    setFieldMapping(mapping);
  };

  const handleMappingChange = (systemField, selectedHeader) => {
    setFieldMapping(prev => ({
      ...prev,
      [systemField]: selectedHeader
    }));
  };

  const validateData = () => {
    const errors = [];
    const requiredFields = ['patient_id', 'screening_date'];
    
    requiredFields.forEach(field => {
      if (!fieldMapping[field]) {
        errors.push(`必填欄位 "${field}" 未映射`);
      }
    });
    
    setValidationErrors(errors);
    return errors.length === 0;
  };

  const processImport = async () => {
    if (!validateData()) {
      return;
    }

    setProcessing(true);
    const token = localStorage.getItem('access_token');

    try {
      // 直接使用檔案上傳，讓後端處理CSV解析
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/api/health-screening/bulk-import/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data);
        setCurrentStep(4);
      } else {
        const errorData = await response.json();
        alert(`匯入失敗: ${errorData.error || errorData.detail || '未知錯誤'}`);
      }
    } catch (error) {
      alert(`網路錯誤: ${error.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const resetImport = () => {
    setFile(null);
    setPreviewData(null);
    setFieldMapping({});
    setValidationErrors([]);
    setResult(null);
    setCurrentStep(1);
    // 重置 FHIR 相關狀態
    setFhirData('');
    setFhirFile(null);
    setFhirResult(null);
    setFhirPreview(null);
  };

  // FHIR 相關處理函數
  const handleFhirFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFhirFile(selectedFile);
    setFhirResult(null);
    setFhirPreview(null);
    
    // 讀取檔案內容
    if (selectedFile) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setFhirData(event.target.result);
      };
      reader.readAsText(selectedFile);
    }
  };

  const handleFhirDragOver = (e) => {
    e.preventDefault();
    setFhirDragOver(true);
  };

  const handleFhirDragLeave = (e) => {
    e.preventDefault();
    setFhirDragOver(false);
  };

  const handleFhirDrop = (e) => {
    e.preventDefault();
    setFhirDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    
    // 檢查檔案類型
    const allowedTypes = ['application/json', 'text/xml', 'application/xml'];
    const fileName = droppedFile.name.toLowerCase();
    if (!allowedTypes.includes(droppedFile.type) && !fileName.endsWith('.json') && !fileName.endsWith('.xml')) {
      alert('僅支援 JSON 和 XML 檔案格式');
      return;
    }
    
    setFhirFile(droppedFile);
    setFhirResult(null);
    setFhirPreview(null);
    
    // 讀取檔案內容
    const reader = new FileReader();
    reader.onload = (event) => {
      setFhirData(event.target.result);
    };
    reader.readAsText(droppedFile);
  };

  const previewFhirData = () => {
    if (!fhirData.trim()) {
      alert('請輸入或上傳 FHIR 數據');
      return;
    }

    try {
      let parsedData;
      
      // 嘗試解析 JSON
      if (fhirData.trim().startsWith('{') || fhirData.trim().startsWith('[')) {
        parsedData = JSON.parse(fhirData);
      } else if (fhirData.trim().startsWith('<')) {
        // XML 格式 - 簡單預覽
        parsedData = { resourceType: 'Bundle', format: 'XML' };
      } else {
        throw new Error('無法識別的 FHIR 格式');
      }

      // 分析 FHIR 資源
      const resources = [];
      if (parsedData.resourceType === 'Bundle' && parsedData.entry) {
        parsedData.entry.forEach(entry => {
          if (entry.resource) {
            resources.push({
              resourceType: entry.resource.resourceType,
              id: entry.resource.id,
              data: entry.resource
            });
          }
        });
      } else if (parsedData.resourceType) {
        resources.push({
          resourceType: parsedData.resourceType,
          id: parsedData.id,
          data: parsedData
        });
      }

      setFhirPreview({
        totalResources: resources.length,
        resources: resources,
        patients: resources.filter(r => r.resourceType === 'Patient').length,
        observations: resources.filter(r => r.resourceType === 'Observation').length,
        encounters: resources.filter(r => r.resourceType === 'Encounter').length,
        diagnosticReports: resources.filter(r => r.resourceType === 'DiagnosticReport').length
      });

    } catch (error) {
      alert(`FHIR 數據格式錯誤: ${error.message}`);
    }
  };

  const processFhirImport = async () => {
    if (!fhirData.trim()) {
      alert('請輸入或上傳 FHIR 數據');
      return;
    }

    setFhirProcessing(true);
    const token = localStorage.getItem('access_token');

    try {
      const response = await fetch('http://localhost:8000/api/health-screening/fhir-import/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fhir_data: fhirData.trim().startsWith('<') ? fhirData : JSON.parse(fhirData),
          format: fhirData.trim().startsWith('<') ? 'xml' : 'json'
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setFhirResult(data);
      } else {
        // 檢查回應是否為 JSON 格式
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          alert(`FHIR 匯入失敗: ${errorData.error || errorData.detail || '未知錯誤'}`);
        } else {
          // 如果不是 JSON，可能是 HTML 錯誤頁面
          const errorText = await response.text();
          console.error('Server error:', errorText);
          alert(`FHIR 匯入失敗: HTTP ${response.status} - ${response.statusText}`);
        }
      }
    } catch (error) {
      alert(`網路錯誤: ${error.message}`);
    } finally {
      setFhirProcessing(false);
    }
  };

  const resetFhirImport = () => {
    setFhirData('');
    setFhirFile(null);
    setFhirResult(null);
    setFhirPreview(null);
  };

  const downloadTemplate = () => {
    // H2U CSV格式的範本
    const template = [
      'ID,Source,BirthDate,CheckDate,SEX,Height,Weight,Waist,PulseRate,FPG,HbA1C,WBC,SBP,DBP,TG,TC,HDL,LDL,Creatinine,HQ_BP_Treat,HQ_SMOKE,HQ_Diabetes,HQ_Diabetes_Treat,HQ_CHD,HQ_arrhythmia,HQ_low_fat_Treat,HQ_Exercise,Neck,Hip',
      '1001,H001,1990/1/15,2024/1/15,M,175,70,85,72,95,5.4,6.5,120,80,150,200,50,130,1.0,FALSE,FALSE,FALSE,FALSE,FALSE,FALSE,FALSE,,',
      '1002,H001,1985/6/20,2024/1/16,F,160,55,75,68,88,5.2,5.8,110,75,120,190,60,120,0.8,FALSE,FALSE,FALSE,FALSE,FALSE,FALSE,FALSE,,',
      '1003,H001,1978/3/10,2024/1/17,M,168,80,90,75,102,5.8,7.2,135,85,180,220,45,150,1.1,TRUE,TRUE,FALSE,FALSE,FALSE,FALSE,FALSE,,'
    ].join('\n');
    
    const blob = new Blob([template], { type: 'text/csv;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'H2U_health_data_template.csv';
    link.click();
    window.URL.revokeObjectURL(url);
  };

  const systemFields = [
    { key: 'patient_id', label: '患者ID *', required: true },
    { key: 'screening_date', label: '檢查日期 *', required: true },
    { key: 'birth_date', label: '出生日期', required: false },
    { key: 'gender', label: '性別', required: false },
    { key: 'height_cm', label: '身高 (cm)', required: false },
    { key: 'weight_kg', label: '體重 (kg)', required: false },
    { key: 'waist_circumference_cm', label: '腰圍 (cm)', required: false },
    { key: 'pulse_rate_bpm', label: '脈搏 (次/分)', required: false },
    { key: 'systolic_bp', label: '收縮壓 (mmHg)', required: false },
    { key: 'diastolic_bp', label: '舒張壓 (mmHg)', required: false },
    { key: 'fasting_glucose', label: '空腹血糖 (mg/dL)', required: false },
    { key: 'hba1c', label: '糖化血色素 (%)', required: false },
    { key: 'wbc_count', label: '白血球計數', required: false },
    { key: 'triglycerides', label: '三酸甘油酯 (mg/dL)', required: false },
    { key: 'total_cholesterol', label: '總膽固醇 (mg/dL)', required: false },
    { key: 'hdl_cholesterol', label: 'HDL膽固醇 (mg/dL)', required: false },
    { key: 'ldl_cholesterol', label: 'LDL膽固醇 (mg/dL)', required: false },
    { key: 'creatinine', label: '肌酸酐 (mg/dL)', required: false },
    { key: 'neck_circumference', label: '頸圍 (cm)', required: false },
    { key: 'hip_circumference', label: '臀圍 (cm)', required: false },
    { key: 'hypertension_treated', label: '高血壓治療', required: false },
    { key: 'is_current_smoker', label: '目前吸菸', required: false },
    { key: 'has_diabetes', label: '有糖尿病', required: false },
    { key: 'diabetes_treated', label: '糖尿病治療', required: false },
    { key: 'has_coronary_heart_disease', label: '有冠心病', required: false },
    { key: 'has_arrhythmia', label: '有心律不整', required: false },
    { key: 'hyperlipidemia_treated', label: '高血脂治療', required: false },
    { key: 'exercise_score', label: '運動習慣', required: false }
  ];

  return (
    <div className="bulk-import">
      <div className="page-header">
        <h2>批量健檢資料匯入系統</h2>
        <div className="header-actions">
          <Link to="/dashboard" className="header-btn secondary">
            ← 返回儀表板
          </Link>
          <Link to="/health-data-input" className="header-btn primary">
            單筆資料輸入
          </Link>
        </div>
      </div>
      
      {/* 匯入模式選擇器 */}
      <div className="import-mode-selector">
        <div className="mode-options">
          <button 
            className={`mode-btn ${importMode === 'csv' ? 'active' : ''}`}
            onClick={() => {setImportMode('csv'); resetImport(); resetFhirImport();}}
          >
            📊 CSV/Excel 格式匯入
          </button>
          <button 
            className={`mode-btn ${importMode === 'fhir' ? 'active' : ''}`}
            onClick={() => {setImportMode('fhir'); resetImport(); resetFhirImport();}}
          >
            🏥 FHIR R4 格式匯入
          </button>
        </div>
        <div className="mode-description">
          {importMode === 'csv' ? (
            <p>支援傳統 CSV 和 Excel 格式的健檢數據匯入，適用於醫院現有的數據格式</p>
          ) : (
            <p>支援 FHIR R4 標準格式（JSON/XML），可匯入患者資料、檢驗數據、診斷報告等標準化醫療數據</p>
          )}
        </div>
      </div>
      
      {/* FHIR 匯入區塊 */}
      {importMode === 'fhir' && (
        <div className="fhir-import-section">
          <div className="fhir-header">
            <h3>🏥 FHIR R4 格式數據匯入</h3>
            <p>支援 FHIR R4 標準的 JSON 或 XML 格式數據，可匯入患者資料、檢驗結果、診斷報告等</p>
          </div>

          {/* FHIR 資料輸入方式選擇 */}
          <div className="fhir-input-methods">
            <div className="input-method-tabs">
              <button className="tab-btn active">📝 直接貼上</button>
              <button className="tab-btn">📁 上傳檔案</button>
            </div>

            {/* 文字輸入區域 */}
            <div className="fhir-text-input">
              <label htmlFor="fhir-data">FHIR 數據 (JSON 或 XML 格式):</label>
              <textarea
                id="fhir-data"
                value={fhirData}
                onChange={(e) => setFhirData(e.target.value)}
                placeholder="請貼上 FHIR R4 格式的 JSON 或 XML 數據..."
                className="fhir-textarea"
                rows={15}
              />
            </div>

            {/* 檔案上傳區域 */}
            <div className="fhir-file-input">
              <div 
                className={`fhir-drop-zone ${fhirDragOver ? 'drag-over' : ''}`}
                onDragOver={handleFhirDragOver}
                onDragLeave={handleFhirDragLeave}
                onDrop={handleFhirDrop}
              >
                <div className="drop-content">
                  <div className="drop-icon">🏥</div>
                  <p>拖放 FHIR 檔案到此處或點擊選擇檔案</p>
                  <p className="file-types">支援格式: .json, .xml</p>
                  <input
                    type="file"
                    accept=".json,.xml"
                    onChange={handleFhirFileChange}
                    className="file-input"
                  />
                  {fhirFile && (
                    <div className="file-info">
                      <span className="file-name">📄 {fhirFile.name}</span>
                      <span className="file-size">({(fhirFile.size / 1024).toFixed(1)} KB)</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* FHIR 範例數據 */}
          <div className="fhir-examples">
            <details>
              <summary>📋 查看 FHIR R4 範例格式</summary>
              <div className="example-content">
                <div className="example-tabs">
                  <button className="example-tab active">Patient 範例</button>
                  <button className="example-tab">Observation 範例</button>
                  <button className="example-tab">Bundle 範例</button>
                </div>
                <pre className="example-code">
{`{
  "resourceType": "Patient",
  "id": "example-patient",
  "identifier": [
    {
      "use": "usual",
      "type": {
        "coding": [
          {
            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
            "code": "MR"
          }
        ]
      },
      "value": "P123456"
    }
  ],
  "name": [
    {
      "use": "official",
      "family": "張",
      "given": ["小明"]
    }
  ],
  "gender": "male",
  "birthDate": "1990-01-15"
}`}
                </pre>
              </div>
            </details>
          </div>

          {/* FHIR 預覽和處理 */}
          <div className="fhir-actions">
            <button 
              onClick={previewFhirData}
              disabled={!fhirData.trim()}
              className="preview-btn"
            >
              🔍 預覽數據
            </button>
            <button 
              onClick={processFhirImport}
              disabled={!fhirData.trim() || fhirProcessing}
              className="import-btn"
            >
              {fhirProcessing ? '處理中...' : '🚀 開始匯入'}
            </button>
            <button 
              onClick={resetFhirImport}
              className="reset-btn"
            >
              🔄 重置
            </button>
          </div>

          {/* FHIR 數據預覽 */}
          {fhirPreview && (
            <div className="fhir-preview">
              <h4>📊 FHIR 數據預覽</h4>
              <div className="preview-summary">
                <div className="summary-item">
                  <span className="label">總資源數:</span>
                  <span className="value">{fhirPreview.totalResources}</span>
                </div>
                <div className="summary-item">
                  <span className="label">患者資料:</span>
                  <span className="value">{fhirPreview.patients}</span>
                </div>
                <div className="summary-item">
                  <span className="label">檢驗數據:</span>
                  <span className="value">{fhirPreview.observations}</span>
                </div>
                <div className="summary-item">
                  <span className="label">診斷報告:</span>
                  <span className="value">{fhirPreview.diagnosticReports}</span>
                </div>
              </div>
              
              <div className="resources-list">
                <h5>資源列表:</h5>
                <div className="resource-items">
                  {fhirPreview.resources.slice(0, 10).map((resource, index) => (
                    <div key={index} className="resource-item">
                      <span className="resource-type">{resource.resourceType}</span>
                      <span className="resource-id">{resource.id || '無ID'}</span>
                    </div>
                  ))}
                  {fhirPreview.resources.length > 10 && (
                    <div className="more-resources">... 還有 {fhirPreview.resources.length - 10} 個資源</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* FHIR 匯入結果 */}
          {fhirResult && (
            <div className="fhir-result">
              <h4>✅ FHIR 匯入結果</h4>
              <div className="result-summary">
                <div className="result-card success">
                  <div className="result-number">{fhirResult.success_count || 0}</div>
                  <div className="result-label">成功匯入</div>
                </div>
                <div className="result-card error">
                  <div className="result-number">{fhirResult.error_count || 0}</div>
                  <div className="result-label">匯入失敗</div>
                </div>
                <div className="result-card total">
                  <div className="result-number">{fhirResult.total_count || 0}</div>
                  <div className="result-label">總計處理</div>
                </div>
              </div>

              {fhirResult.created_patients && (
                <div className="created-items">
                  <h5>新增患者: {fhirResult.created_patients}</h5>
                </div>
              )}

              {fhirResult.created_screenings && (
                <div className="created-items">
                  <h5>新增健檢記錄: {fhirResult.created_screenings}</h5>
                </div>
              )}

              {fhirResult.errors && fhirResult.errors.length > 0 && (
                <div className="error-details">
                  <h5>❌ 錯誤詳情:</h5>
                  <div className="error-list">
                    {fhirResult.errors.map((error, index) => (
                      <div key={index} className="error-item">
                        <span className="error-message">{error}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* CSV/Excel 匯入區塊 */}
      {importMode === 'csv' && (
        <>
          {/* 步驟指示器 */}
          <div className="steps-indicator">
            <div className={`step ${currentStep >= 1 ? 'active' : ''} ${currentStep > 1 ? 'completed' : ''}`}>
              <span className="step-number">1</span>
              <span className="step-label">檔案上傳</span>
            </div>
            <div className={`step ${currentStep >= 2 ? 'active' : ''} ${currentStep > 2 ? 'completed' : ''}`}>
              <span className="step-number">2</span>
              <span className="step-label">資料預覽</span>
            </div>
            <div className={`step ${currentStep >= 3 ? 'active' : ''} ${currentStep > 3 ? 'completed' : ''}`}>
              <span className="step-number">3</span>
              <span className="step-label">欄位映射</span>
            </div>
            <div className={`step ${currentStep >= 4 ? 'active' : ''}`}>
              <span className="step-number">4</span>
              <span className="step-label">匯入結果</span>
            </div>
          </div>

      {/* 步驟1: 檔案上傳 */}
      {currentStep === 1 && (
        <div className="upload-section">
          <div className="upload-options">
            <button className="template-btn" onClick={downloadTemplate}>
              📋 下載範本檔案
            </button>
            <div className="format-selector">
              <label>支援格式:</label>
              <span className="supported-formats">CSV, Excel (.xlsx, .xls)</span>
            </div>
          </div>

          <div 
            className={`file-drop-zone ${dragOver ? 'drag-over' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="drop-content">
              <div className="drop-icon">📁</div>
              <p>拖放檔案到此處或點擊選擇檔案</p>
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileChange}
                className="file-input"
              />
              {file && (
                <div className="file-info">
                  <span className="file-name">📄 {file.name}</span>
                  <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                </div>
              )}
            </div>
          </div>

          <div className="upload-actions">
            <button 
              onClick={parseFile}
              disabled={!file || uploading}
              className="parse-btn"
            >
              {uploading ? '解析中...' : '解析檔案'}
            </button>
          </div>
        </div>
      )}

      {/* 步驟2: 資料預覽 */}
      {currentStep === 2 && previewData && (
        <div className="preview-section">
          <h3>資料預覽</h3>
          <div className="preview-info">
            <span>總計: {previewData.row_count} 筆資料</span>
            <span>欄位: {previewData.headers.length} 個</span>
          </div>
          
          <div className="preview-table-container">
            <table className="preview-table">
              <thead>
                <tr>
                  {previewData.headers.map((header, index) => (
                    <th key={index}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewData.sample_data.slice(0, 5).map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {previewData.headers.map((header, colIndex) => (
                      <td key={colIndex}>{row[header] || '-'}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="preview-actions">
            <button onClick={() => setCurrentStep(3)} className="next-btn">
              下一步: 欄位映射
            </button>
            <button onClick={resetImport} className="cancel-btn">
              重新選擇檔案
            </button>
          </div>
        </div>
      )}

      {/* 步驟3: 欄位映射 */}
      {currentStep === 3 && previewData && (
        <div className="mapping-section">
          <h3>欄位映射設定</h3>
          <p className="mapping-description">
            請將系統欄位與您的檔案欄位進行映射。紅色標記為必填欄位。
          </p>
          
          {validationErrors.length > 0 && (
            <div className="validation-errors">
              <h4>⚠️ 驗證錯誤:</h4>
              <ul>
                {validationErrors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="mapping-grid">
            {systemFields.map(field => (
              <div key={field.key} className="mapping-row">
                <label className={`system-field ${field.required ? 'required' : ''}`}>
                  {field.label}
                </label>
                <select
                  value={fieldMapping[field.key] || ''}
                  onChange={(e) => handleMappingChange(field.key, e.target.value)}
                  className="mapping-select"
                >
                  <option value="">-- 請選擇欄位 --</option>
                  {previewData.headers.map(header => (
                    <option key={header} value={header}>{header}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>

          <div className="mapping-actions">
            <button onClick={processImport} disabled={processing} className="import-btn">
              {processing ? '匯入中...' : '開始匯入'}
            </button>
            <button onClick={() => setCurrentStep(2)} className="back-btn">
              上一步
            </button>
            <button onClick={resetImport} className="cancel-btn">
              取消
            </button>
          </div>
        </div>
      )}

      {/* 步驟4: 匯入結果 */}
      {currentStep === 4 && result && (
        <div className="result-section">
          <h3>匯入結果</h3>
          
          <div className="result-summary">
            <div className="result-card success">
              <div className="result-number">{result.success_count}</div>
              <div className="result-label">成功匯入</div>
            </div>
            <div className="result-card error">
              <div className="result-number">{result.error_count}</div>
              <div className="result-label">匯入失敗</div>
            </div>
            <div className="result-card total">
              <div className="result-number">{result.total_count}</div>
              <div className="result-label">總計處理</div>
            </div>
          </div>

          {result.errors && result.errors.length > 0 && (
            <div className="error-details">
              <h4>錯誤詳情:</h4>
              <div className="error-list">
                {result.errors.map((error, index) => (
                  <div key={index} className="error-item">
                    <span className="error-row">第 {error.row} 行:</span>
                    <span className="error-message">{error.error}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="result-actions">
            <button onClick={resetImport} className="new-import-btn">
              重新匯入
            </button>
            <button onClick={() => window.location.href = '/health-data-input'} className="manual-input-btn">
              手動輸入
            </button>
          </div>
        </div>
      )}
        </>
      )}
    </div>
  );
}

export default BulkHealthDataImport;
