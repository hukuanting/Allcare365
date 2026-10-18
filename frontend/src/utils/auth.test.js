import { vi } from 'vitest';
import { checkAuthStatus, isTokenValid, performLogout, setAuthState } from './auth';

const token = (payload) => `header.${btoa(JSON.stringify(payload))}.signature`;

beforeEach(() => { localStorage.clear(); sessionStorage.clear(); });

test('fails closed for malformed and expiry-less tokens', () => {
  expect(isTokenValid('not-a-jwt')).toBe(false);
  expect(isTokenValid(token({ sub: '1' }))).toBe(false);
  expect(isTokenValid(token({ exp: Math.floor(Date.now() / 1000) - 1 }))).toBe(false);
});

test('refuses a pending registration response that has no access token', () => {
  expect(() => setAuthState({ status: 'pending', user: { username: 'pending-user' } })).toThrow('valid access token');
  expect(checkAuthStatus().isAuthenticated).toBe(false);
});

test('logs out at the backend before clearing a rotated refresh token', async () => {
  const access = token({ exp: Math.floor(Date.now() / 1000) + 600 });
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', 'rotated-refresh');
  global.fetch = vi.fn().mockResolvedValue({ ok: true });
  await performLogout('timeout');
  expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/auth/logout/'), expect.objectContaining({
    method: 'POST', body: JSON.stringify({ refresh: 'rotated-refresh' }), keepalive: true,
  }));
  expect(localStorage.getItem('refresh_token')).toBeNull();
});
