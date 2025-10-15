import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { checkAuthStatus } from '../utils/auth';

function ProtectedRoute({ children }) {
  const [isChecking, setIsChecking] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const checkAuth = () => {
      console.log('ProtectedRoute: 檢查認證狀態');
      
      const authResult = checkAuthStatus();
      
      console.log('ProtectedRoute auth result:', authResult);
      
      if (authResult.isAuthenticated) {
        console.log('ProtectedRoute: 認證通過');
        setIsAuthenticated(true);
      } else {
        console.log('ProtectedRoute: 認證失敗', authResult.reason);
        setIsAuthenticated(false);
      }
      setIsChecking(false);
    };

    // 初始檢查
    checkAuth();
    
    // 監聽認證狀態變更事件
    const handleAuthChange = (event) => {
      console.log('ProtectedRoute: 收到認證狀態變更事件', event.detail);
      
      if (event.detail.isAuthenticated) {
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
      }
      setIsChecking(false);
    };
    
    // 監聽會話登出事件
    const handleSessionLogout = () => {
      console.log('ProtectedRoute: 收到會話登出事件');
      setIsAuthenticated(false);
      setIsChecking(false);
    };
    
    window.addEventListener('auth-change', handleAuthChange);
    window.addEventListener('session-logout', handleSessionLogout);
    
    return () => {
      window.removeEventListener('auth-change', handleAuthChange);
      window.removeEventListener('session-logout', handleSessionLogout);
    };
  }, []);

  if (isChecking) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '200px',
        fontSize: '16px',
        color: '#666'
      }}>
        <div>
          <div style={{ marginBottom: '10px' }}>🔐</div>
          檢查認證狀態...
        </div>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    console.log('ProtectedRoute: 未認證，重定向到登入頁');
    return <Navigate to="/login" replace />;
  }
  
  return children;
}

export default ProtectedRoute;