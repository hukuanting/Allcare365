// 認證工具函數
import sessionManager from './sessionManager';

export const isTokenValid = (token) => {
  if (!token) return false;
  
  try {
    // 解析 JWT token
    const payload = JSON.parse(atob(token.split('.')[1]));
    const currentTime = Date.now() / 1000;
    
    console.log('Token validation:', {
      exp: payload.exp,
      currentTime: currentTime,
      isValid: payload.exp > currentTime,
      timeUntilExpiry: payload.exp - currentTime
    });
    
    // 檢查是否過期
    return payload.exp > currentTime;
  } catch (error) {
    console.error('Token validation error:', error);
    return false;
  }
};

export const clearAuthState = (reason = 'manual') => {
  console.log('clearAuthState: 清除認證狀態', { reason });
  
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user_info');
  localStorage.removeItem('active_tabs');
  localStorage.removeItem('allcare365_last_activity');
  
  // 清理sessionStorage
  sessionStorage.clear();
  
  // 觸發認證狀態變更事件
  window.dispatchEvent(new CustomEvent('auth-change', { 
    detail: { isAuthenticated: false, reason } 
  }));
};

export const setAuthState = (data) => {
  localStorage.setItem('access_token', data.access);
  localStorage.setItem('refresh_token', data.refresh || '');
  localStorage.setItem('user_info', JSON.stringify({
    username: data.user.username,
    first_name: data.user.first_name || data.user.username
  }));
  
  // 初始化會話管理
  sessionManager.init();
  
  // 觸發認證狀態變更事件
  window.dispatchEvent(new CustomEvent('auth-change', { 
    detail: { isAuthenticated: true, userInfo: data.user } 
  }));
};

// 檢查認證狀態（增強版）
export const checkAuthStatus = () => {
  const token = localStorage.getItem('access_token');
  const userInfo = localStorage.getItem('user_info');
  
  if (!token || !userInfo) {
    // 如果部分資料存在，清除所有資料避免不一致
    if (token || userInfo) {
      console.log('檢測到不完整的認證資料，清除所有資料');
      clearAuthState('incomplete_data');
    }
    return { isAuthenticated: false, reason: 'missing_credentials' };
  }
  
  if (!isTokenValid(token)) {
    // Token 無效時，檢查是否有 refresh token
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      console.log('Token 過期且沒有 refresh token，清除認證資料');
      clearAuthState('no_refresh_token');
    }
    return { isAuthenticated: false, reason: 'token_expired' };
  }
  
  return { 
    isAuthenticated: true, 
    userInfo: JSON.parse(userInfo),
    token 
  };
};

// 優雅的登出函數
export const performLogout = async (reason = 'manual') => {
  console.log('performLogout: 執行登出', { reason });
  
  try {
    // 如果有refresh token，嘗試通知後端
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken && reason === 'manual') {
      await fetch('http://localhost:8000/api/auth/logout/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({ refresh: refreshToken }),
      }).catch(error => {
        console.warn('登出API調用失敗:', error);
      });
    }
  } catch (error) {
    console.warn('登出過程中發生錯誤:', error);
  } finally {
    // 無論API調用是否成功，都清除本地狀態
    clearAuthState(reason);
  }
};