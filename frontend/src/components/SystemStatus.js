import React, { useState, useEffect } from 'react';
import './SystemStatus.css';

function SystemStatus() {
  const [systemStatus, setSystemStatus] = useState({
    api: { status: 'checking', message: '檢查中...' },
    database: { status: 'checking', message: '檢查中...' },
    authentication: { status: 'checking', message: '檢查中...' }
  });

  useEffect(() => {
    checkSystemStatus();
    // 每30秒檢查一次系統狀態
    const interval = setInterval(checkSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkSystemStatus = async () => {
    const newStatus = { ...systemStatus };

    // 檢查API狀態
    try {
      const response = await fetch('/api/health/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        newStatus.api = { status: 'online', message: 'API服務正常' };
      } else {
        newStatus.api = { status: 'error', message: 'API服務異常' };
      }
    } catch (error) {
      newStatus.api = { status: 'offline', message: 'API服務離線' };
    }

    // 檢查認證狀態
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const response = await fetch('/api/auth/verify/', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          newStatus.authentication = { status: 'online', message: '認證正常' };
        } else {
          newStatus.authentication = { status: 'error', message: '認證過期' };
        }
      } catch (error) {
        newStatus.authentication = { status: 'error', message: '認證檢查失敗' };
      }
    } else {
      newStatus.authentication = { status: 'offline', message: '未登入' };
    }

    // 檢查數據庫狀態（通過API間接檢查）
    try {
      const response = await fetch('/api/patients/?limit=1', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        newStatus.database = { status: 'online', message: '數據庫連接正常' };
      } else if (response.status === 401) {
        newStatus.database = { status: 'warning', message: '需要認證' };
      } else {
        newStatus.database = { status: 'error', message: '數據庫連接異常' };
      }
    } catch (error) {
      newStatus.database = { status: 'offline', message: '數據庫離線' };
    }

    setSystemStatus(newStatus);
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'online': return '🟢';
      case 'warning': return '🟡';
      case 'error': return '🔴';
      case 'offline': return '⚫';
      case 'checking': return '🔄';
      default: return '❓';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return '#4CAF50';
      case 'warning': return '#FF9800';
      case 'error': return '#F44336';
      case 'offline': return '#9E9E9E';
      case 'checking': return '#2196F3';
      default: return '#9E9E9E';
    }
  };

  return (
    <div className="system-status">
      <h3>系統狀態</h3>
      <div className="status-grid">
        {Object.entries(systemStatus).map(([key, value]) => (
          <div key={key} className="status-item">
            <div className="status-indicator">
              <span className="status-icon">{getStatusIcon(value.status)}</span>
              <span 
                className="status-dot"
                style={{ backgroundColor: getStatusColor(value.status) }}
              ></span>
            </div>
            <div className="status-info">
              <span className="status-name">
                {key === 'api' ? 'API服務' : 
                 key === 'database' ? '數據庫' : 
                 key === 'authentication' ? '認證系統' : key}
              </span>
              <span 
                className="status-message"
                style={{ color: getStatusColor(value.status) }}
              >
                {value.message}
              </span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="status-summary">
        <button 
          className="refresh-status-btn"
          onClick={checkSystemStatus}
          title="重新檢查系統狀態"
        >
          🔄 重新檢查
        </button>
        <span className="last-check">
          最後檢查: {new Date().toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}

export default SystemStatus;