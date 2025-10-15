import React, { useState, useEffect } from 'react';
import { api } from '../config/api';
import './PharmacyManagement.css';

function PharmacyManagement() {
  const [medications, setMedications] = useState([]);
  const [prescriptions, setPrescriptions] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('medications');
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [message, setMessage] = useState('');

  const [medicationForm, setMedicationForm] = useState({
    name: '',
    generic_name: '',
    brand_name: '',
    dosage_form: 'tablet',
    strength: '',
    unit: 'mg',
    manufacturer: '',
    ndc_number: '',
    price: '',
    stock_quantity: '',
    expiry_date: '',
    description: ''
  });

  const [prescriptionForm, setPrescriptionForm] = useState({
    patient: '',
    medication_name: '',
    dosage: '',
    frequency: '',
    duration: '',
    quantity: '',
    instructions: '',
    prescriber: '',
    date_prescribed: new Date().toISOString().split('T')[0],
    status: 'active'
  });

  useEffect(() => {
    if (activeTab === 'medications') {
      fetchMedications();
    } else {
      fetchPrescriptions();
    }
    fetchPatients();
  }, [activeTab, searchTerm]);

  const fetchMedications = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      
      const response = await api.get(`/api/pharmacy/?${params}`);
      if (response.ok) {
        const data = await response.json();
        setMedications(Array.isArray(data.results) ? data.results : Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error('Failed to fetch medications:', error);
      setMessage('獲取藥品列表失敗');
    } finally {
      setLoading(false);
    }
  };

  const fetchPrescriptions = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      
      const response = await api.get(`/api/pharmacy/prescriptions/?${params}`);
      if (response.ok) {
        const data = await response.json();
        setPrescriptions(Array.isArray(data.results) ? data.results : Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error('Failed to fetch prescriptions:', error);
      setMessage('獲取處方列表失敗');
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

  const handleMedicationSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const url = editingItem 
        ? `/api/pharmacy/${editingItem.id}/`
        : '/api/pharmacy/';
      
      const method = editingItem ? 'PUT' : 'POST';
      
      const response = await api[method.toLowerCase()](url, medicationForm);
      
      if (response.ok) {
        setMessage(editingItem ? '藥品更新成功！' : '藥品新增成功！');
        resetForms();
        fetchMedications();
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

  const handlePrescriptionSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const url = editingItem 
        ? `/api/pharmacy/prescriptions/${editingItem.id}/`
        : '/api/pharmacy/prescriptions/';
      
      const method = editingItem ? 'PUT' : 'POST';
      
      const response = await api[method.toLowerCase()](url, prescriptionForm);
      
      if (response.ok) {
        setMessage(editingItem ? '處方更新成功！' : '處方新增成功！');
        resetForms();
        fetchPrescriptions();
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

  const handleEdit = (item) => {
    setEditingItem(item);
    if (activeTab === 'medications') {
      setMedicationForm({
        name: item.name || '',
        generic_name: item.generic_name || '',
        brand_name: item.brand_name || '',
        dosage_form: item.dosage_form || 'tablet',
        strength: item.strength || '',
        unit: item.unit || 'mg',
        manufacturer: item.manufacturer || '',
        ndc_number: item.ndc_number || '',
        price: item.price || '',
        stock_quantity: item.stock_quantity || '',
        expiry_date: item.expiry_date || '',
        description: item.description || ''
      });
    } else {
      setPrescriptionForm({
        patient: item.patient?.id || '',
        medication_name: item.medication_name || '',
        dosage: item.dosage || '',
        frequency: item.frequency || '',
        duration: item.duration || '',
        quantity: item.quantity || '',
        instructions: item.instructions || '',
        prescriber: item.prescriber || '',
        date_prescribed: item.date_prescribed || '',
        status: item.status || 'active'
      });
    }
    setShowAddForm(true);
  };

  const handleDelete = async (itemId) => {
    if (!window.confirm('確定要刪除此項目嗎？')) return;

    try {
      const url = activeTab === 'medications' 
        ? `/api/pharmacy/${itemId}/`
        : `/api/pharmacy/prescriptions/${itemId}/`;
      
      const response = await api.delete(url);
      if (response.ok) {
        setMessage('刪除成功！');
        if (activeTab === 'medications') {
          fetchMedications();
        } else {
          fetchPrescriptions();
        }
      } else {
        setMessage('刪除失敗');
      }
    } catch (error) {
      setMessage(`刪除錯誤: ${error.message}`);
    }
  };

  const resetForms = () => {
    setMedicationForm({
      name: '',
      generic_name: '',
      brand_name: '',
      dosage_form: 'tablet',
      strength: '',
      unit: 'mg',
      manufacturer: '',
      ndc_number: '',
      price: '',
      stock_quantity: '',
      expiry_date: '',
      description: ''
    });
    setPrescriptionForm({
      patient: '',
      medication_name: '',
      dosage: '',
      frequency: '',
      duration: '',
      quantity: '',
      instructions: '',
      prescriber: '',
      date_prescribed: new Date().toISOString().split('T')[0],
      status: 'active'
    });
    setEditingItem(null);
    setShowAddForm(false);
  };

  const handleMedicationChange = (e) => {
    const { name, value } = e.target;
    setMedicationForm(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handlePrescriptionChange = (e) => {
    const { name, value } = e.target;
    setPrescriptionForm(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const getStatusColor = (status) => {
    const colors = {
      'active': '#27ae60',
      'completed': '#3498db',
      'cancelled': '#e74c3c',
      'expired': '#95a5a6'
    };
    return colors[status] || '#95a5a6';
  };

  const getStatusText = (status) => {
    const texts = {
      'active': '使用中',
      'completed': '已完成',
      'cancelled': '已取消',
      'expired': '已過期'
    };
    return texts[status] || status;
  };

  return (
    <div className="pharmacy-management">
      <div className="page-header">
        <h2>藥房管理系統</h2>
        <div className="header-actions">
          <button 
            onClick={() => setShowAddForm(true)}
            className="btn btn-primary"
          >
            + 新增{activeTab === 'medications' ? '藥品' : '處方'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`alert ${message.includes('成功') ? 'alert-success' : 'alert-error'}`}>
          {message}
        </div>
      )}

      {/* 標籤切換 */}
      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'medications' ? 'active' : ''}`}
          onClick={() => setActiveTab('medications')}
        >
          💊 藥品管理
        </button>
        <button 
          className={`tab ${activeTab === 'prescriptions' ? 'active' : ''}`}
          onClick={() => setActiveTab('prescriptions')}
        >
          📋 處方管理
        </button>
      </div>

      {/* 搜尋區域 */}
      <div className="search-section">
        <div className="search-box">
          <input
            type="text"
            placeholder={`搜尋${activeTab === 'medications' ? '藥品名稱或製造商' : '患者姓名或藥品'}...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
      </div>

      {/* 新增/編輯表單 */}
      {showAddForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{editingItem ? '編輯' : '新增'}{activeTab === 'medications' ? '藥品' : '處方'}</h3>
              <button onClick={resetForms} className="close-btn">×</button>
            </div>
            
            {activeTab === 'medications' ? (
              <form onSubmit={handleMedicationSubmit} className="pharmacy-form">
                <div className="form-grid">
                  <div className="form-group">
                    <label>藥品名稱 *</label>
                    <input
                      type="text"
                      name="name"
                      value={medicationForm.name}
                      onChange={handleMedicationChange}
                      required
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>學名</label>
                    <input
                      type="text"
                      name="generic_name"
                      value={medicationForm.generic_name}
                      onChange={handleMedicationChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>商品名</label>
                    <input
                      type="text"
                      name="brand_name"
                      value={medicationForm.brand_name}
                      onChange={handleMedicationChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>劑型</label>
                    <select
                      name="dosage_form"
                      value={medicationForm.dosage_form}
                      onChange={handleMedicationChange}
                    >
                      <option value="tablet">錠劑</option>
                      <option value="capsule">膠囊</option>
                      <option value="liquid">液劑</option>
                      <option value="injection">注射劑</option>
                      <option value="cream">乳膏</option>
                      <option value="ointment">軟膏</option>
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label>劑量</label>
                    <input
                      type="text"
                      name="strength"
                      value={medicationForm.strength}
                      onChange={handleMedicationChange}
                      placeholder="例: 500"
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>單位</label>
                    <select
                      name="unit"
                      value={medicationForm.unit}
                      onChange={handleMedicationChange}
                    >
                      <option value="mg">mg</option>
                      <option value="g">g</option>
                      <option value="ml">ml</option>
                      <option value="mcg">mcg</option>
                      <option value="IU">IU</option>
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label>製造商</label>
                    <input
                      type="text"
                      name="manufacturer"
                      value={medicationForm.manufacturer}
                      onChange={handleMedicationChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>藥品代碼</label>
                    <input
                      type="text"
                      name="ndc_number"
                      value={medicationForm.ndc_number}
                      onChange={handleMedicationChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>價格</label>
                    <input
                      type="number"
                      name="price"
                      value={medicationForm.price}
                      onChange={handleMedicationChange}
                      step="0.01"
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>庫存數量</label>
                    <input
                      type="number"
                      name="stock_quantity"
                      value={medicationForm.stock_quantity}
                      onChange={handleMedicationChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>有效期限</label>
                    <input
                      type="date"
                      name="expiry_date"
                      value={medicationForm.expiry_date}
                      onChange={handleMedicationChange}
                    />
                  </div>
                  
                  <div className="form-group full-width">
                    <label>說明</label>
                    <textarea
                      name="description"
                      value={medicationForm.description}
                      onChange={handleMedicationChange}
                      rows="3"
                    />
                  </div>
                </div>
                
                <div className="form-actions">
                  <button type="submit" disabled={loading} className="btn btn-primary">
                    {loading ? '處理中...' : (editingItem ? '更新' : '新增')}
                  </button>
                  <button type="button" onClick={resetForms} className="btn btn-secondary">
                    取消
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handlePrescriptionSubmit} className="pharmacy-form">
                <div className="form-grid">
                  <div className="form-group">
                    <label>患者 *</label>
                    <select
                      name="patient"
                      value={prescriptionForm.patient}
                      onChange={handlePrescriptionChange}
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
                    <label>藥品名稱 *</label>
                    <input
                      type="text"
                      name="medication_name"
                      value={prescriptionForm.medication_name}
                      onChange={handlePrescriptionChange}
                      required
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>劑量</label>
                    <input
                      type="text"
                      name="dosage"
                      value={prescriptionForm.dosage}
                      onChange={handlePrescriptionChange}
                      placeholder="例: 500mg"
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>頻率</label>
                    <input
                      type="text"
                      name="frequency"
                      value={prescriptionForm.frequency}
                      onChange={handlePrescriptionChange}
                      placeholder="例: 一日三次"
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>療程</label>
                    <input
                      type="text"
                      name="duration"
                      value={prescriptionForm.duration}
                      onChange={handlePrescriptionChange}
                      placeholder="例: 7天"
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>數量</label>
                    <input
                      type="number"
                      name="quantity"
                      value={prescriptionForm.quantity}
                      onChange={handlePrescriptionChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>開立醫師</label>
                    <input
                      type="text"
                      name="prescriber"
                      value={prescriptionForm.prescriber}
                      onChange={handlePrescriptionChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>開立日期</label>
                    <input
                      type="date"
                      name="date_prescribed"
                      value={prescriptionForm.date_prescribed}
                      onChange={handlePrescriptionChange}
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>狀態</label>
                    <select
                      name="status"
                      value={prescriptionForm.status}
                      onChange={handlePrescriptionChange}
                    >
                      <option value="active">使用中</option>
                      <option value="completed">已完成</option>
                      <option value="cancelled">已取消</option>
                      <option value="expired">已過期</option>
                    </select>
                  </div>
                  
                  <div className="form-group full-width">
                    <label>用藥指示</label>
                    <textarea
                      name="instructions"
                      value={prescriptionForm.instructions}
                      onChange={handlePrescriptionChange}
                      rows="3"
                      placeholder="用藥方法和注意事項"
                    />
                  </div>
                </div>
                
                <div className="form-actions">
                  <button type="submit" disabled={loading} className="btn btn-primary">
                    {loading ? '處理中...' : (editingItem ? '更新' : '新增')}
                  </button>
                  <button type="button" onClick={resetForms} className="btn btn-secondary">
                    取消
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* 內容區域 */}
      <div className="content-container">
        {loading ? (
          <div className="loading">載入中...</div>
        ) : activeTab === 'medications' ? (
          <div className="medications-grid">
            {Array.isArray(medications) && medications.map(medication => (
              <div key={medication.id} className="medication-card">
                <div className="medication-header">
                  <h4>{medication.name}</h4>
                  <div className="stock-info">
                    庫存: {medication.stock_quantity || 0}
                  </div>
                </div>
                
                <div className="medication-body">
                  {medication.generic_name && (
                    <div className="info-row">
                      <span className="label">學名:</span>
                      <span>{medication.generic_name}</span>
                    </div>
                  )}
                  
                  {medication.brand_name && (
                    <div className="info-row">
                      <span className="label">商品名:</span>
                      <span>{medication.brand_name}</span>
                    </div>
                  )}
                  
                  <div className="info-row">
                    <span className="label">劑型:</span>
                    <span>{medication.dosage_form}</span>
                  </div>
                  
                  {medication.strength && (
                    <div className="info-row">
                      <span className="label">劑量:</span>
                      <span>{medication.strength} {medication.unit}</span>
                    </div>
                  )}
                  
                  {medication.manufacturer && (
                    <div className="info-row">
                      <span className="label">製造商:</span>
                      <span>{medication.manufacturer}</span>
                    </div>
                  )}
                  
                  {medication.price && (
                    <div className="info-row">
                      <span className="label">價格:</span>
                      <span>NT$ {medication.price}</span>
                    </div>
                  )}
                  
                  {medication.expiry_date && (
                    <div className="info-row">
                      <span className="label">有效期限:</span>
                      <span>{new Date(medication.expiry_date).toLocaleDateString()}</span>
                    </div>
                  )}
                </div>
                
                <div className="medication-actions">
                  <button 
                    onClick={() => handleEdit(medication)}
                    className="btn btn-sm btn-edit"
                  >
                    編輯
                  </button>
                  <button 
                    onClick={() => handleDelete(medication.id)}
                    className="btn btn-sm btn-delete"
                  >
                    刪除
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="prescriptions-grid">
            {Array.isArray(prescriptions) && prescriptions.map(prescription => (
              <div key={prescription.id} className="prescription-card">
                <div className="prescription-header">
                  <div className="patient-info">
                    <strong>{prescription.patient?.last_name}{prescription.patient?.first_name}</strong>
                  </div>
                  <div 
                    className="prescription-status"
                    style={{ backgroundColor: getStatusColor(prescription.status) }}
                  >
                    {getStatusText(prescription.status)}
                  </div>
                </div>
                
                <div className="prescription-body">
                  <div className="medication-name">
                    <h4>{prescription.medication_name}</h4>
                  </div>
                  
                  {prescription.dosage && (
                    <div className="info-row">
                      <span className="label">劑量:</span>
                      <span>{prescription.dosage}</span>
                    </div>
                  )}
                  
                  {prescription.frequency && (
                    <div className="info-row">
                      <span className="label">頻率:</span>
                      <span>{prescription.frequency}</span>
                    </div>
                  )}
                  
                  {prescription.duration && (
                    <div className="info-row">
                      <span className="label">療程:</span>
                      <span>{prescription.duration}</span>
                    </div>
                  )}
                  
                  {prescription.quantity && (
                    <div className="info-row">
                      <span className="label">數量:</span>
                      <span>{prescription.quantity}</span>
                    </div>
                  )}
                  
                  {prescription.prescriber && (
                    <div className="info-row">
                      <span className="label">開立醫師:</span>
                      <span>{prescription.prescriber}</span>
                    </div>
                  )}
                  
                  {prescription.date_prescribed && (
                    <div className="info-row">
                      <span className="label">開立日期:</span>
                      <span>{new Date(prescription.date_prescribed).toLocaleDateString()}</span>
                    </div>
                  )}
                  
                  {prescription.instructions && (
                    <div className="instructions">
                      <span className="label">用藥指示:</span>
                      <p>{prescription.instructions}</p>
                    </div>
                  )}
                </div>
                
                <div className="prescription-actions">
                  <button 
                    onClick={() => handleEdit(prescription)}
                    className="btn btn-sm btn-edit"
                  >
                    編輯
                  </button>
                  <button 
                    onClick={() => handleDelete(prescription.id)}
                    className="btn btn-sm btn-delete"
                  >
                    刪除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {!loading && ((activeTab === 'medications' && medications.length === 0) || 
                      (activeTab === 'prescriptions' && prescriptions.length === 0)) && (
          <div className="no-results">
            <p>沒有找到{activeTab === 'medications' ? '藥品' : '處方'}記錄</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default PharmacyManagement;