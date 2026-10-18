import { vi } from 'vitest';
import { api } from './api';
const token = value => 'header.' + btoa(JSON.stringify({ exp: Date.now()/1000 + 600, generation: value })) + '.signature';
beforeEach(() => { localStorage.clear(); global.fetch = vi.fn(); });
afterEach(() => vi.restoreAllMocks());
test('credential failures do not dispatch session logout or send stale bearer credentials', async () => {
  localStorage.setItem('access_token', token('old')); const listener = vi.fn();
  window.addEventListener('session-logout', listener);
  global.fetch.mockResolvedValue({ status: 401 });
  await api.post('/api/auth/login/', { username: 'synthetic', password: 'synthetic' });
  expect(global.fetch.mock.calls[0][1].headers.Authorization).toBeUndefined();
  expect(listener).not.toHaveBeenCalled(); window.removeEventListener('session-logout', listener);
});
test('a stale API 401 cannot sign out a newer login', async () => {
  let finish; localStorage.setItem('access_token', token('old')); const listener = vi.fn();
  window.addEventListener('session-logout', listener);
  global.fetch.mockReturnValue(new Promise(resolve => { finish = resolve; }));
  const pending = api.get('/api/patients/'); localStorage.setItem('access_token', token('new'));
  finish({ status: 401 }); await pending;
  expect(listener).not.toHaveBeenCalled(); window.removeEventListener('session-logout', listener);
});
test('a current protected API 401 still rejects the session', async () => {
  localStorage.setItem('access_token', token('current')); const listener = vi.fn();
  window.addEventListener('session-logout', listener); global.fetch.mockResolvedValue({ status: 401 });
  await api.get('/api/patients/'); expect(listener).toHaveBeenCalledTimes(1);
  window.removeEventListener('session-logout', listener);
});
