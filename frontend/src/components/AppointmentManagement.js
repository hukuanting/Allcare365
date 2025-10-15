import React from 'react';
import './AppointmentManagement.css';

function AppointmentManagement() {
  return (
    <div className="appointment-management">
      <div className="development-notice">
        <div className="notice-card">
          <div className="notice-icon">🚧</div>
          <div className="notice-content">
            <h2>預約管理系統</h2>
            <h3>功能開發中</h3>
            <p>此功能目前正在開發和優化中，暫時無法使用。</p>
            <div className="notice-details">
              <h4>即將推出的功能：</h4>
              <ul>
                <li>📅 預約排程管理</li>
                <li>👥 患者預約查詢</li>
                <li>⏰ 預約提醒通知</li>
                <li>📊 預約統計報表</li>
                <li>🔄 預約狀態更新</li>
              </ul>
            </div>
            <div className="notice-actions">
              <button 
                onClick={() => window.history.back()} 
                className="btn btn-primary"
              >
                返回上一頁
              </button>
              <button 
                onClick={() => window.location.href = '/main'} 
                className="btn btn-secondary"
              >
                回到主頁
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AppointmentManagement;