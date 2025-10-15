/**
 * Allcare365 - API配置優化
 * 統一管理API端點和配置
 */

// API基礎配置
export const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  TIMEOUT: 30000, // 30秒超時
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1秒重試延遲
};

// API端點配置
export const API_ENDPOINTS = {
  // 認證相關
  AUTH: {
    LOGIN: '/api/auth/login/',
    LOGOUT: '/api/auth/logout/',
    REGISTER: '/api/auth/register/',
    REFRESH: '/api/auth/token/refresh/',
    PROFILE: '/api/auth/profile/',
    CHANGE_PASSWORD: '/api/auth/change-password/',
  },
  
  // 患者管理
  PATIENTS: {
    LIST: '/api/patients/',
    DETAIL: (id) => `/api/patients/${id}/`,
    CREATE: '/api/patients/',
    UPDATE: (id) => `/api/patients/${id}/`,
    DELETE: (id) => `/api/patients/${id}/`,
    SEARCH: '/api/patients/search/',
  },
  
  // 健康篩檢
  HEALTH_SCREENING: {
    LIST: '/api/health-screening/screenings/',
    DETAIL: (id) => `/api/health-screening/screenings/${id}/`,
    CREATE: '/api/health-screening/screenings/',
    UPDATE: (id) => `/api/health-screening/screenings/${id}/`,
    DELETE: (id) => `/api/health-screening/screenings/${id}/`,
    PARSE_FILE: '/api/health-screening/parse-file/',
    BULK_IMPORT: '/api/health-screening/bulk-import/',
    RISK_ANALYSIS: (id) => `/api/health-screening/screenings/${id}/calculate_comprehensive_risk/`,
    EXPORT_PDF: (id) => `/api/health-screening/screenings/${id}/export_pdf/`,
    EXPORT_EXCEL: '/api/health-screening/export_excel/',
  },
  
  // 實驗室
  LABORATORY: {
    LIST: '/api/laboratory/',
    DETAIL: (id) => `/api/laboratory/${id}/`,
    CREATE: '/api/laboratory/',
    RESULTS: '/api/laboratory/results/',
    CRITICAL_RESULTS: '/api/laboratory/critical-results/',
  },
  
  // 藥房
  PHARMACY: {
    LIST: '/api/pharmacy/',
    INVENTORY: '/api/pharmacy/inventory/',
    PRESCRIPTIONS: '/api/pharmacy/prescriptions/',
    DRUG_INTERACTIONS: '/api/pharmacy/drug-interactions/',
  },
  
  // 預約管理
  APPOINTMENTS: {
    LIST: '/api/appointments/',
    CREATE: '/api/appointments/',
    UPDATE: (id) => `/api/appointments/${id}/`,
    CANCEL: (id) => `/api/appointments/${id}/cancel/`,
    CALENDAR: '/api/appointments/calendar/',
  },
  
  // 報告
  REPORTS: {
    DASHBOARD: '/api/reports/dashboard/',
    HEALTH_TRENDS: '/api/reports/health-trends/',
    RISK_ANALYSIS: '/api/reports/risk-analysis/',
    EXPORT: '/api/reports/export/',
  },
  
  // 文檔管理
  DOCUMENTS: {
    LIST: '/api/documents/',
    UPLOAD: '/api/documents/upload/',
    DOWNLOAD: (id) => `/api/documents/${id}/download/`,
    DELETE: (id) => `/api/documents/${id}/`,
  },
  
  // FHIR集成
  FHIR: {
    PATIENT: '/fhir/Patient/',
    OBSERVATION: '/fhir/Observation/',
    CONDITION: '/fhir/Condition/',
    MEDICATION: '/fhir/Medication/',
  },
};

// HTTP狀態碼
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
};

// 錯誤訊息映射
export const ERROR_MESSAGES = {
  [HTTP_STATUS.BAD_REQUEST]: '請求參數錯誤',
  [HTTP_STATUS.UNAUTHORIZED]: '請重新登入',
  [HTTP_STATUS.FORBIDDEN]: '權限不足',
  [HTTP_STATUS.NOT_FOUND]: '資源不存在',
  [HTTP_STATUS.CONFLICT]: '資料衝突',
  [HTTP_STATUS.UNPROCESSABLE_ENTITY]: '資料驗證失敗',
  [HTTP_STATUS.INTERNAL_SERVER_ERROR]: '伺服器內部錯誤',
  [HTTP_STATUS.BAD_GATEWAY]: '網關錯誤',
  [HTTP_STATUS.SERVICE_UNAVAILABLE]: '服務暫時不可用',
  NETWORK_ERROR: '網路連線錯誤',
  TIMEOUT: '請求超時',
  UNKNOWN: '未知錯誤',
};

// 請求配置
export const REQUEST_CONFIG = {
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  timeout: API_CONFIG.TIMEOUT,
};

// 文件上傳配置
export const UPLOAD_CONFIG = {
  maxSize: 10 * 1024 * 1024, // 10MB
  allowedTypes: [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
    'application/vnd.ms-excel', // .xls
    'text/csv', // .csv
    'application/pdf', // .pdf
    'image/jpeg', // .jpg
    'image/png', // .png
  ],
  headers: {
    'Content-Type': 'multipart/form-data',
  },
};

// 分頁配置
export const PAGINATION_CONFIG = {
  defaultPageSize: 25,
  pageSizeOptions: [10, 25, 50, 100],
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total, range) => 
    `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
};

// 快取配置
export const CACHE_CONFIG = {
  defaultTTL: 5 * 60 * 1000, // 5分鐘
  maxSize: 100, // 最多快取100個項目
  keys: {
    USER_PROFILE: 'user_profile',
    PATIENTS_LIST: 'patients_list',
    HEALTH_SCREENINGS: 'health_screenings',
    DASHBOARD_DATA: 'dashboard_data',
  },
};

// WebSocket配置
export const WEBSOCKET_CONFIG = {
  url: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws/',
  reconnectInterval: 5000, // 5秒重連間隔
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000, // 30秒心跳間隔
};

// 主題配置
export const THEME_CONFIG = {
  primary: '#1890ff',
  success: '#52c41a',
  warning: '#faad14',
  error: '#f5222d',
  info: '#1890ff',
  borderRadius: '6px',
  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
};

// 表單驗證配置
export const VALIDATION_CONFIG = {
  password: {
    minLength: 12,
    requireUppercase: true,
    requireLowercase: true,
    requireNumbers: true,
    requireSpecialChars: true,
  },
  email: {
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  },
  phone: {
    pattern: /^[\+]?[1-9][\d]{0,15}$/,
  },
  patientId: {
    pattern: /^[A-Z0-9]{6,12}$/,
  },
};

// 導出所有配置
export default {
  API_CONFIG,
  API_ENDPOINTS,
  HTTP_STATUS,
  ERROR_MESSAGES,
  REQUEST_CONFIG,
  UPLOAD_CONFIG,
  PAGINATION_CONFIG,
  CACHE_CONFIG,
  WEBSOCKET_CONFIG,
  THEME_CONFIG,
  VALIDATION_CONFIG,
};