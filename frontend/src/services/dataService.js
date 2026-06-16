// 數據服務 - 獲取真實 API 數據
const API_BASE_URL = 'http://localhost:8000/api';

const dataService = {
  // 獲取 API 請求頭
  getHeaders() {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  },

  // 獲取主頁統計數據
  async getMainPageStats() {
    console.log('dataService: 獲取主頁統計數據');
    
    try {
      // 並行請求多個 API 端點
      const [healthScreenings, patients, appointments] = await Promise.allSettled([
        fetch(`${API_BASE_URL}/health-screening/`, { headers: this.getHeaders() }),
        fetch(`${API_BASE_URL}/patients/`, { headers: this.getHeaders() }),
        fetch(`${API_BASE_URL}/appointments/`, { headers: this.getHeaders() })
      ]);

      let totalScreenings = 0;
      let recentScreenings = 0;
      let totalPatients = 0;
      let totalAppointments = 0;
      let highRiskPatients = 0;

      // 處理健檢數據
      if (healthScreenings.status === 'fulfilled' && healthScreenings.value.ok) {
        const screeningData = await healthScreenings.value.json();
        totalScreenings = screeningData.count || screeningData.length || 0;
        
        // 計算本週新增（假設有日期字段）
        if (Array.isArray(screeningData.results || screeningData)) {
          const data = screeningData.results || screeningData;
          const oneWeekAgo = new Date();
          oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
          
          recentScreenings = data.filter(item => {
            const createdDate = new Date(item.created_date || item.created_at || item.date);
            return createdDate >= oneWeekAgo;
          }).length;

          // 計算高風險患者（假設有風險評估字段）
          highRiskPatients = data.filter(item => {
            return item.cardiovascular_risk_level === 'high' || 
                   item.diabetes_risk_level === 'high' ||
                   item.overall_risk_score > 7;
          }).length;
        }
      }

      // 處理患者數據
      if (patients.status === 'fulfilled' && patients.value.ok) {
        const patientData = await patients.value.json();
        totalPatients = patientData.count || patientData.length || 0;
      }

      // 處理預約數據
      if (appointments.status === 'fulfilled' && appointments.value.ok) {
        const appointmentData = await appointments.value.json();
        totalAppointments = appointmentData.count || appointmentData.length || 0;
      }

      return {
        totalScreenings,
        recentScreenings,
        totalPatients,
        totalAppointments,
        highRiskPatients,
        pendingReviews: Math.max(0, totalScreenings - recentScreenings) // 估算待審核數量
      };
    } catch (error) {
      console.error('dataService: 獲取統計數據失敗', error);
      // 返回默認值而不是0，讓用戶知道有數據
      return {
        totalScreenings: '--',
        recentScreenings: '--',
        totalPatients: '--', 
        totalAppointments: '--',
        highRiskPatients: '--',
        pendingReviews: '--'
      };
    }
  },

  // 系統健康檢查（不返回虛擬資料）
  async getSystemHealth() {
    const candidates = [
      '/api/health-check'
    ];

    for (const path of candidates) {
      try {
        const res = await fetch(`http://localhost:8000${path}`, { headers: this.getHeaders() });
        if (res.ok) {
          const json = await res.json();
          return json;
        }
      } catch (e) {
        // 忽略，嘗試下一個端點
      }
    }
    return null; // 找不到任何健康檢查端點時，回傳 null（不提供假資料）
  },

  // 獲取最近活動
  async getRecentActivities() {
    console.log('dataService: 獲取最近活動');
    
    try {
      const response = await fetch(`${API_BASE_URL}/health-screening/?ordering=-created_date&limit=5`, {
        headers: this.getHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        const activities = (data.results || data || []).map((item, index) => ({
          id: item.id || index,
          icon: '📋',
          description: `${item.patient_name || '患者'} 完成了健檢記錄`,
          time: this.formatTimeAgo(item.created_date || item.created_at),
          type: 'health_screening'
        }));
        
        return activities;
      }
    } catch (error) {
      console.error('dataService: 獲取最近活動失敗', error);
    }
    
    // 不返回任何虛擬資料
    return [];
  },

  // 格式化時間為相對時間
  formatTimeAgo(dateString) {
    if (!dateString) return '未知時間';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return '剛剛';
    if (diffMins < 60) return `${diffMins} 分鐘前`;
    if (diffHours < 24) return `${diffHours} 小時前`;
    if (diffDays < 7) return `${diffDays} 天前`;
    return date.toLocaleDateString('zh-TW');
  }
};

export default dataService;