import React, { useState, useEffect } from 'react';
import { api } from '../config/api';
import './LaboratoryManagement.css';

function LaboratoryManagement() {
  const [labResults, setLabResults] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingResult, setEditingResult] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [message, setMessage] = useState('');

  const [formData, setFormData] = useState({
    patient: '',
    test_name: '',
    test_category: 'blood',
    result_value: '',
    result_unit: '',
    reference_range: '',
    status: 'pending',
    ordered_date: new Date().toISOString().split('T')[0],
    collected_date: '',
    reported_date: '',
    notes: '',
    abnormal_flag: false,
    critical_flag: false
  });

  useEffect(() => {
    fetchLabResults();
    fetchPatients();
  }, [searchTerm, filterStatus]);

  const fetchLabResults = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (filterStatus !== 'all') params.append('status', filterStatus);
      
      const response = await api.get(`/api/laboratory/?${params}`);
      if (response.ok) {
        const data = await response.json();
        setLabResults(data.results || data);
      }
    } catch (error) {
      console.error('Failed to fetch lab results:', error);
      setMessage('獲取檢驗結果失敗');
    } finally {
      setLoading(false);
    }
  };

  const fetchPatients = async () => {
    try {
      const response = await api.get('/api/patients/');
      if (response.ok) {
        const data = await response.json();
        setPatients(data.results || data);
      }
    } catch (error) {
      console.error('Failed to fetch patients:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const url = editingResult 
        ? `/api/laboratory/${editingResult.id}/`
        : '/api/laboratory/';
      
      const method = editingResult ? 'PUT' : 'POST';
      
      const response = await api[method.toLowerCase()](url, formData);
      
      if (response.ok) {
        setMessage(editingResult ? '檢驗結果更新成功！' : '檢驗結果創建成功！');
        resetForm();
        fetchLabResults();
      } else {
        const errorData = await response.json();
        setMessage(`操作失敗: ${JSON.stringify(errorData)}`);
      }
    } catch (error) {
      setMessage(`網路錯誤: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (result) => {
    setEditingResult(result);
    setFormData({
      patient: result.patient?.id || '',
      test_name: result.test_name || '',
      test_category: result.test_category || 'blood',
      result_value: result.result_value || '',
      result_unit: result.result_unit || '',
      reference_range: result.reference_range || '',
      status: result.status || 'pending',
      ordered_date: result.ordered_date || '',
      collected_date: result.collected_date || '',
      reported_date: result.reported_date || '',
      notes: result.notes || '',
      abnormal_flag: result.abnormal_flag || false,
      critical_flag: result.critical_flag || false
    });
    setShowAddForm(true);
  };

  const handleDelete = async (resultId) => {
    if (!window.confirm('確定要刪除此檢驗結果嗎？')) return;

    try {
      const response = await api.delete(`/api/laboratory/${resultId}/`);
      if (response.ok) {
        setMessage('檢驗結果刪除成功！');
        fetchLabResults();
      } else {
        setMessage('刪除失敗');
      }
    } catch (error) {
      setMessage(`刪除錯誤: ${error.message}`);
    }
  };

  const resetForm = () => {
    setFormData({
      patient: '',
      test_name: '',
      test_category: 'blood',
      result_value: '',
      result_unit: '',
      reference_range: '',
      status: 'pending',
      ordered_date: new Date().toISOString().split('T')[0],
      collected_date: '',
      reported_date: '',
      notes: '',
      abnormal_flag: false,
      critical_flag: false
    });
    setEditingResult(null);
    setShowAddForm(false);
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const getStatusColor = (status) => {
    const colors = {
      'pending': '#f39c12',
      'collected': '#3498db',
      'processing': '#9b59b6',
      'completed': '#27ae60',
      'cancelled': '#e74c3c'
    };
    return colors[status] || '#95a5a6';
  };

  const getStatusText = (status) => {
    const texts = {
      'pending': '待採檢',
      'collected': '已採檢',
      'processing': '檢驗中',
      'completed': '已完成',
      'cancelled': '已取消'
    };
    return texts[status] || status;
  };

  const getCategoryText = (category) => {
    const texts = {
      'blood': '血液檢查',
      'urine': '尿液檢查',
      'biochemistry': '生化檢查',
      'hematology': '血液學',
      'immunology': '免疫學',
      'microbiology': '微生物學',
      'pathology': '病理學'
    };
    return texts[category] || category;
  };

  return (
    <div className="laboratory-management">
      <div className="page-header">
        <h2>檢驗管理系統</h2>
        <div className="header-actions">
          <button 
            onClick={() => setShowAddForm(true)}
            className="btn btn-primary"
          >
            + 新增檢驗
          </button>
        </div>
      </div>

      {message && (
        <div className={`alert ${message.includes('成功') ? 'alert-success' : 'alert-error'}`}>
          {message}
        </div>
      )}

      {/* 篩選區域 */}
      <div className="filter-section">
        <div className="search-box">
          <input
            type="text"
            placeholder="搜尋患者姓名或檢驗項目..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        
        <div className="status-filter">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="filter-select"
          >
            <option value="all">所有狀態</option>
            <option value="pending">待採檢</option>
            <option value="collected">已採檢</option>
            <option value="processing">檢驗中</option>
            <option value="completed">已完成</option>
            <option value="cancelled">已取消</option>
          </select>
        </div>
      </div>

      {/* 新增/編輯表單 */}
      {showAddForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{editingResult ? '編輯檢驗結果' : '新增檢驗'}</h3>
              <button onClick={resetForm} className="close-btn">×</button>
            </div>
            
            <form onSubmit={handleSubmit} className="lab-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>患者 *</label>
                  <select
                    name="patient"
                    value={formData.patient}
                    onChange={handleChange}
                    required
                  >
                    <option value="">請選擇患者</option>
                    {patients.map(patient => (
                      <option key={patient.id} value={patient.id}>
                        {patient.last_name}{patient.first_name}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="form-group">
                  <label>檢驗項目 *</label>
                  <input
                    type="text"
                    name="test_name"
                    value={formData.test_name}
                    onChange={handleChange}
                    placeholder="例: 血糖、膽固醇"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>檢驗類別</label>
                  <select
                    name="test_category"
                    value={formData.test_category}
                    onChange={handleChange}
                  >
                    <option value="blood">血液檢查</option>
                    <option value="urine">尿液檢查</option>
                    <option value="biochemistry">生化檢查</option>
                    <option value="hematology">血液學</option>
                    <option value="immunology">免疫學</option>
                    <option value="microbiology">微生物學</option>
                    <option value="pathology">病理學</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label>檢驗結果</label>
                  <input
                    type="text"
                    name="result_value"
                    value={formData.result_value}
                    onChange={handleChange}
                    placeholder="數值或描述"
                  />
                </div>
                
                <div className="form-group">
                  <label>單位</label>
                  <input
                    type="text"
                    name="result_unit"
                    value={formData.result_unit}
                    onChange={handleChange}
                    placeholder="mg/dL, mmol/L 等"
                  />
                </div>
                
                <div className="form-group">
                  <label>參考範圍</label>
                  <input
                    type="text"
                    name="reference_range"
                    value={formData.reference_range}
                    onChange={handleChange}
                    placeholder="例: 70-100 mg/dL"
                  />
                </div>
                
                <div className="form-group">
                  <label>狀態</label>
                  <select
                    name="status"
                    value={formData.status}
                    onChange={handleChange}
                  >
                    <option value="pending">待採檢</option>
                    <option value="collected">已採檢</option>
                    <option value="processing">檢驗中</option>
                    <option value="completed">已完成</option>
                    <option value="cancelled">已取消</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label>開立日期</label>
                  <input
                    type="date"
                    name="ordered_date"
                    value={formData.ordered_date}
                    onChange={handleChange}
                  />
                </div>
                
                <div className="form-group">
                  <label>採檢日期</label>
                  <input
                    type="date"
                    name="collected_date"
                    value={formData.collected_date}
                    onChange={handleChange}
                  />
                </div>
                
                <div className="form-group">
                  <label>報告日期</label>
                  <input
                    type="date"
                    name="reported_date"
                    value={formData.reported_date}
                    onChange={handleChange}
                  />
                </div>
                
                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      name="abnormal_flag"
                      checked={formData.abnormal_flag}
                      onChange={handleChange}
                    />
                    異常結果
                  </label>
                </div>
                
                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      name="critical_flag"
                      checked={formData.critical_flag}
                      onChange={handleChange}
                    />
                    危急值
                  </label>
                </div>
                
                <div className="form-group full-width">
                  <label>備註</label>
                  <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    rows="3"
                    placeholder="檢驗備註或說明"
                  />
                </div>
              </div>
              
              <div className="form-actions">
                <button type="submit" disabled={loading} className="btn btn-primary">
                  {loading ? '處理中...' : (editingResult ? '更新' : '新增')}
                </button>
                <button type="button" onClick={resetForm} className="btn btn-secondary">
                  取消
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 檢驗結果列表 */}
      <div className="lab-results-container">
        {loading ? (
          <div className="loading">載入中...</div>
        ) : (
          <div className="lab-results-grid">
            {labResults.map(result => (
              <div key={result.id} className="lab-result-card">
                <div className="result-header">
                  <div className="test-info">
                    <h4>{result.test_name}</h4>
                    <span className="test-category">{getCategoryText(result.test_category)}</span>
                  </div>
                  <div 
                    className="result-status"
                    style={{ backgroundColor: getStatusColor(result.status) }}
                  >
                    {getStatusText(result.status)}
                  </div>
                </div>
                
                <div className="result-body">
                  <div className="patient-info">
                    <strong>{result.patient?.last_name}{result.patient?.first_name}</strong>
                  </div>
                  
                  {result.result_value && (
                    <div className="result-value">
                      <span className="label">結果:</span>
                      <span className={`value ${result.abnormal_flag ? 'abnormal' : ''} ${result.critical_flag ? 'critical' : ''}`}>
                        {result.result_value} {result.result_unit}
                      </span>
                    </div>
                  )}
                  
                  {result.reference_range && (
                    <div className="reference-range">
                      <span className="label">參考範圍:</span>
                      <span>{result.reference_range}</span>
                    </div>
                  )}
                  
                  <div className="dates-info">
                    {result.ordered_date && (
                      <div>開立: {new Date(result.ordered_date).toLocaleDateString()}</div>
                    )}
                    {result.collected_date && (
                      <div>採檢: {new Date(result.collected_date).toLocaleDateString()}</div>
                    )}
                    {result.reported_date && (
                      <div>報告: {new Date(result.reported_date).toLocaleDateString()}</div>
                    )}
                  </div>
                  
                  {result.notes && (
                    <div className="result-notes">
                      備註: {result.notes}
                    </div>
                  )}
                  
                  <div className="flags">
                    {result.abnormal_flag && (
                      <span className="flag abnormal">異常</span>
                    )}
                    {result.critical_flag && (
                      <span className="flag critical">危急</span>
                    )}
                  </div>
                </div>
                
                <div className="result-actions">
                  <button 
                    onClick={() => handleEdit(result)}
                    className="btn btn-sm btn-edit"
                  >
                    編輯
                  </button>
                  <button 
                    onClick={() => handleDelete(result.id)}
                    className="btn btn-sm btn-delete"
                  >
                    刪除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {!loading && labResults.length === 0 && (
          <div className="no-results">
            <p>沒有找到檢驗結果</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default LaboratoryManagement;