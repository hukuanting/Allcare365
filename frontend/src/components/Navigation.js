import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Navigation.css';

function Navigation() {
  const { isAuthenticated, userInfo, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = async () => {
    console.log('Navigation: 手動登出');
    await logout();
    navigate('/login');
  };

  const isActive = (path) => {
    return location.pathname === path ? 'active' : '';
  };

  return (
    <nav className="main-navigation">
      <div className="nav-container">
        {/* Logo and Brand */}
        <div className="nav-brand">
          <Link to="/" className="brand-link">
            <span className="brand-icon">🏥</span>
            <span className="brand-text">Allcare365</span>
          </Link>
        </div>

        {/* Main Navigation Links - Core Functions Only */}
        <div className="nav-links">
          {isAuthenticated ? (
            <>
              {/* Main Page */}
              <Link to="/main" className={`nav-link ${isActive('/main') || isActive('/dashboard')}`}>
                <span className="nav-icon">🏠</span>
                <span className="nav-text">主頁</span>
              </Link>

              {/* Patient Management */}
              <Link to="/patients" className={`nav-link ${isActive('/patients')}`}>
                <span className="nav-icon">👥</span>
                <span className="nav-text">患者管理</span>
              </Link>

              {/* Appointment Management */}
              <Link to="/appointments" className={`nav-link ${isActive('/appointments')}`}>
                <span className="nav-icon">📅</span>
                <span className="nav-text">預約管理</span>
              </Link>

              {/* Health Data Management */}
              <div className="nav-dropdown">
                <span className="nav-link dropdown-toggle">
                  <span className="nav-icon">📋</span>
                  <span className="nav-text">健康數據</span>
                  <span className="dropdown-arrow">▼</span>
                </span>
                <div className="dropdown-menu">
                  <Link to="/health-data-input" className={`dropdown-item ${isActive('/health-data-input')}`}>
                    ➕ 單筆資料輸入
                  </Link>
                  <Link to="/bulk-import" className={`dropdown-item ${isActive('/bulk-import')}`}>
                    📁 批量資料匯入
                  </Link>
                  <Link to="/health-records" className={`dropdown-item ${isActive('/health-records')}`}>
                    📄 健檢記錄查詢
                  </Link>
                  <Link to="/risk-analysis" className={`dropdown-item ${isActive('/risk-analysis')}`}>
                    ⚠️ 風險分析
                  </Link>
                </div>
              </div>

              {/* Medical Services */}
              <div className="nav-dropdown">
                <span className="nav-link dropdown-toggle">
                  <span className="nav-icon">🏥</span>
                  <span className="nav-text">醫療服務</span>
                  <span className="dropdown-arrow">▼</span>
                </span>
                <div className="dropdown-menu">
                  <Link to="/laboratory" className={`dropdown-item ${isActive('/laboratory')}`}>
                    🧪 檢驗管理
                  </Link>
                  <Link to="/pharmacy" className={`dropdown-item ${isActive('/pharmacy')}`}>
                    💊 藥房管理
                  </Link>
                  <Link to="/management-center" className={`dropdown-item ${isActive('/management-center')}`}>
                    🎛️ 統一管理
                  </Link>
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* User Menu */}
        <div className="nav-user">
          {isAuthenticated ? (
            <div className="user-dropdown">
              <div className="user-info">
                <span className="user-avatar">👤</span>
                <span className="user-name">{userInfo?.first_name || '用戶'}</span>
                <span className="dropdown-arrow">▼</span>
              </div>
              <div className="user-dropdown-menu">
                <Link to="/profile" className="dropdown-item">
                  👤 個人資料
                </Link>
                <Link to="/settings" className="dropdown-item">
                  ⚙️ 系統設定
                </Link>
                <div className="dropdown-divider"></div>
                <Link to="/reports" className="dropdown-item">
                  📊 統計報告
                </Link>
                <Link to="/billing" className="dropdown-item">
                  💰 帳單管理
                </Link>
                <Link to="/documents" className="dropdown-item">
                  📄 文件管理
                </Link>
                <Link to="/help" className="dropdown-item">
                  ❓ 說明文件
                </Link>
                <div className="dropdown-divider"></div>
                <button onClick={handleLogout} className="dropdown-item logout-btn">
                  🚪 登出
                </button>
              </div>
            </div>
          ) : (
            <div className="auth-links">
              <Link to="/login" className={`auth-link login ${isActive('/login')}`}>
                登入
              </Link>
              <Link to="/register" className={`auth-link register ${isActive('/register')}`}>
                註冊
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navigation;
