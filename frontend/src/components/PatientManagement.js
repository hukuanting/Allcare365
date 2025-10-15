import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../config/api';
import './PatientManagement_Beautiful.css';

function PatientManagement() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [pageCount, setPageCount] = useState(1);
  const [sortKey, setSortKey] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    date_of_birth: '',
    gender: 'M',
    phone: '',
    email: '',
    address: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    insurance_number: '',
    medical_record_number: ''
  });

  const PAGE_SIZE = 25;

  useEffect(() => {
    // 檢查認證狀態
    const token = localStorage.getItem('access_token');
    if (!token) {
      setError('請先登入系統才能訪問患者管理');
      setLoading(false);
      return;
    }
  }, []);

  // 當頁碼或搜尋詞變更時載入數據（含簡單防抖）
  useEffect(() => {
    const t = setTimeout(() => {
      fetchPatients();
    }, 300);
    return () => clearTimeout(t);
  }, [page, searchTerm]);

  const fetchPatients = async () => {
    try {
      setLoading(true);
      setError(''); // 清除之前的錯誤
      
      console.log('fetchPatients: 開始獲取患者列表');
      
      // 檢查服務器是否可達
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超時
      
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(PAGE_SIZE),
        search: searchTerm || ''
      });
      const response = await api.get(`/api/patients/?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      console.log('fetchPatients 響應:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('fetchPatients 數據:', data);
        const list = data.results || data;
        setPatients(list);
        setTotalCount(data.count ?? list.length);
        setPageCount(Math.max(1, Math.ceil((data.count ?? list.length) / PAGE_SIZE)));
        setError(''); // 清除錯誤
      } else {
        const errorText = await response.text();
        console.error('fetchPatients 失敗:', response.status, errorText);
        setError(`獲取患者列表失敗 (${response.status}): ${errorText.substring(0, 100)}...`);
      }
    } catch (error) {
      console.error('fetchPatients 錯誤:', error);
      
      if (error.name === 'AbortError') {
        setError('請求超時，請檢查網路連接或服務器狀態');
      } else if (error.message.includes('Failed to fetch')) {
        setError('無法連接到服務器，請確保後端服務器正在運行 (http://localhost:8000)');
      } else {
        setError(`載入患者資料時發生錯誤: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // 檢查認證狀態
    const token = localStorage.getItem('access_token');
    const userInfo = localStorage.getItem('user_info');
    
    console.log('提交前檢查:', {
      hasToken: !!token,
      hasUserInfo: !!userInfo,
      tokenLength: token ? token.length : 0,
      tokenStart: token ? token.substring(0, 20) : 'N/A'
    });
    
    if (!token) {
      setError('請先登入系統');
      return;
    }
    
    // 檢查 token 格式
    const tokenParts = token.split('.');
    if (tokenParts.length !== 3) {
      setError('Token 格式錯誤，請重新登入');
      console.error('Invalid token format, parts:', tokenParts.length);
      return;
    }
    
    // 檢查 token 是否過期
    try {
      const payload = JSON.parse(atob(tokenParts[1]));
      const isExpired = payload.exp <= Date.now() / 1000;
      console.log('Token 檢查:', {
        exp: payload.exp,
        now: Date.now() / 1000,
        isExpired: isExpired,
        expiresAt: new Date(payload.exp * 1000)
      });
      
      if (isExpired) {
        setError('Token 已過期，請重新登入');
        return;
      }
    } catch (e) {
      setError('Token 解析錯誤，請重新登入');
      console.error('Token parsing error:', e);
      return;
    }
    
    try {
      console.log('提交表單數據:', formData);
      
      // 轉換前端字段名稱到後端字段名稱
      const backendData = {
        first_name: formData.first_name,
        last_name: formData.last_name,
        date_of_birth: formData.date_of_birth,
        gender: formData.gender,
        phone_mobile: formData.phone, // 前端 phone -> 後端 phone_mobile
        email: formData.email,
        address_line1: formData.address, // 前端 address -> 後端 address_line1
        emergency_contact_name: formData.emergency_contact_name,
        emergency_contact_phone: formData.emergency_contact_phone,
        medical_record_number: formData.medical_record_number,
        // 注意：insurance_number 在 Patient 模型中不存在，需要單獨處理
        additional_notes: formData.insurance_number ? `保險號碼: ${formData.insurance_number}` : ''
      };
      
      console.log('轉換後的後端數據:', backendData);
      
      // 手動構建請求，確保 token 正確傳遞
      const url = selectedPatient 
        ? `http://localhost:8000/api/patients/${selectedPatient.id}/`
        : 'http://localhost:8000/api/patients/';
      
      const requestOptions = {
        method: selectedPatient ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          // 完全移除認證 header 用於測試
        },
        body: JSON.stringify(backendData) // 使用轉換後的數據
      };
      
      console.log('請求配置:', {
        url,
        method: requestOptions.method,
        hasAuth: requestOptions.headers.Authorization ? 'YES' : 'NO',
        authHeader: requestOptions.headers.Authorization?.substring(0, 20) + '...'
      });
      
      // 直接使用 fetch 而不是 api 工具
      const response = await fetch(url, requestOptions);
      
      console.log('API 響應狀態:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok
      });

      if (response.ok) {
        const responseData = await response.json();
        console.log('患者創建/更新成功:', responseData);
        
        // 檢查是否有病歷號變更的提示
        if (responseData.medical_record_number && 
            formData.medical_record_number && 
            responseData.medical_record_number !== formData.medical_record_number) {
          alert(`注意：輸入的病歷號已存在，系統已自動生成新病歷號：${responseData.medical_record_number}`);
        }
        
        await fetchPatients();
        setShowAddForm(false);
        setSelectedPatient(null);
        setFormData({
          first_name: '',
          last_name: '',
          date_of_birth: '',
          gender: 'M',
          phone: '',
          email: '',
          address: '',
          emergency_contact_name: '',
          emergency_contact_phone: '',
          insurance_number: '',
          medical_record_number: ''
        });
        setError(''); // 清除錯誤信息
      } else {
        // 嘗試解析錯誤響應
        let errorData;
        const contentType = response.headers.get('content-type');
        
        try {
          if (contentType && contentType.includes('application/json')) {
            errorData = await response.json();
          } else {
            // 如果不是JSON響應，獲取文本內容
            const textResponse = await response.text();
            console.error('非JSON響應:', textResponse);
            setError(`服務器錯誤 (${response.status}): 收到非JSON響應`);
            return;
          }
        } catch (parseError) {
          console.error('解析響應錯誤:', parseError);
          setError(`響應解析錯誤: ${parseError.message}`);
          return;
        }
        
        console.error('API 錯誤響應:', errorData);
        
        if (response.status === 401) {
          setError('認證失敗，請重新登入');
        } else if (response.status === 400 && errorData.medical_record_number) {
          // 特別處理病歷號重複錯誤
          setError('病歷號已存在，請使用其他病歷號或留空讓系統自動生成');
        } else {
          // 格式化錯誤信息
          let errorMessage = '操作失敗：';
          if (typeof errorData === 'object') {
            const errors = [];
            for (const [field, messages] of Object.entries(errorData)) {
              if (Array.isArray(messages)) {
                errors.push(`${field}: ${messages.join(', ')}`);
              } else {
                errors.push(`${field}: ${messages}`);
              }
            }
            errorMessage += errors.join('; ');
          } else {
            errorMessage += JSON.stringify(errorData);
          }
          setError(errorMessage);
        }
      }
    } catch (error) {
      console.error('Submit error:', error);
      
      // 更詳細的錯誤信息
      if (error.name === 'SyntaxError' && error.message.includes('Unexpected token')) {
        setError('服務器響應格式錯誤，可能是服務器內部錯誤。請檢查後端服務狀態。');
      } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
        setError('網絡連接錯誤，請檢查後端服務是否正在運行。');
      } else {
        setError(`提交錯誤: ${error.message}`);
      }
    }
  };

  const handleEdit = (patient) => {
    setSelectedPatient(patient);
    setFormData({
      first_name: patient.first_name || '',
      last_name: patient.last_name || '',
      date_of_birth: patient.date_of_birth || '',
      gender: patient.gender || 'M',
      phone: patient.phone_mobile || patient.phone || '', // 後端 phone_mobile -> 前端 phone
      email: patient.email || '',
      address: patient.address_line1 || patient.address || '', // 後端 address_line1 -> 前端 address
      emergency_contact_name: patient.emergency_contact_name || '',
      emergency_contact_phone: patient.emergency_contact_phone || '',
      insurance_number: patient.insurance_number || '',
      medical_record_number: patient.medical_record_number || ''
    });
    setShowAddForm(true);
  };

  const handleDelete = async (patientId) => {
    if (window.confirm('確定要刪除此患者嗎？此操作無法復原！')) {
      try {
        console.log('刪除患者 ID:', patientId);
        
        // 直接使用 fetch，不使用認證
        const response = await fetch(`http://localhost:8000/api/patients/${patientId}/`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          }
        });
        
        console.log('刪除響應:', {
          status: response.status,
          statusText: response.statusText,
          ok: response.ok
        });
        
        if (response.ok) {
          console.log('患者刪除成功');
          await fetchPatients(); // 重新載入患者列表
          setError(''); // 清除錯誤
        } else {
          const errorText = await response.text();
          console.error('刪除失敗:', response.status, errorText);
          setError(`刪除失敗 (${response.status}): ${errorText}`);
        }
      } catch (error) {
        console.error('刪除錯誤:', error);
        setError(`刪除失敗: ${error.message}`);
      }
    }
  };

  // 後端已提供搜尋與分頁，前端僅作顯示
  const filteredPatients = patients;

  if (loading) {
    return <div className="patient-management"><div className="loading">載入中...</div></div>;
  }

  return (
    <div className="patient-management">
      <div className="page-header">
        <h1>患者管理</h1>
        <p>管理患者基本資料和聯絡信息</p>
      </div>

      {error && (
        <div className="error-message">
          {error}
          {error.includes('請先登入') && (
            <div style={{marginTop: '10px'}}>
              <button 
                onClick={() => window.location.href = '/login'}
                className="btn btn-primary"
              >
                前往登入
              </button>
            </div>
          )}
        </div>
      )}

      <div className="controls">
        <div className="search-box">
          <input
            type="text"
            placeholder="搜尋患者姓名、ID或電話..."
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
          />
        </div>
        <div className="header-actions">
          <button 
            onClick={() => {
              setShowAddForm(true);
              setSelectedPatient(null);
              setFormData({
                first_name: '',
                last_name: '',
                date_of_birth: '',
                gender: 'M',
                phone: '',
                email: '',
                address: '',
                emergency_contact_name: '',
                emergency_contact_phone: '',
                insurance_number: '',
                medical_record_number: ''
              });
            }}
            className="add-patient-btn"
          >
            ➕ 新增患者
          </button>
          
          <button onClick={fetchPatients} className="btn btn-secondary">
            🔄 重新載入
          </button>
        </div>
      </div>

      {showAddForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{selectedPatient ? '編輯患者' : '新增患者'}</h3>
              <button 
                type="button"
                onClick={() => {
                  setShowAddForm(false);
                  setSelectedPatient(null);
                }}
                className="close-btn"
              >
                ×
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="patient-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>姓 *:</label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>名 *:</label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>出生日期 *:</label>
                  <input
                    type="date"
                    value={formData.date_of_birth}
                    onChange={(e) => setFormData({...formData, date_of_birth: e.target.value})}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>性別 *:</label>
                  <select
                    value={formData.gender}
                    onChange={(e) => setFormData({...formData, gender: e.target.value})}
                    required
                  >
                    <option value="">請選擇</option>
                    <option value="M">男性</option>
                    <option value="F">女性</option>
                    <option value="O">其他</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>電話:</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  />
                </div>

                <div className="form-group">
                  <label>電子郵件:</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                  />
                </div>

                <div className="form-group">
                  <label>緊急聯絡人:</label>
                  <input
                    type="text"
                    value={formData.emergency_contact_name}
                    onChange={(e) => setFormData({...formData, emergency_contact_name: e.target.value})}
                  />
                </div>
                <div className="form-group">
                  <label>緊急聯絡電話:</label>
                  <input
                    type="tel"
                    value={formData.emergency_contact_phone}
                    onChange={(e) => setFormData({...formData, emergency_contact_phone: e.target.value})}
                  />
                </div>
                
                <div className="form-group">
                  <label>保險號碼:</label>
                  <input
                    type="text"
                    value={formData.insurance_number}
                    onChange={(e) => setFormData({...formData, insurance_number: e.target.value})}
                  />
                </div>
                
                <div className="form-group">
                  <label>病歷號 (可選):</label>
                  <input
                    type="text"
                    value={formData.medical_record_number}
                    onChange={(e) => setFormData({...formData, medical_record_number: e.target.value})}
                    placeholder="留空將自動生成病歷號"
                  />
                  <small style={{color: '#666', fontSize: '12px', marginTop: '4px', display: 'block'}}>
                    如果輸入的病歷號已存在，系統將自動生成新的病歷號
                  </small>
                </div>
                
                <div className="form-group full-width">
                  <label>地址:</label>
                  <input
                    type="text"
                    value={formData.address}
                    onChange={(e) => setFormData({...formData, address: e.target.value})}
                  />
                </div>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn btn-primary">
                  {selectedPatient ? '更新' : '新增'}
                </button>
                <button 
                  type="button" 
                  onClick={() => {
                    setShowAddForm(false);
                    setSelectedPatient(null);
                  }}
                  className="btn btn-secondary"
                >
                  取消
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="records-summary">
        <div className="summary-card">
          <h3>總患者數</h3>
          <span className="count">{totalCount}</span>
        </div>
      </div>

      <div className="records-list">
        {filteredPatients.length === 0 ? (
          <div className="no-records">
            <p>沒有找到符合條件的患者</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="patients-table">
              <thead>
                <tr>
                  <th>病歷號</th>
                  <th>姓名</th>
                  <th>性別</th>
                  <th>出生日期</th>
                  <th>年齡</th>
                  <th>電話</th>
                  <th>電子郵件</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredPatients.map((patient, index) => {
                  const age = patient.date_of_birth ? Math.floor((new Date() - new Date(patient.date_of_birth)) / (365.25 * 24 * 60 * 60 * 1000)) : null;
                  return (
                    <tr key={patient.id || index}>
                      <td>{patient.medical_record_number || `P${patient.id}`}</td>
                      <td>{patient.last_name}{patient.first_name}</td>
                      <td>{patient.gender === 'M' ? '男' : patient.gender === 'F' ? '女' : '其他'}</td>
                      <td>{patient.date_of_birth || 'N/A'}</td>
                      <td>{age !== null ? `${age} 歲` : 'N/A'}</td>
                      <td>{patient.phone_mobile || patient.phone || 'N/A'}</td>
                      <td>{patient.email || 'N/A'}</td>
                      <td>
                        <div className="action-buttons">
                          <button className="action-btn edit-btn" onClick={() => handleEdit(patient)}>編輯</button>
                          <button className="action-btn" onClick={() => window.alert('查看病歷尚未實作')}>查看</button>
                          <button className="action-btn" onClick={() => window.alert('預約掛號尚未實作')}>預約</button>
                          <button className="action-btn delete-btn" onClick={() => handleDelete(patient.id)}>刪除</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div className="pagination">
              <div className="pagination-info">共 {totalCount} 筆 • 第 {page} / {pageCount} 頁</div>
              <div className="pagination-controls">
                <button className="btn btn-secondary" disabled={page <= 1} onClick={() => setPage(1)}>« 第一頁</button>
                <button className="btn btn-secondary" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>‹ 上一頁</button>
                <button className="btn btn-secondary" disabled={page >= pageCount} onClick={() => setPage(p => Math.min(pageCount, p + 1))}>下一頁 ›</button>
                <button className="btn btn-secondary" disabled={page >= pageCount} onClick={() => setPage(pageCount)}>最後一頁 »</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default PatientManagement;