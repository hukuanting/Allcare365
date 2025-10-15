import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import dataService from '../services/dataService';
import './Dashboard.css';

function Dashboard() {
  const [isLoading, setIsLoading] = useState(true);
  const [userInfo, setUserInfo] = useState(null);
  const [recentActivities, setRecentActivities] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);

  useEffect(() => {
    console.log('主頁: 組件已掛載');
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    
    try {
      // 獲取用戶資訊
      const userData = localStorage.getItem('user_info');
      if (userData) {
        try {
          const parsedUser = JSON.parse(userData);
          setUserInfo(parsedUser);
          console.log('主頁: 用戶資訊載入成功', parsedUser);
        } catch (error) {
          console.error('主頁: 用戶資訊解析失敗', error);
        }
      }

      // 載入最近活動（真實 API）
      const activitiesData = await dataService.getRecentActivities();
      setRecentActivities(Array.isArray(activitiesData) ? activitiesData : []);

      // 載入系統健康狀態（真實 API）
      const health = await dataService.getSystemHealth();
      setSystemHealth(health);

      console.log('主頁: 數據載入完成', { activities: activitiesData, health });
      
    } catch (error) {
      console.error('主頁: 數據載入失敗', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '400px',
        fontSize: '18px'
      }}>
        <div>
          <div>Allcare365 載入中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Allcare365 主頁</h1>
        <p>歡迎 {userInfo?.username || userInfo?.first_name || '用戶'} 回到您的健康管理系統</p>
      </div>

      {/* 首屏大型橫幅（Hero） */}
      <section className="dashboard-hero">
        <div className="hero-content">
          <h2>全方位智慧醫療管理平台</h2>
          <p>以數據為核心，串聯健檢、門診、檢驗、藥局與報告，打造安全、專業且高效率的臨床作業環境。</p>
          <div className="hero-cta">
            <Link to="/health-data-input" className="cta-button primary">開始輸入資料</Link>
            <Link to="/risk-analysis" className="cta-button secondary">查看風險分析</Link>
          </div>
        </div>
      </section>

      <div className="dashboard-main-content">
        {/* 功能導覽（Modules Showcase） */}
        <section className="modules-showcase">
          <h2>功能導覽</h2>
          <div className="modules-grid">
            <Link to="/patients" className="module-tile">
              <div className="tile-content">
                <h3>患者管理</h3>
                <p>病歷摘要、健康資料、就診紀錄</p>
              </div>
            </Link>
            <Link to="/appointments" className="module-tile">
              <div className="tile-content">
                <h3>預約排程</h3>
                <p>門診時段、提醒通知、候補管理</p>
              </div>
            </Link>
            <Link to="/laboratory" className="module-tile">
              <div className="tile-content">
                <h3>檢驗管理</h3>
                <p>檢驗單、結果回傳、異常警示</p>
              </div>
            </Link>
            <Link to="/pharmacy" className="module-tile">
              <div className="tile-content">
                <h3>藥局與處方</h3>
                <p>處方開立、調劑紀錄、庫存管理</p>
              </div>
            </Link>
          </div>
        </section>

        <div className="quick-actions-section">
          <h2>快速操作</h2>
          <div className="quick-actions-grid">
            <Link to="/health-data-input" className="action-card">
              <div className="action-content">
                <h3>單筆資料輸入</h3>
                <p>輸入單一患者的健康檢查數據</p>
              </div>
              <div className="action-arrow">→</div>
            </Link>
            
            <Link to="/bulk-import" className="action-card">
              <div className="action-content">
                <h3>批量資料匯入</h3>
                <p>批量匯入多位患者的健康數據</p>
              </div>
              <div className="action-arrow">→</div>
            </Link>
            
            <Link to="/risk-analysis" className="action-card">
              <div className="action-content">
                <h3>風險分析</h3>
                <p>查看患者的疾病風險評估報告</p>
              </div>
              <div className="action-arrow">→</div>
            </Link>
            
            <Link to="/health-records" className="action-card">
              <div className="action-content">
                <h3>健檢記錄</h3>
                <p>查詢和管理健檢歷史記錄</p>
              </div>
              <div className="action-arrow">→</div>
            </Link>
          </div>
        </div>
      </div>

      {/* 開發者資訊區塊 */}
      <div className="developer-info-section">
        <div className="developer-content">
          <h3>Allcare365 開發人員</h3>
          <div className="info-grid">
            <div className="info-item">
              <h4>地址</h4>
              <p>106台北市大安區芳蘭路49號</p>
            </div>
            <div className="info-item">
              <h4>單位</h4>
              <p>國立台灣大學醫學工程所</p>
            </div>
            <div className="info-item">
              <h4>聯絡電話</h4>
              <p>+886 911485919</p>
            </div>
            <div className="info-item">
              <h4>開發者</h4>
              <p>HU, KUAN TING</p>
            </div>
            <div className="info-item">
              <h4>指導教授</h4>
              <p>林啟萬教授</p>
            </div>
            <div className="info-item">
              <h4>Email</h4>
              <p>hukuanting@gmail.com</p>
            </div>
          </div>
          <div className="developer-footer">
            <p>© 2024 Allcare365. All Rights Reserved.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;