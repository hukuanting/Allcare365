import API_CONFIG from '../config/api';
import sessionManager, { ACTIVITY_KEY, IDLE_TIMEOUT_MS } from './sessionManager';

const STORAGE_KEYS = { access: 'access_token', refresh: 'refresh_token', user: 'user_info' };

const decodeJwtPayload = (token) => {
  if (typeof token !== 'string' || !token.trim()) return null;
  const parts = token.split('.');
  if (parts.length !== 3 || !parts.every(Boolean)) return null;
  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - base64.length % 4) % 4), '=');
    const payload = JSON.parse(atob(padded));
    return payload && typeof payload === 'object' ? payload : null;
  } catch (_error) { return null; }
};

export const isTokenValid = (token) => {
  const payload = decodeJwtPayload(token);
  return Boolean(payload && typeof payload.exp === 'number' && payload.exp > Date.now() / 1000);
};

export const getStoredUser = () => {
  const raw = localStorage.getItem(STORAGE_KEYS.user);
  if (!raw) return null;
  try { const user = JSON.parse(raw); return user && typeof user === 'object' ? user : null; } catch (_error) { return null; }
};

export const clearAuthState = (reason = 'manual') => {
  Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
  localStorage.removeItem('active_tabs');
  localStorage.removeItem(ACTIVITY_KEY);
  sessionStorage.removeItem('allcare365_session');
  sessionManager.cleanup();
  window.dispatchEvent(new CustomEvent('auth-change', { detail: { isAuthenticated: false, reason } }));
};

export const setAuthState = (data = {}) => {
  const access = data.access || data.access_token;
  if (!isTokenValid(access)) throw new Error('The sign-in response did not include a valid access token.');
  const user = data.user || data.profile || {};
  const roles = Array.isArray(user.roles) ? user.roles : [user.role || user.product_role || user.legacy_role || user.user_type || 'patient'];
  sessionManager.cleanup();
  localStorage.setItem(ACTIVITY_KEY, String(Date.now()));
  localStorage.setItem(STORAGE_KEYS.access, access);
  const refresh = data.refresh || data.refresh_token;
  if (typeof refresh === 'string' && refresh) localStorage.setItem(STORAGE_KEYS.refresh, refresh);
  else localStorage.removeItem(STORAGE_KEYS.refresh);
  localStorage.setItem(STORAGE_KEYS.user, JSON.stringify({ id: user.id, username: user.username || user.email || 'user', first_name: user.first_name || '', last_name: user.last_name || '', role: user.role || user.product_role || user.legacy_role || user.user_type || 'patient', roles, product_role: user.product_role || '', legacy_role: user.legacy_role || '', email: user.email || '' }));
  sessionManager.init();
  window.dispatchEvent(new CustomEvent('auth-change', { detail: { isAuthenticated: true, userInfo: getStoredUser() } }));
};

export const checkAuthStatus = () => {
  const token = localStorage.getItem(STORAGE_KEYS.access); const userInfo = getStoredUser();
  if (!token || !userInfo) return { isAuthenticated: false, reason: 'missing_credentials' };
  const lastActivity = Number(localStorage.getItem(ACTIVITY_KEY));
  if (localStorage.getItem(ACTIVITY_KEY) && Date.now() - lastActivity >= IDLE_TIMEOUT_MS) {
    clearAuthState('idle_timeout');
    return { isAuthenticated: false, reason: 'idle_timeout' };
  }
  if (!isTokenValid(token)) return { isAuthenticated: false, reason: 'token_expired' };
  return { isAuthenticated: true, userInfo, role: userInfo.role, token };
};

export const performLogout = async (reason = 'manual') => {
  const refresh = localStorage.getItem(STORAGE_KEYS.refresh); const access = localStorage.getItem(STORAGE_KEYS.access);
  clearAuthState(reason);
  if (access) try { await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.LOGOUT}`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}) }, body: JSON.stringify({ refresh }), keepalive: true }); } catch (_error) { /* local sign-out must continue */ }
};
