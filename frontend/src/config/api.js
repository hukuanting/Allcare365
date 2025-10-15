// API 配置文件
const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  ENDPOINTS: {
    // 認證相關
    LOGIN: '/api/auth/login/',
    REGISTER: '/api/auth/register/',
    LOGOUT: '/api/auth/logout/',
    PROFILE: '/api/auth/profile/',
    TOKEN_REFRESH: '/api/auth/token/refresh/',
    
    // 健康檢查數據
    HEALTH_SCREENING: '/api/health-screening/screenings/',
    PARSE_FILE: '/api/health-screening/parse-file/',
    BULK_IMPORT: '/api/health-screening/bulk-import/',
    RISK_ANALYSIS: '/api/health-screening/risk-analysis/',
    
    // 患者管理
    PATIENTS: '/api/patients/',
    
    // 醫療記錄
    MEDICAL_RECORDS: '/api/medical-records/',
    
    // 報告
    REPORTS: '/api/reports/',
  }
};

// API 請求工具函數
export const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_CONFIG.BASE_URL}${endpoint}`;
  const token = localStorage.getItem('access_token');
  
  console.log('API Request:', {
    url,
    hasToken: !!token,
    tokenLength: token ? token.length : 0,
    method: options.method || 'GET'
  });
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
    },
  };
  
  const mergedOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, mergedOptions);
    
    console.log('API Response:', {
      url,
      status: response.status,
      statusText: response.statusText,
      ok: response.ok
    });
    
    // 處理 401 認證錯誤
    if (response.status === 401 && token && !url.includes('/login/')) {
      console.error('認證失敗 - 401 Unauthorized:', url);
      console.log('當前 token:', token.substring(0, 20) + '...');
      
      // 嘗試刷新 token
      const refreshSuccess = await refreshToken();
      if (refreshSuccess) {
        console.log('Token 刷新成功，重試請求');
        // 重新獲取新的 token 並重試請求
        const newToken = localStorage.getItem('access_token');
        const retryOptions = {
          ...mergedOptions,
          headers: {
            ...mergedOptions.headers,
            'Authorization': `Bearer ${newToken}`
          }
        };
        return await fetch(url, retryOptions);
      } else {
        console.log('Token 刷新失敗，需要重新登入');
        // 觸發登出事件
        window.dispatchEvent(new CustomEvent('session-logout', {
          detail: { reason: 'token_refresh_failed' }
        }));
      }
    }
    
    return response;
  } catch (error) {
    console.error('API 請求錯誤:', error);
    throw error;
  }
};

// Token 刷新函數
const refreshToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) {
    console.log('沒有 refresh token，無法刷新');
    return false;
  }
  
  try {
    console.log('嘗試刷新 token...');
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOKEN_REFRESH}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: refreshToken }),
    });
    
    console.log('Token 刷新回應:', response.status, response.statusText);
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access);
      console.log('Token 刷新成功');
      return true;
    } else {
      const errorData = await response.text();
      console.error('Token 刷新失敗:', response.status, errorData);
      
      // 如果是 token 無效，清除所有認證資料
      if (response.status === 401 || errorData.includes('token not valid')) {
        console.log('Token 已失效，清除認證資料');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_info');
      }
      return false;
    }
  } catch (error) {
    console.error('Token 刷新錯誤:', error);
    return false;
  }
};

// 便捷的 API 方法
export const api = {
  // GET 請求
  get: (endpoint, options = {}) => 
    apiRequest(endpoint, { method: 'GET', ...options }),
  
  // POST 請求
  post: (endpoint, data, options = {}) => 
    apiRequest(endpoint, { 
      method: 'POST', 
      body: JSON.stringify(data), 
      ...options 
    }),
  
  // PUT 請求
  put: (endpoint, data, options = {}) => 
    apiRequest(endpoint, { 
      method: 'PUT', 
      body: JSON.stringify(data), 
      ...options 
    }),
  
  // DELETE 請求
  delete: (endpoint, options = {}) => 
    apiRequest(endpoint, { method: 'DELETE', ...options }),
  
  // 文件上傳
  upload: (endpoint, formData, options = {}) => {
    const token = localStorage.getItem('access_token');
    return apiRequest(endpoint, {
      method: 'POST',
      body: formData,
      headers: {
        ...(token && { 'Authorization': `Bearer ${token}` }),
        // 不設置 Content-Type，讓瀏覽器自動設置 multipart/form-data
      },
      ...options
    });
  }
};

export default API_CONFIG;