import API_CONFIG from '../config/api';
import { clearAuthState, isTokenValid } from './auth';

export const IDLE_TIMEOUT_MS = 15 * 60 * 1000;
export const ACTIVITY_KEY = 'allcare365_last_activity';
// Scroll can be caused by focus restoration; count input events instead.
const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'mousemove', 'wheel', 'touchstart', 'touchmove'];

class SessionManager {
  constructor() {
    this.isInitialized = false;
    this.tokenCheckInterval = null;
    this.refreshPromise = null;
    this.generation = 0;
    this.refreshRetryAt = 0;
  }

  init() {
    if (this.isInitialized) return;
    if (!localStorage.getItem(ACTIVITY_KEY)) localStorage.setItem(ACTIVITY_KEY, String(Date.now()));
    this.activityHandler = () => {
      if (!this.checkIdle()) return;
      const previous = Number(localStorage.getItem(ACTIVITY_KEY));
      if (Date.now() - previous >= 1000) localStorage.setItem(ACTIVITY_KEY, String(Date.now()));
    };
    this.visibilityHandler = () => { if (!document.hidden) this.checkTokenExpiry(); };
    this.storageHandler = (event) => {
      if (event.key === 'access_token' && !event.newValue && !localStorage.getItem('access_token')) {
        this.expireSession('signed_out_elsewhere');
      }
    };
    this.logoutHandler = (event) => {
      if (event.detail?.reason === 'unauthorized') this.expireSession('unauthorized');
    };
    ACTIVITY_EVENTS.forEach(event => window.addEventListener(event, this.activityHandler, { passive: true }));
    document.addEventListener('visibilitychange', this.visibilityHandler);
    window.addEventListener('storage', this.storageHandler);
    window.addEventListener('session-logout', this.logoutHandler);
    // Reloading and tab closure must not revoke credentials in other tabs.
    this.tokenCheckInterval = setInterval(() => this.checkTokenExpiry(), 10000);
    this.isInitialized = true;
    this.checkIdle();
  }

  checkIdle() {
    if (!localStorage.getItem('access_token')) return false;
    const lastActivity = Number(localStorage.getItem(ACTIVITY_KEY));
    if (!Number.isFinite(lastActivity) || lastActivity <= 0 || Date.now() - lastActivity >= IDLE_TIMEOUT_MS) {
      this.expireSession('idle_timeout', true);
      return false;
    }
    return true;
  }

  notifyBackendLogout() {
    const refresh = localStorage.getItem('refresh_token');
    const access = localStorage.getItem('access_token');
    if (access) fetch(API_CONFIG.BASE_URL + API_CONFIG.ENDPOINTS.LOGOUT, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + access },
      body: JSON.stringify({ refresh }), keepalive: true,
    }).catch(() => {});
  }

  checkTokenExpiry() {
    if (!this.checkIdle()) return;
    const token = localStorage.getItem('access_token');
    if (!isTokenValid(token)) { this.refreshToken(); return; }
    try {
      const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      if (payload.exp - Date.now() / 1000 < 300) this.refreshToken();
    } catch (_error) { this.expireSession('invalid_token'); }
  }

  refreshToken() {
    if (this.refreshPromise) return this.refreshPromise;
    if (Date.now() < this.refreshRetryAt && isTokenValid(localStorage.getItem('access_token'))) return Promise.resolve(false);
    const refresh = localStorage.getItem('refresh_token');
    const generation = this.generation;
    if (!refresh) { this.expireSession('missing_refresh_token'); return Promise.resolve(false); }
    const operation = async () => {
      if (generation !== this.generation) return false;
      // Another tab may already have rotated the credential while waiting.
      if (localStorage.getItem('refresh_token') !== refresh) return isTokenValid(localStorage.getItem('access_token'));
      return this.requestRefresh(refresh, generation);
    };
    const pending = (navigator.locks?.request
      ? navigator.locks.request('allcare365-token-refresh', operation)
      : operation()).finally(() => { if (this.refreshPromise === pending) this.refreshPromise = null; });
    this.refreshPromise = pending;
    return pending;
  }

  async requestRefresh(refresh, generation = this.generation) {
    const stillCurrent = () => generation === this.generation && localStorage.getItem('refresh_token') === refresh;
    let transientFailure = true;
    try {
      const response = await fetch(API_CONFIG.BASE_URL + API_CONFIG.ENDPOINTS.TOKEN_REFRESH, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh }),
      });
      transientFailure = response.status === 429 || response.status >= 500;
      const data = await response.json().catch(() => ({}));
      if (!stillCurrent()) return false;
      if (!response.ok || !isTokenValid(data.access)) throw new Error('Refresh rejected');
      this.refreshRetryAt = 0;
      localStorage.setItem('access_token', data.access);
      const replacement = data.refresh || data.refresh_token;
      if (typeof replacement === 'string' && replacement) localStorage.setItem('refresh_token', replacement);
      window.dispatchEvent(new CustomEvent('token-refreshed', { detail: { newToken: data.access } }));
      return true;
    } catch (_error) {
      if (stillCurrent()) {
        if (transientFailure && isTokenValid(localStorage.getItem('access_token'))) {
          // A temporary service failure does not invalidate an unexpired credential.
          this.refreshRetryAt = Date.now() + 30000;
        } else this.expireSession('refresh_failed');
      }
      return false;
    }
  }

  expireSession(reason, notifyBackend = false) {
    if (notifyBackend) this.notifyBackendLogout();
    this.cleanup();
    clearAuthState(reason);
    if (reason !== 'unauthorized') window.dispatchEvent(new CustomEvent('session-logout', { detail: { reason } }));
  }

  cleanup() {
    this.generation += 1;
    this.refreshRetryAt = 0;
    if (this.tokenCheckInterval) clearInterval(this.tokenCheckInterval);
    ACTIVITY_EVENTS.forEach(event => window.removeEventListener(event, this.activityHandler));
    document.removeEventListener('visibilitychange', this.visibilityHandler);
    window.removeEventListener('storage', this.storageHandler);
    window.removeEventListener('session-logout', this.logoutHandler);
    this.tokenCheckInterval = null;
    this.refreshPromise = null;
    this.isInitialized = false;
  }
}

const sessionManager = new SessionManager();
export { SessionManager, sessionManager };
export default sessionManager;
