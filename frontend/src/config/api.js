const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  ENDPOINTS: {
    LOGIN: '/api/auth/login/',
    REGISTER: '/api/auth/register/',
    LOGOUT: '/api/auth/logout/',
    PROFILE: '/api/auth/profile/',
    TOKEN_REFRESH: '/api/auth/token/refresh/',

    PATIENTS: '/api/patients/',
    HEALTH_SCREENINGS: '/api/health-screening/screenings/',
    IMMUNIZATIONS: '/api/health-screening/immunizations/',
    PROBLEMS: '/api/health-screening/problems/',
    PROCEDURES: '/api/health-screening/procedures/',
    PARSE_FILE: '/api/health-screening/parse-file/',
    BULK_IMPORT: '/api/health-screening/bulk-import/',
    FHIR_IMPORT: '/api/health-screening/fhir-import/',
    RISK_ANALYSIS: '/api/health-screening/risk-analysis/',
    RISK_ALGORITHMS: '/api/health-screening/risk-algorithms/',
    COHORT_SUMMARY: '/api/health-screening/cohorts/summary/',
    PATIENTS_LIKE_THIS: '/api/health-screening/cohorts/patients-like-this/',
    DATA_QUALITY_SUMMARY: '/api/health-screening/data-quality/summary/',
    CONTINUOUS_SIGNAL_REPORT: '/api/health-screening/research/continuous-signals/latest/',
    RESEARCH_REPORTS: '/api/health-screening/research-reports/',

    FHIR_BASE: '/fhir/R4',
  },
};

const authHeader = () => {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const buildHeaders = (headers = {}, includeJson = true) => ({
  ...(includeJson ? { 'Content-Type': 'application/json' } : {}),
  ...authHeader(),
  ...headers,
});

export const apiRequest = async (endpoint, options = {}) => {
  const includeJson = options.includeJson !== false;
  const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, {
    ...options,
    headers: buildHeaders(options.headers, includeJson),
  });

  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('session-logout', {
      detail: { reason: 'unauthorized' },
    }));
  }

  return response;
};

export const parseApiResponse = async (response) => {
  const contentType = response.headers.get('content-type') || '';

  if (!contentType.includes('application/json')) {
    const text = await response.text();
    return text ? { detail: text } : {};
  }

  return response.json();
};

export const api = {
  get: (endpoint, options = {}) => apiRequest(endpoint, { method: 'GET', ...options }),
  post: (endpoint, data, options = {}) => apiRequest(endpoint, {
    method: 'POST',
    body: JSON.stringify(data),
    ...options,
  }),
  put: (endpoint, data, options = {}) => apiRequest(endpoint, {
    method: 'PUT',
    body: JSON.stringify(data),
    ...options,
  }),
  patch: (endpoint, data, options = {}) => apiRequest(endpoint, {
    method: 'PATCH',
    body: JSON.stringify(data),
    ...options,
  }),
  delete: (endpoint, options = {}) => apiRequest(endpoint, { method: 'DELETE', ...options }),
  upload: (endpoint, formData, options = {}) => apiRequest(endpoint, {
    method: 'POST',
    body: formData,
    includeJson: false,
    ...options,
  }),
};

export default API_CONFIG;
