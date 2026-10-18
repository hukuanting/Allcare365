import { vi } from 'vitest';
import { SessionManager, sessionManager, ACTIVITY_KEY, IDLE_TIMEOUT_MS } from './sessionManager';
import { setAuthState, clearAuthState } from './auth';
const token = payload => 'header.' + btoa(JSON.stringify(payload)) + '.signature';
let manager;
beforeEach(() => {
  sessionManager.cleanup(); localStorage.clear(); sessionStorage.clear();
  vi.useFakeTimers(); vi.setSystemTime(new Date('2026-10-10T00:00:00Z'));
  global.fetch = vi.fn().mockResolvedValue({ ok: true }); manager = new SessionManager();
});
afterEach(() => { manager.cleanup(); sessionManager.cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });
const signIn = () => setAuthState({ access: token({ exp: Date.now()/1000 + 3600 }), refresh: 'fresh-refresh', user: { role: 'viewer' } });

test('new login resets old idle time and survives reload/unload events', () => {
  localStorage.setItem(ACTIVITY_KEY, String(Date.now() - IDLE_TIMEOUT_MS));
  signIn(); const access = localStorage.getItem('access_token');
  window.dispatchEvent(new Event('beforeunload'));
  window.dispatchEvent(new Event('pagehide'));
  expect(localStorage.getItem('access_token')).toBe(access);
  expect(global.fetch).not.toHaveBeenCalled();
});

test('expires at fifteen minutes of inactivity without heartbeat extending it', () => {
  signIn(); vi.advanceTimersByTime(IDLE_TIMEOUT_MS - 1);
  expect(localStorage.getItem('access_token')).not.toBeNull();
  vi.advanceTimersByTime(1);
  expect(localStorage.getItem('access_token')).toBeNull();
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(global.fetch.mock.calls[0][0]).toContain('/api/auth/logout/');
});

test('real user activity extends the idle deadline', () => {
  signIn(); vi.advanceTimersByTime(10*60*1000);
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
  vi.advanceTimersByTime(10*60*1000);
  expect(localStorage.getItem('access_token')).not.toBeNull();
  vi.advanceTimersByTime(5*60*1000);
  expect(localStorage.getItem('access_token')).toBeNull();
});

test('returning from a hidden tab cannot revive an expired session', () => {
  signIn(); vi.setSystemTime(Date.now() + IDLE_TIMEOUT_MS);
  document.dispatchEvent(new Event('visibilitychange'));
  expect(localStorage.getItem('access_token')).toBeNull();
});

test('shares one refresh request and persists the rotated refresh token', async () => {
  localStorage.setItem('refresh_token', 'old-refresh');
  global.fetch.mockResolvedValue({ ok: true, json: async () => ({ access: token({ exp: Date.now()/1000 + 600 }), refresh: 'new-refresh' }) });
  const first = manager.refreshToken(); const second = manager.refreshToken();
  expect(first).toBe(second); await expect(first).resolves.toBe(true);
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(localStorage.getItem('refresh_token')).toBe('new-refresh');
});

test.each([true, false])('an old refresh result (%s) cannot replace or clear a newer login', async ok => {
  let finish; localStorage.setItem('refresh_token', 'old-refresh');
  global.fetch.mockReturnValue(new Promise(resolve => { finish = resolve; }));
  const pending = manager.refreshToken(); signIn();
  const access = localStorage.getItem('access_token');
  finish({ ok, json: async () => ({ access: token({ exp: Date.now()/1000 + 900 }), refresh: 'obsolete-refresh' }) });
  await pending;
  expect(localStorage.getItem('access_token')).toBe(access);
  expect(localStorage.getItem('refresh_token')).toBe('fresh-refresh');
  expect(global.fetch).toHaveBeenCalledTimes(1);
});

test('a delayed refresh cannot restore a signed out account', async () => {
  let finish; localStorage.setItem('refresh_token', 'old-refresh');
  global.fetch.mockReturnValue(new Promise(resolve => { finish = resolve; }));
  const pending = manager.refreshToken(); clearAuthState();
  finish({ ok: true, json: async () => ({ access: token({ exp: Date.now()/1000 + 900 }), refresh: 'obsolete-refresh' }) });
  await pending; expect(localStorage.getItem('access_token')).toBeNull();
});


test.each(['network',503,429])('temporary refresh failure %s preserves valid access and retries after a delay',async failure=>{
 const access=token({exp:Date.now()/1000+120});localStorage.setItem('access_token',access);localStorage.setItem('refresh_token','synthetic-refresh');
 if(failure==='network') global.fetch.mockRejectedValueOnce(new TypeError('Network unavailable'));
 else global.fetch.mockResolvedValueOnce({ok:false,status:failure,json:async()=>({})});
 await expect(manager.refreshToken()).resolves.toBe(false);
 expect(localStorage.getItem('access_token')).toBe(access);
 await manager.refreshToken();expect(global.fetch).toHaveBeenCalledTimes(1);
 vi.setSystemTime(Date.now()+30000);
 const replacement=token({exp:Date.now()/1000+600});global.fetch.mockResolvedValueOnce({ok:true,status:200,json:async()=>({access:replacement,refresh:'rotated'})});
 await expect(manager.refreshToken()).resolves.toBe(true);expect(localStorage.getItem('access_token')).toBe(replacement);
});

test('rejected refresh clears even unexpired access',async()=>{
 localStorage.setItem('access_token',token({exp:Date.now()/1000+120}));localStorage.setItem('refresh_token','synthetic-refresh');
 global.fetch.mockResolvedValue({ok:false,status:401,json:async()=>({})});
 await manager.refreshToken();expect(localStorage.getItem('access_token')).toBeNull();
});

test('temporary refresh failure cannot retain expired access',async()=>{
 localStorage.setItem('access_token',token({exp:Date.now()/1000-1}));localStorage.setItem('refresh_token','synthetic-refresh');
 global.fetch.mockRejectedValue(new TypeError('Network unavailable'));
 await manager.refreshToken();expect(localStorage.getItem('access_token')).toBeNull();
});

test('automatic scroll does not extend the idle deadline',()=>{signIn();vi.advanceTimersByTime(10*60*1000);window.dispatchEvent(new Event('scroll'));vi.advanceTimersByTime(5*60*1000);expect(localStorage.getItem('access_token')).toBeNull();});
test('wheel input extends the idle deadline',()=>{signIn();vi.advanceTimersByTime(10*60*1000);window.dispatchEvent(new WheelEvent('wheel',{deltaY:100}));vi.advanceTimersByTime(10*60*1000);expect(localStorage.getItem('access_token')).not.toBeNull();vi.advanceTimersByTime(5*60*1000);expect(localStorage.getItem('access_token')).toBeNull();});
