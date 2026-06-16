import API_CONFIG from '../config/api';
import sessionManager from './sessionManager';

const STORAGE_KEYS = {
  access: 'access_token',
  refresh: 'refresh_token',
  user: 'user_info',
};

export const isTokenValid = (token) => {
  if (!token) return false;

  const parts = token.split('.');
  if (parts.length !== 3) return true;

  try {
    const payload = JSON.parse(atob(parts[1]));
    return !payload.exp || payload.exp > Date.now() / 1000;
  } catch (_error) {
    return true;
  }
};

export const getStoredUser = () => {
  const raw = localStorage.getItem(STORAGE_KEYS.user);
  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch (_error) {
    return null;
  }
};

export const clearAuthState = (reason = 'manual') => {
  localStorage.removeItem(STORAGE_KEYS.access);
  localStorage.removeItem(STORAGE_KEYS.refresh);
  localStorage.removeItem(STORAGE_KEYS.user);
  localStorage.removeItem('active_tabs');
  localStorage.removeItem('allcare365_last_activity');
  sessionStorage.clear();
  sessionManager.cleanup();

  window.dispatchEvent(new CustomEvent('auth-change', {
    detail: { isAuthenticated: false, reason },
  }));
};

export const setAuthState = (data) => {
  const user = data.user || data.profile || {};
  const roles = Array.isArray(user.roles)
    ? user.roles
    : [user.role || user.product_role || user.legacy_role || user.user_type || 'patient'];

  localStorage.setItem(STORAGE_KEYS.access, data.access || data.access_token || '');
  localStorage.setItem(STORAGE_KEYS.refresh, data.refresh || data.refresh_token || '');
  localStorage.setItem(STORAGE_KEYS.user, JSON.stringify({
    id: user.id,
    username: user.username || user.email || 'user',
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    role: user.role || user.product_role || user.legacy_role || user.user_type || 'patient',
    roles,
    product_role: user.product_role || '',
    legacy_role: user.legacy_role || '',
    email: user.email || '',
  }));

  sessionManager.init();
  window.dispatchEvent(new CustomEvent('auth-change', {
    detail: { isAuthenticated: true, userInfo: getStoredUser() },
  }));
};

export const checkAuthStatus = () => {
  const token = localStorage.getItem(STORAGE_KEYS.access);
  const userInfo = getStoredUser();

  if (!token || !userInfo) {
    return { isAuthenticated: false, reason: 'missing_credentials' };
  }

  if (!isTokenValid(token)) {
    return { isAuthenticated: false, reason: 'token_expired' };
  }

  return {
    isAuthenticated: true,
    userInfo,
    role: userInfo.role,
    token,
  };
};

export const performLogout = async (reason = 'manual') => {
  const refresh = localStorage.getItem(STORAGE_KEYS.refresh);
  const access = localStorage.getItem(STORAGE_KEYS.access);

  if (refresh && reason === 'manual') {
    try {
      await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.LOGOUT}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(access ? { Authorization: `Bearer ${access}` } : {}),
        },
        body: JSON.stringify({ refresh }),
      });
    } catch (_error) {
      // Local logout must continue even if the server request fails.
    }
  }

  clearAuthState(reason);
};
