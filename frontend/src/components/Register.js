import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../config/api';
import './Login.css'; // 使用與登入頁面相同的樣式

function Register() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('正在註冊...');

    // 基本驗證
    if (password !== password2) {
      setMessage('密碼不匹配，請重新輸入');
      return;
    }

    if (password.length < 8) {
      setMessage('密碼長度至少需要 8 個字符');
      return;
    }

    try {
      console.log('Attempting registration with:', { username, email: email || `${username}@example.com` });
      
      const response = await api.post('/api/auth/register/', {
        username, 
        password, 
        password2,
        email: email || `${username}@example.com`,
        first_name: '',
        last_name: ''
      });

      console.log('Registration response:', response);

      if (response && response.ok) {
        const data = await response.json();
        console.log('Registration successful:', data);
        setMessage('註冊成功！正在跳轉到登入頁面...');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else if (response) {
        const errorData = await response.json();
        console.error('Registration error:', errorData);
        
        // 處理不同類型的錯誤
        if (errorData.username) {
          setMessage(`註冊失敗: ${errorData.username[0]}`);
        } else if (errorData.password) {
          setMessage(`註冊失敗: ${errorData.password[0]}`);
        } else if (errorData.email) {
          setMessage(`註冊失敗: ${errorData.email[0]}`);
        } else {
          setMessage(`註冊失敗: ${errorData.detail || '未知錯誤'}`);
        }
      } else {
        setMessage('註冊失敗: 網絡連接問題');
      }
    } catch (error) {
      console.error('Registration error:', error);
      setMessage(`註冊錯誤: ${error.message}`);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h2 className="login-title">Register</h2>
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label className="form-label">用戶名 *:</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="form-input"
              placeholder="請輸入用戶名"
              required
              minLength="3"
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">電子郵件:</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="form-input"
              placeholder="選填，如不填寫將自動生成"
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">密碼 *:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="form-input"
              placeholder="至少 8 個字符"
              required
              minLength="8"
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">確認密碼 *:</label>
            <input
              type="password"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
              className="form-input"
              placeholder="請再次輸入密碼"
              required
              minLength="8"
            />
          </div>
          
          <button type="submit" className="login-button">
            註冊帳號
          </button>
        </form>
        
        {message && (
          <div className={`message ${message.includes('成功') ? 'success-message' : 'error-message'}`}>
            {message}
          </div>
        )}
        
        <div className="login-auth-links">
          <p>已有帳號？ <Link to="/login">立即登入</Link></p>
          <p><Link to="/">返回首頁</Link></p>
        </div>
      </div>
    </div>
  );
}

export default Register;
