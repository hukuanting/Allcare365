import { useState, useEffect } from 'react';
import { checkAuthStatus as checkAuth, performLogout } from '../utils/auth';
import sessionManager from '../utils/sessionManager';

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuthStatus = () => {
    console.log('useAuth: 檢查認證狀態');
    
    const authResult = checkAuth();
    
    console.log('useAuth checkAuthStatus result:', authResult);
    
    if (authResult.isAuthenticated) {
      setIsAuthenticated(true);
      setUserInfo(authResult.userInfo);
    } else {
      setIsAuthenticated(false);
      setUserInfo(null);
      
      // 如果是因為TOKEN過期，顯示友好提示
      if (authResult.reason === 'token_expired') {
        console.log('useAuth: TOKEN已過期');
        // sessionManager會處理過期通知
      }
    }
    setLoading(false);
  };

  const logout = async () => {
    console.log('useAuth: 執行手動登出操作');
    await performLogout('manual');
    setIsAuthenticated(false);
    setUserInfo(null);
  };

  useEffect(() => {
    // 初始檢查
    checkAuthStatus();
    
    // 監聽認證狀態變更事件
    const handleAuthChange = (event) => {
      console.log('useAuth: 收到認證狀態變更事件', event.detail);
      
      if (event.detail.isAuthenticated) {
        setIsAuthenticated(true);
        setUserInfo(event.detail.userInfo);
      } else {
        setIsAuthenticated(false);
        setUserInfo(null);
      }
      setLoading(false);
    };
    
    // 監聽會話登出事件
    const handleSessionLogout = (event) => {
      console.log('useAuth: 收到會話登出事件', event.detail);
      setIsAuthenticated(false);
      setUserInfo(null);
      
      // 如果是因為瀏覽器關閉導致的登出，不需要跳轉
      if (event.detail.reason !== 'browser_close') {
        window.location.href = '/login';
      }
    };
    
    // 監聽TOKEN刷新事件
    const handleTokenRefresh = (event) => {
      console.log('useAuth: TOKEN已刷新', event.detail);
      // TOKEN刷新後重新檢查認證狀態
      checkAuthStatus();
    };
    
    // 監聽localStorage變化（跨標籤頁同步）
    const handleStorageChange = (event) => {
      if (event.key === 'access_token' || event.key === 'user_info') {
        console.log('useAuth: 檢測到認證相關localStorage變化');
        checkAuthStatus();
      }
    };
    
    window.addEventListener('auth-change', handleAuthChange);
    window.addEventListener('session-logout', handleSessionLogout);
    window.addEventListener('token-refreshed', handleTokenRefresh);
    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      window.removeEventListener('auth-change', handleAuthChange);
      window.removeEventListener('session-logout', handleSessionLogout);
      window.removeEventListener('token-refreshed', handleTokenRefresh);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  return {
    isAuthenticated,
    userInfo,
    loading,
    logout,
    checkAuthStatus
  };
}