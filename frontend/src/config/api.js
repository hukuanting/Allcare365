const API_CONFIG = {
  BASE_URL: (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '')).replace(/\/$/, ''),
  ENDPOINTS: {
    LOGIN: '/api/auth/login/',
    REGISTER: '/api/auth/register/',
    LOGOUT: '/api/auth/logout/',
    PROFILE: '/api/auth/profile/',
    TOKEN_REFRESH: '/api/auth/token/refresh/',
    MFA_ENROLL: '/api/auth/mfa/enroll/',
    MFA_VERIFY: '/api/auth/mfa/verify/',

    PATIENTS: '/api/patients/',
    HEALTH_SCREENINGS: '/api/health-screening/screenings/',
    IMMUNIZATIONS: '/api/health-screening/immunizations/',
    PROBLEMS: '/api/health-screening/problems/',
    PROCEDURES: '/api/health-screening/procedures/',
    PARSE_FILE: '/api/health-screening/parse-file/',
    BULK_IMPORT: '/api/health-screening/bulk-import/',
    FHIR_PREVIEW: '/api/health-screening/fhir-preview/',
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
  const headers = buildHeaders(options.headers, includeJson);
  const credentialEndpoint = [API_CONFIG.ENDPOINTS.LOGIN, API_CONFIG.ENDPOINTS.REGISTER, API_CONFIG.ENDPOINTS.MFA_ENROLL, API_CONFIG.ENDPOINTS.MFA_VERIFY, API_CONFIG.ENDPOINTS.TOKEN_REFRESH].includes(endpoint.split('?')[0]);
  if (credentialEndpoint) delete headers.Authorization;
  const sentAuthorization = headers.Authorization;
  const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, { ...options, headers });

  if (response.status === 401 && !credentialEndpoint && sentAuthorization
      && sentAuthorization === `Bearer ${localStorage.getItem('access_token')}`) {
    window.dispatchEvent(new CustomEvent('session-logout', {
      detail: { reason: 'unauthorized' },
    }));
  }

  return response;
};

export { parseApiResponse } from '../utils/apiResponse';

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
