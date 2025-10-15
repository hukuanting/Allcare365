import React from 'react';
import './EmptyState.css';

function EmptyState({ 
  icon = '📋', 
  title = '暫無數據', 
  description = '目前沒有相關數據，請先添加一些內容。',
  actionText = '開始添加',
  onAction = null,
  showAction = true 
}) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-description">{description}</p>
      {showAction && onAction && (
        <button className="empty-state-action" onClick={onAction}>
          {actionText}
        </button>
      )}
    </div>
  );
}

export default EmptyState;