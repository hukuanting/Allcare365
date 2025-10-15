import React from 'react';
import './RiskAnalysis.css';

function RiskAnalysisResults({ riskData, onClose }) {
  if (!riskData) return null;

  const getRiskColor = (category) => {
    switch (category?.toLowerCase()) {
      case 'low': return '#28a745';
      case 'moderate': return '#ffc107';
      case 'high': return '#fd7e14';
      case 'very_high': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const getRiskLabel = (category) => {
    switch (category?.toLowerCase()) {
      case 'low': return '低風險';
      case 'moderate': return '中等風險';
      case 'high': return '高風險';
      case 'very_high': return '極高風險';
      default: return '未知';
    }
  };

  return (
    <div className="risk-analysis-modal">
      <div className="risk-analysis-content">
        <div className="risk-analysis-header">
          <h2>🏥 疾病風險分析報告</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="risk-analysis-body">
          {Object.entries(riskData).map(([riskType, assessment]) => (
            <div key={riskType} className="risk-card">
              <div className="risk-card-header">
                <h3>{getRiskTypeLabel(riskType)}</h3>
                <div 
                  className="risk-badge"
                  style={{ backgroundColor: getRiskColor(assessment.risk_category) }}
                >
                  {getRiskLabel(assessment.risk_category)}
                </div>
              </div>
              
              <div className="risk-card-body">
                <div className="risk-metrics">
                  <div className="risk-metric">
                    <span className="metric-label">風險分數:</span>
                    <span className="metric-value">{assessment.risk_score?.toFixed(2) || 'N/A'}</span>
                  </div>
                  <div className="risk-metric">
                    <span className="metric-label">風險百分比:</span>
                    <span className="metric-value">{assessment.risk_percentage?.toFixed(1) || 'N/A'}%</span>
                  </div>
                  <div className="risk-metric">
                    <span className="metric-label">時間範圍:</span>
                    <span className="metric-value">{assessment.time_horizon || 'N/A'}</span>
                  </div>
                  <div className="risk-metric">
                    <span className="metric-label">信心水準:</span>
                    <span className="metric-value">{assessment.confidence_level || 'N/A'}</span>
                  </div>
                </div>
                
                {assessment.recommendations && assessment.recommendations.length > 0 && (
                  <div className="risk-recommendations">
                    <h4>📋 建議事項:</h4>
                    <ul>
                      {assessment.recommendations.map((rec, index) => (
                        <li key={index}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        
        <div className="risk-analysis-footer">
          <p className="disclaimer">
            ⚠️ 此風險評估僅供參考，請諮詢專業醫師進行詳細診斷。
          </p>
          <button className="btn btn-primary" onClick={onClose}>
            關閉報告
          </button>
        </div>
      </div>
    </div>
  );
}

function getRiskTypeLabel(riskType) {
  const labels = {
    'cardiovascular': '心血管疾病風險',
    'diabetes': '糖尿病風險',
    'metabolic_syndrome': '代謝症候群風險',
    'stroke': '中風風險',
    'coronary_heart_disease': '冠心病風險',
    'hypertension': '高血壓風險',
    'dyslipidemia': '血脂異常風險'
  };
  return labels[riskType] || riskType;
}

export default RiskAnalysisResults;