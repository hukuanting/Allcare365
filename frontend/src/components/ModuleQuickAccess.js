import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './ModuleQuickAccess.css';

function ModuleQuickAccess() {
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();

  // 所有可用的功能模組
  const allModules = [
    // 患者管理相關
    {
      id: 'patient-list',
      title: '患者列表',
      description: '查看和管理所有患者資料',
      icon: '👥',
      category: '患者管理',
      route: '/patients',
      keywords: ['患者', '病人', '列表', '管理']
    },
    {
      id: 'patient-add',
      title: '新增患者',
      description: '註冊新的患者資料',
      icon: '👤➕',
      category: '患者管理',
      route: '/patients?action=create',
      keywords: ['新增', '註冊', '患者', '病人']
    },
    
    // 健康篩檢相關
    {
      id: 'health-input',
      title: '健檢數據輸入',
      description: '單筆輸入患者健康檢查數據',
      icon: '📋',
      category: '健康篩檢',
      route: '/health-data-input',
      keywords: ['健檢', '輸入', '數據', '檢查']
    },
    {
      id: 'bulk-import',
      title: '批量數據匯入',
      description: '批量匯入Excel或CSV健檢數據',
      icon: '📁',
      category: '健康篩檢',
      route: '/bulk-import',
      keywords: ['批量', '匯入', 'excel', 'csv', '大量']
    },
    {
      id: 'health-records',
      title: '健檢記錄查詢',
      description: '查詢和管理歷史健檢記錄',
      icon: '📄',
      category: '健康篩檢',
      route: '/health-records',
      keywords: ['記錄', '查詢', '歷史', '健檢']
    },
    
    // 風險分析相關
    {
      id: 'risk-analysis',
      title: '疾病風險分析',
      description: '查看患者疾病風險評估報告',
      icon: '⚠️',
      category: '風險分析',
      route: '/risk-analysis',
      keywords: ['風險', '分析', '疾病', '評估', '報告']
    },
    
    // 實驗室管理
    {
      id: 'lab-management',
      title: '檢驗管理',
      description: '管理實驗室檢驗申請和結果',
      icon: '🧪',
      category: '實驗室',
      route: '/laboratory',
      keywords: ['檢驗', '實驗室', '化驗', '報告']
    },
    {
      id: 'lab-results',
      title: '檢驗結果',
      description: '查看和管理檢驗結果',
      icon: '📊',
      category: '實驗室',
      route: '/laboratory?tab=results',
      keywords: ['結果', '檢驗', '報告', '數值']
    },
    
    // 藥房管理
    {
      id: 'pharmacy',
      title: '藥房管理',
      description: '管理藥品庫存和處方',
      icon: '💊',
      category: '藥房',
      route: '/pharmacy',
      keywords: ['藥房', '藥品', '庫存', '處方']
    },
    {
      id: 'prescriptions',
      title: '處方管理',
      description: '開立和管理患者處方',
      icon: '📝',
      category: '藥房',
      route: '/pharmacy?tab=prescriptions',
      keywords: ['處方', '開藥', '用藥', '藥物']
    },
    
    // 預約管理
    {
      id: 'appointments',
      title: '預約管理',
      description: '管理患者預約和排程',
      icon: '📅',
      category: '預約',
      route: '/appointments',
      keywords: ['預約', '排程', '時間', '約診']
    },
    {
      id: 'appointment-calendar',
      title: '預約日曆',
      description: '查看預約日曆和時間安排',
      icon: '🗓️',
      category: '預約',
      route: '/appointments?view=calendar',
      keywords: ['日曆', '預約', '時間表', '排程']
    }
  ];

  // 篩選模組
  const filteredModules = allModules.filter(module =>
    module.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    module.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    module.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
    module.keywords.some(keyword => keyword.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // 按類別分組
  const groupedModules = filteredModules.reduce((groups, module) => {
    const category = module.category;
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(module);
    return groups;
  }, {});

  const handleModuleClick = (route) => {
    navigate(route);
  };

  const getCategoryIcon = (category) => {
    const icons = {
      '患者管理': '👥',
      '健康篩檢': '📋',
      '風險分析': '⚠️',
      '實驗室': '🧪',
      '藥房': '💊',
      '預約': '📅'
    };
    return icons[category] || '📁';
  };

  const getCategoryColor = (category) => {
    const colors = {
      '患者管理': '#4CAF50',
      '健康篩檢': '#2196F3',
      '風險分析': '#FF5722',
      '實驗室': '#FF9800',
      '藥房': '#9C27B0',
      '預約': '#F44336'
    };
    return colors[category] || '#607D8B';
  };

  return (
    <div className="module-quick-access">
      <div className="quick-access-header">
        <h2>🎛️ 功能快速訪問</h2>
        <p>快速找到並訪問您需要的功能模組</p>
      </div>

      <div className="search-section">
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="搜尋功能模組... (例如: 患者、健檢、風險分析)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          {searchTerm && (
            <button
              className="clear-search"
              onClick={() => setSearchTerm('')}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      <div className="modules-container">
        {Object.keys(groupedModules).length === 0 ? (
          <div className="no-results">
            <div className="no-results-icon">🔍</div>
            <h3>找不到相關功能</h3>
            <p>請嘗試其他關鍵字，或清空搜尋條件查看所有功能</p>
          </div>
        ) : (
          Object.entries(groupedModules).map(([category, modules]) => (
            <div key={category} className="category-section">
              <div className="category-header">
                <span 
                  className="category-icon"
                  style={{ color: getCategoryColor(category) }}
                >
                  {getCategoryIcon(category)}
                </span>
                <h3 style={{ color: getCategoryColor(category) }}>
                  {category}
                </h3>
                <span className="module-count">({modules.length})</span>
              </div>
              
              <div className="modules-grid">
                {modules.map(module => (
                  <div
                    key={module.id}
                    className="module-card"
                    onClick={() => handleModuleClick(module.route)}
                    style={{ borderColor: getCategoryColor(category) }}
                  >
                    <div className="module-header">
                      <span 
                        className="module-icon"
                        style={{ color: getCategoryColor(category) }}
                      >
                        {module.icon}
                      </span>
                      <h4>{module.title}</h4>
                    </div>
                    <p className="module-description">{module.description}</p>
                    <div className="module-footer">
                      <span className="module-category">{module.category}</span>
                      <span className="access-arrow">→</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {searchTerm && (
        <div className="search-summary">
          找到 {filteredModules.length} 個相關功能
        </div>
      )}
    </div>
  );
}

export default ModuleQuickAccess;