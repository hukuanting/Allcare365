import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../config/api';
import API_CONFIG from '../config/api';
import { setAuthState, checkAuthStatus } from '../utils/auth';
import './Login.css';

function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  // 檢查是否已經登入
  useEffect(() => {
    const authResult = checkAuthStatus();
    if (authResult.isAuthenticated) {
      console.log('Login: 用戶已登入，重定向到儀表板');
      navigate('/dashboard', { replace: true });
    }
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('正在登入...');
    
    try {
      // 使用配置好的 API
      const response = await api.post(API_CONFIG.ENDPOINTS.LOGIN, {
        username: username,
        password: password
      });

      if (response && response.ok) {
        const data = await response.json();
        console.log('Login successful:', data);
        console.log('Setting localStorage items...');
        
        // 使用統一的認證狀態設置
        setAuthState(data);
        
        console.log('Auth state set, localStorage:', {
          access_token: !!localStorage.getItem('access_token'),
          user_info: !!localStorage.getItem('user_info')
        });
        
        setMessage('登入成功！正在跳轉...');
        
        // 延遲跳轉，確保所有組件都收到狀態更新
        setTimeout(() => {
          console.log('Navigating to dashboard...');
          navigate('/dashboard', { replace: true });
        }, 500);
      } else if (response) {
        const data = await response.json();
        setMessage(`登入失敗: ${data.detail || '無效的憑證'}`);
      } else {
        setMessage('登入失敗: 網絡連接問題');
      }
    } catch (error) {
      console.error('Login error:', error);
      setMessage(`網絡錯誤: ${error.message}`);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h2 className="login-title">Login</h2>
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label className="form-label">Username:</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="form-input"
              placeholder="請輸入您的用戶名"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Password:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="form-input"
              placeholder="請輸入您的密碼"
              required
            />
          </div>
          <button type="submit" className="login-button">登入</button>
        </form>
        
        {message && (
          <div className={`message ${message.includes('成功') ? 'success-message' : 'error-message'}`}>
            {message}
          </div>
        )}
        
        <div className="login-auth-links">
          <p>還沒有帳號？ <Link to="/register">立即註冊</Link></p>
          <p><Link to="/">返回首頁</Link></p>
        </div>
      </div>
    </div>
  );
}

export default Login;
