import React, { useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Navigation from './components/Navigation';
import Dashboard from './components/Dashboard';
import Login from './components/Login';
import Register from './components/Register';
import HealthDataInput from './components/HealthDataInput';
import RiskAnalysis from './components/RiskAnalysis';
import BulkHealthDataImport from './components/BulkHealthDataImport';
import HealthRecords from './components/HealthRecords';
import PatientManagement from './components/PatientManagement';
import AppointmentManagement from './components/AppointmentManagement';
import LaboratoryManagement from './components/LaboratoryManagement';
import PharmacyManagement from './components/PharmacyManagement';
import UnifiedManagementCenter from './components/UnifiedManagementCenter';
import ProtectedRoute from './components/ProtectedRoute';
import sessionManager from './utils/sessionManager';
import { checkAuthStatus } from './utils/auth';
import './App.css';
import './components/HomePage.css';

function Home() {
  return (
    <div className="home-page">
      <div className="hero-section">
        <div className="hero-content">
          <h1>智慧健康管理平台</h1>
          <p>您的全方位健康管理夥伴</p>
        </div>
      </div>
      
      <div className="info-section">
        <h2>核心服務</h2>
        <div className="info-cards">
          <div className="card">
            <div className="icon">🏥</div>
            <h3>院所介紹</h3>
            <p>提供專業、溫馨的醫療服務，守護您的健康。</p>
          </div>
          <div className="card">
            <div className="icon">❤️</div>
            <h3>服務項目</h3>
            <p>從預防保健到急症處理，提供全方位的醫療選擇。</p>
          </div>
          <div className="card">
            <div className="icon">🤝</div>
            <h3>合作夥伴</h3>
            <p>與頂尖醫療機構合作，提供最先進的醫療技術。</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  useEffect(() => {
    console.log('App: 應用程序啟動');
    
    // 檢查是否有現有的認證狀態
    const authResult = checkAuthStatus();
    if (authResult.isAuthenticated) {
      console.log('App: 檢測到現有認證狀態，初始化會話管理');
      sessionManager.init();
    }
    
    // 監聽會話登出事件
    const handleSessionLogout = (event) => {
      console.log('App: 收到會話登出事件', event.detail);
      
      // 根據登出原因顯示不同的提示
      if (event.detail.reason === 'browser_close') {
        console.log('App: 瀏覽器關閉導致的登出');
      } else if (event.detail.reason === 'token_refresh_failed') {
        console.log('App: TOKEN刷新失敗導致的登出');
        // 可以在這裡顯示友好的提示信息
      }
    };
    
    window.addEventListener('session-logout', handleSessionLogout);
    
    return () => {
      window.removeEventListener('session-logout', handleSessionLogout);
      // 清理會話管理器
      sessionManager.cleanup();
    };
  }, []);

  return (
    <Router>
      <div className="app">
        <Navigation />
        <main className="main-content">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<Home />} />
            <Route path="/main" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/health-data-input" element={
              <ProtectedRoute>
                <HealthDataInput />
              </ProtectedRoute>
            } />
            <Route path="/bulk-import" element={
              <ProtectedRoute>
                <BulkHealthDataImport />
              </ProtectedRoute>
            } />
            <Route path="/risk-analysis" element={
              <ProtectedRoute>
                <RiskAnalysis />
              </ProtectedRoute>
            } />
            <Route path="/health-records" element={
              <ProtectedRoute>
                <HealthRecords />
              </ProtectedRoute>
            } />
            <Route path="/patients" element={
              <ProtectedRoute>
                <PatientManagement />
              </ProtectedRoute>
            } />
            <Route path="/appointments" element={
              <ProtectedRoute>
                <AppointmentManagement />
              </ProtectedRoute>
            } />
            <Route path="/laboratory" element={
              <ProtectedRoute>
                <LaboratoryManagement />
              </ProtectedRoute>
            } />
            <Route path="/pharmacy" element={
              <ProtectedRoute>
                <PharmacyManagement />
              </ProtectedRoute>
            } />
            <Route path="/management-center" element={
              <ProtectedRoute>
                <UnifiedManagementCenter />
              </ProtectedRoute>
            } />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;