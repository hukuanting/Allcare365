import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../config/api';
import ModuleQuickAccess from './ModuleQuickAccess';
import EmptyState from './EmptyState';
import dataService from '../services/dataService';
import './UnifiedManagementCenter.css';

function UnifiedManagementCenter() {
  const [activeModule, setActiveModule] = useState('overview');
  const [systemStats, setSystemStats] = useState({
    patients: { total: 0, new: 0, active: 0 },
    screenings: { total: 0, pending: 0, completed: 0 },
    laboratory: { pending: 0, critical: 0, normal: 0 },
    pharmacy: { lowStock: 0, prescriptions: 0, inventory: 0 },
    appointments: { today: 0, upcoming: 0, completed: 0 }
  });
  const [recentActivities, setRecentActivities] = useState([]);
  const navigate = useNavigate();

  // 模組配置
  const modules = [
    {
      id: 'quick-access',
      name: '快速訪問',
      icon: '🚀',
      color: '#E91E63',
      description: '快速找到並訪問所有功能模組',
      route: '/management-center?tab=quick-access',
      features: ['智能搜尋', '分類瀏覽', '快速導航', '功能索引'],
      stats: { total: 12, categories: 6, recent: 3 }
    },
    {
      id: 'patients',
      name: '患者管理',
      icon: '👥',
      color: '#4CAF50',
      description: '管理患者資料、病歷和基本信息',
      route: '/patients',
      features: ['新增患者', '編輯資料', '查看病歷', '搜尋患者'],
      stats: systemStats.patients
    },
    {
      id: 'health-screening',
      name: '健康篩檢',
      icon: '📋',
      color: '#2196F3',
      description: '健康檢查數據輸入和管理',
      route: '/health-data-input',
      features: ['單筆輸入', '批量匯入', '數據驗證', '報告生成'],
      stats: systemStats.screenings
    },
    {
      id: 'laboratory',
      name: '檢驗管理',
      icon: '🧪',
      color: '#FF9800',
      description: '實驗室檢驗結果和報告管理',
      route: '/laboratory',
      features: ['檢驗申請', '結果錄入', '報告審核', '異常追蹤'],
      stats: systemStats.laboratory
    },
    {
      id: 'pharmacy',
      name: '藥房管理',
      icon: '💊',
      color: '#9C27B0',
      description: '藥品庫存、處方和配藥管理',
      route: '/pharmacy',
      features: ['庫存管理', '處方配藥', '藥品查詢', '用藥指導'],
      stats: systemStats.pharmacy
    },
    {
      id: 'appointments',
      name: '預約管理',
      icon: '📅',
      color: '#F44336',
      description: '預約排程和時間管理',
      route: '/appointments',
      features: ['預約排程', '時間管理', '提醒通知', '取消重排'],
      stats: systemStats.appointments
    },
    {
      id: 'risk-analysis',
      name: '風險分析',
      icon: '⚠️',
      color: '#FF5722',
      description: '疾病風險評估和預測分析',
      route: '/risk-analysis',
      features: ['風險計算', '趨勢分析', '預警系統', '建議生成'],
      stats: { high: 5, medium: 12, low: 45 }
    }
  ];

  // 快速操作配置
  const quickActions = [
    {
      title: '新增患者',
      icon: '👤➕',
      action: () => navigate('/patients?action=create'),
      color: '#4CAF50'
    },
    {
      title: '健檢輸入',
      icon: '📋➕',
      action: () => navigate('/health-data-input'),
      color: '#2196F3'
    },
    {
      title: '批量匯入',
      icon: '📁⬆️',
      action: () => navigate('/bulk-import'),
      color: '#FF9800'
    },
    {
      title: '風險分析',
      icon: '📊⚠️',
      action: () => navigate('/risk-analysis'),
      color: '#F44336'
    },
    {
      title: '檢驗申請',
      icon: '🧪➕',
      action: () => navigate('/laboratory?action=create'),
      color: '#9C27B0'
    },
    {
      title: '預約排程',
      icon: '📅➕',
      action: () => navigate('/appointments?action=create'),
      color: '#607D8B'
    }
  ];

  useEffect(() => {
    fetchSystemStats();
    fetchRecentActivities();
  }, []);

  const fetchSystemStats = async () => {
    try {
      // 使用數據服務獲取真實數據
      const stats = await dataService.getSystemStats();
      setSystemStats(stats);
    } catch (error) {
      console.error('Failed to fetch system stats:', error);
      // 設置空狀態
      setSystemStats({
        patients: { total: 0, new: 0, active: 0 },
        screenings: { total: 0, pending: 0, completed: 0 },
        laboratory: { pending: 0, critical: 0, normal: 0 },
        pharmacy: { lowStock: 0, prescriptions: 0, inventory: 0 },
        appointments: { today: 0, upcoming: 0, completed: 0 }
      });
    }
  };

  const fetchRecentActivities = async () => {
    try {
      // 使用數據服務獲取真實數據
      const activities = await dataService.getRecentActivities();
      setRecentActivities(activities);
    } catch (error) {
      console.error('Failed to fetch recent activities:', error);
      setRecentActivities([]);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return '#F44336';
      case 'medium': return '#FF9800';
      default: return '#4CAF50';
    }
  };

  const renderOverview = () => (
    <div className="overview-content">
      {/* 系統概覽 */}
      <div className="system-overview">
        <h2>系統概覽</h2>
        <div className="overview-grid">
          {modules.map(module => (
            <div key={module.id} className="overview-card" style={{ borderColor: module.color }}>
              <div className="overview-header">
                <span className="overview-icon" style={{ color: module.color }}>
                  {module.icon}
                </span>
                <h3>{module.name}</h3>
              </div>
              <div className="overview-stats">
                {Object.entries(module.stats).map(([key, value]) => (
                  <div key={key} className="stat-item">
                    <span className="stat-label">{key}:</span>
                    <span className="stat-value">{value}</span>
                  </div>
                ))}
              </div>
              <Link to={module.route} className="overview-link">
                進入管理 →
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* 快速操作 */}
      <div className="quick-actions-section">
        <h2>快速操作</h2>
        <div className="quick-actions-grid">
          {quickActions.map((action, index) => (
            <button
              key={index}
              className="quick-action-btn"
              onClick={action.action}
              style={{ borderColor: action.color }}
            >
              <span className="action-icon" style={{ color: action.color }}>
                {action.icon}
              </span>
              <span className="action-title">{action.title}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 最近活動 */}
      <div className="recent-activities">
        <h2>最近活動</h2>
        <div className="activities-list">
          {recentActivities.length > 0 ? (
            recentActivities.map(activity => (
              <div key={activity.id} className="activity-item">
                <div 
                  className="activity-icon"
                  style={{ backgroundColor: getPriorityColor(activity.priority) }}
                >
                  {activity.icon}
                </div>
                <div className="activity-content">
                  <h4>{activity.title}</h4>
                  <p>{activity.description}</p>
                  <span className="activity-time">{activity.time}</span>
                </div>
                <div className={`priority-indicator ${activity.priority}`}>
                  {activity.priority === 'high' ? '🔴' : 
                   activity.priority === 'medium' ? '🟡' : '🟢'}
                </div>
              </div>
            ))
          ) : (
            <EmptyState
              icon="📊"
              title="暫無系統活動"
              description="系統活動記錄會在您使用各項功能時自動生成。"
              actionText="開始使用系統"
              onAction={() => navigate('/health-data-input')}
            />
          )}
        </div>
      </div>
    </div>
  );

  const renderModuleDetail = (moduleId) => {
    const module = modules.find(m => m.id === moduleId);
    if (!module) return null;

    // 特殊處理快速訪問模組
    if (moduleId === 'quick-access') {
      return <ModuleQuickAccess />;
    }

    return (
      <div className="module-detail">
        <div className="module-header">
          <div className="module-title">
            <span className="module-icon" style={{ color: module.color }}>
              {module.icon}
            </span>
            <h2>{module.name}</h2>
          </div>
          <Link to={module.route} className="enter-module-btn">
            進入完整管理界面
          </Link>
        </div>
        
        <div className="module-description">
          <p>{module.description}</p>
        </div>

        <div className="module-features">
          <h3>主要功能</h3>
          <div className="features-grid">
            {module.features.map((feature, index) => (
              <div key={index} className="feature-item">
                <span className="feature-icon">✓</span>
                <span>{feature}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="module-stats-detail">
          <h3>統計數據</h3>
          <div className="stats-cards">
            {Object.entries(module.stats).map(([key, value]) => (
              <div key={key} className="stat-card">
                <div className="stat-number">{value}</div>
                <div className="stat-label">{key}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="unified-management-center">
      <div className="management-header">
        <h1>Allcare365 統一管理中心</h1>
        <p>集中管理所有醫療模組，提供完整的系統操作界面</p>
      </div>

      <div className="management-navigation">
        <button
          className={`nav-btn ${activeModule === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveModule('overview')}
        >
          📊 系統概覽
        </button>
        {modules.map(module => (
          <button
            key={module.id}
            className={`nav-btn ${activeModule === module.id ? 'active' : ''}`}
            onClick={() => setActiveModule(module.id)}
          >
            {module.icon} {module.name}
          </button>
        ))}
      </div>

      <div className="management-content">
        {activeModule === 'overview' ? renderOverview() : renderModuleDetail(activeModule)}
      </div>
    </div>
  );
}

export default UnifiedManagementCenter;