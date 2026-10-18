import { vi } from 'vitest';
import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import Login from './Login';
import Register from './Register';
import { api, parseApiResponse } from '../config/api';

const routing = vi.hoisted(() => ({ state: null, navigate: vi.fn() }));

vi.mock('react-router-dom', () => ({
  Link: ({ children, to }) => <a href={to}>{children}</a>,
  useLocation: () => ({ state: routing.state }),
  useNavigate: () => routing.navigate,
}));

vi.mock('../config/api', () => ({
  __esModule: true,
  default: { ENDPOINTS: { LOGIN: '/api/auth/login/', REGISTER: '/api/auth/register/', MFA_ENROLL: '/api/auth/mfa/enroll/', MFA_VERIFY: '/api/auth/mfa/verify/' } },
  api: { post: vi.fn() },
  parseApiResponse: vi.fn((response) => response.payload),
}));

const fillLogin = () => {
  fireEvent.change(screen.getByRole('textbox', { name: /^帳號/ }), { target: { value: 'clinician' } });
  fireEvent.change(screen.getByLabelText(/^密碼/), { target: { value: 'password' } });
};

beforeEach(() => {
  routing.state = null; routing.navigate.mockReset();
  localStorage.clear();
  sessionStorage.clear();
  api.post.mockReset();
  parseApiResponse.mockImplementation((response) => response.payload);
});

test('shows OTP only after the server requires MFA', async () => {
  api.post.mockResolvedValue({ ok: false, payload: { code: 'mfa_required' } });
  render(<Login />); fillLogin();
  expect(screen.queryByRole('textbox', { name: /^驗證器代碼/ })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '登入' }));
  const otp = await screen.findByRole('textbox', { name: /^驗證器代碼/ });
  await waitFor(() => expect(otp).toHaveFocus());
  expect(screen.getByRole('alert')).toHaveClass('MuiAlert-standardInfo');
  fireEvent.change(otp, { target: { value: '123456' } });
  fireEvent.click(screen.getByRole('button', { name: '登入' }));
  await waitFor(() => expect(api.post).toHaveBeenLastCalledWith('/api/auth/login/', expect.objectContaining({ otp_token: '123456' })));
});

test('public Viewer registration completes without automatically signing in', async () => {
  api.post.mockResolvedValue({ ok: true, payload: { status: 'active', detail: '帳號已建立，可使用 Viewer 權限登入。' } });
  render(<Register />);
  fireEvent.change(screen.getByRole('textbox', { name: /^帳號/ }), { target: { value: 'applicant' } });
  fireEvent.change(screen.getByLabelText(/^Email/), { target: { value: 'applicant@example.test' } });
  fireEvent.change(screen.getByLabelText(/^密碼/), { target: { value: 'Password-123' } });
  fireEvent.change(screen.getByLabelText(/^確認密碼/), { target: { value: 'Password-123' } });
  fireEvent.click(screen.getByRole('button', { name: '申請帳號' }));
  const confirmation=await screen.findByRole('heading', { name: '帳號已建立' });await waitFor(()=>expect(confirmation).toHaveFocus());
  expect(localStorage.getItem('access_token')).toBeNull();
});

test('enrolls MFA without persisting the provisioning URI and verifies before login', async () => {
  const access = `header.${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 600 }))}.signature`;
  api.post
    .mockResolvedValueOnce({ ok: false, payload: { code: 'mfa_enrollment_required' } })
    .mockResolvedValueOnce({ ok: true, payload: { provisioning_uri: 'otpauth://totp/AllCare365:clinician?secret=TESTSECRET' } })
    .mockResolvedValueOnce({ ok: true, payload: { access, refresh: 'refresh', user: { username: 'clinician' } } });
  render(<Login />);
  fillLogin();
  fireEvent.click(screen.getByRole('button', { name: '登入' }));
  expect(await screen.findByRole('button', { name: '開始設定 MFA' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '開始設定 MFA' }));
  expect(await screen.findByDisplayValue(/otpauth:\/\/totp/)).toBeInTheDocument();
  expect(localStorage.getItem('provisioning_uri')).toBeNull();
  fireEvent.change(screen.getByRole('textbox', { name: /^驗證器代碼/ }), { target: { value: '123456' } });
  fireEvent.click(screen.getByRole('button', { name: '驗證並登入' }));
  await waitFor(() => expect(api.post).toHaveBeenLastCalledWith('/api/auth/mfa/verify/', expect.objectContaining({ otp_token: '123456' })));
  expect(localStorage.getItem('access_token')).toBe(access);
});

test('MFA form submission follows enrollment phase and changing identity discards setup', async () => {
 api.post.mockResolvedValueOnce({ok:false,payload:{code:'mfa_enrollment_required'}}).mockResolvedValueOnce({ok:true,payload:{provisioning_uri:'otpauth://totp/Synthetic?secret=TEST'}});
 render(<Login/>);fillLogin();fireEvent.submit(screen.getByRole('form',{name:'登入'}));await screen.findByRole('button',{name:'開始設定 MFA'});
 fireEvent.submit(screen.getByRole('form',{name:'登入'}));await screen.findByDisplayValue(/otpauth:/);expect(api.post).toHaveBeenLastCalledWith('/api/auth/mfa/enroll/',expect.any(Object));
 fireEvent.change(screen.getByRole('textbox',{name:/^帳號/}),{target:{value:'second-user'}});expect(screen.queryByDisplayValue(/otpauth:/)).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'登入'})).toBeInTheDocument();expect(screen.queryByRole('textbox',{name:/^驗證器代碼/})).not.toBeInTheDocument();
});
test('login fields lock while a request is pending and recover after failure',async()=>{
 let complete;api.post.mockReturnValue(new Promise(resolve=>{complete=resolve;}));render(<Login/>);fillLogin();act(()=>{fireEvent.submit(screen.getByRole('form',{name:'登入'}));fireEvent.submit(screen.getByRole('form',{name:'登入'}));});expect(api.post).toHaveBeenCalledTimes(1);expect(screen.getByRole('textbox',{name:/^帳號/})).toBeDisabled();expect(screen.getByLabelText(/^密碼/)).toBeDisabled();expect(screen.getByRole('form',{name:'登入'})).toHaveAttribute('aria-busy','true');
 await act(async()=>complete({ok:false,payload:{detail:'Synthetic login failure'}}));await screen.findByText('Synthetic login failure');await waitFor(()=>expect(screen.getByRole('alert')).toHaveFocus());expect(screen.getByRole('textbox',{name:/^帳號/})).toBeEnabled();expect(screen.getByLabelText(/^密碼/)).toHaveValue('password');
});
test('registration confirmation prevents submitting another application',async()=>{
 api.post.mockResolvedValue({ok:true,payload:{status:'active'}});render(<Register/>);fireEvent.change(screen.getByRole('textbox',{name:/^帳號/}),{target:{value:'synthetic'}});fireEvent.change(screen.getByRole('textbox',{name:/^Email/}),{target:{value:'synthetic@example.test'}});fireEvent.change(screen.getByLabelText(/^密碼/),{target:{value:'Password-123'}});fireEvent.change(screen.getByLabelText(/^確認密碼/),{target:{value:'Password-123'}});fireEvent.submit(screen.getByRole('form',{name:'申請帳號'}));await screen.findByRole('heading',{name:'帳號已建立'});expect(screen.queryByRole('form',{name:'申請帳號'})).not.toBeInTheDocument();expect(screen.getByRole('link',{name:'前往登入'})).toHaveAttribute('href','/login');expect(localStorage.getItem('access_token')).toBeNull();
});

test('session reauthentication explains idle expiry and restores patient query and anchor',async()=>{
 routing.state={reason:'idle_timeout',from:{pathname:'/risk-analysis',search:'?patient_id=synthetic-id',hash:'#results'}};
 const access='header.'+btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+1800}))+'.signature';
 api.post.mockResolvedValue({ok:true,payload:{access,refresh:'synthetic-refresh',user:{username:'synthetic'}}});
 render(<Login/>);expect(screen.getByText(/已超過 15 分鐘未操作/)).toBeInTheDocument();fillLogin();
 fireEvent.click(screen.getByRole('button',{name:'登入'}));
 await waitFor(()=>expect(routing.navigate).toHaveBeenCalledWith('/risk-analysis?patient_id=synthetic-id#results',{replace:true}));
});

test('registration password mismatch focuses the explanation and preserves editable fields',async()=>{
 render(<Register/>);fireEvent.change(screen.getByLabelText(/^密碼/),{target:{value:'Synthetic-Password-1'}});fireEvent.change(screen.getByLabelText(/^確認密碼/),{target:{value:'Synthetic-Password-2'}});fireEvent.submit(screen.getByRole('form',{name:'申請帳號'}));
 const alert=await screen.findByRole('alert');expect(alert).toHaveTextContent('兩次輸入的密碼不一致。');await waitFor(()=>expect(alert).toHaveFocus());expect(screen.getByLabelText(/^確認密碼/)).toHaveValue('Synthetic-Password-2');expect(screen.getByRole('button',{name:'申請帳號'})).toBeEnabled();expect(api.post).not.toHaveBeenCalled();
});

test('MFA enrollment and verification ignore repeated pending submissions',async()=>{
 let enrollDone,verifyDone;api.post.mockResolvedValueOnce({ok:false,payload:{code:'mfa_enrollment_required'}}).mockReturnValueOnce(new Promise(resolve=>{enrollDone=resolve})).mockReturnValueOnce(new Promise(resolve=>{verifyDone=resolve}));
 render(<Login/>);fillLogin();const form=screen.getByRole('form',{name:'登入'});fireEvent.submit(form);await screen.findByRole('button',{name:'開始設定 MFA'});
 act(()=>{fireEvent.submit(form);fireEvent.submit(form)});expect(api.post).toHaveBeenCalledTimes(2);await act(async()=>enrollDone({ok:true,payload:{provisioning_uri:'otpauth://totp/Synthetic?secret=TEST'}}));
 fireEvent.change(await screen.findByRole('textbox',{name:/^驗證器代碼/}),{target:{value:'123456'}});act(()=>{fireEvent.submit(form);fireEvent.submit(form)});expect(api.post).toHaveBeenCalledTimes(3);await act(async()=>verifyDone({ok:false,payload:{detail:'Synthetic verification failure'}}));expect(await screen.findByText('Synthetic verification failure')).toBeInTheDocument();expect(screen.getByRole('button',{name:'驗證並登入'})).toBeEnabled();
});

test('registration sends one pending application and permits retry after failure',async()=>{
 let finish;api.post.mockReturnValueOnce(new Promise(resolve=>{finish=resolve})).mockResolvedValueOnce({ok:true,payload:{status:'active'}});render(<Register/>);
 fireEvent.change(screen.getByRole('textbox',{name:/^帳號/}),{target:{value:'synthetic-applicant'}});fireEvent.change(screen.getByLabelText(/^Email/),{target:{value:'synthetic@example.test'}});fireEvent.change(screen.getByLabelText(/^密碼/),{target:{value:'Synthetic-Password-1'}});fireEvent.change(screen.getByLabelText(/^確認密碼/),{target:{value:'Synthetic-Password-1'}});
 const form=screen.getByRole('form',{name:'申請帳號'});act(()=>{fireEvent.submit(form);fireEvent.submit(form)});expect(api.post).toHaveBeenCalledTimes(1);expect(screen.getByRole('textbox',{name:/^帳號/})).toBeDisabled();
 await act(async()=>finish({ok:false,payload:{detail:'Synthetic registration failure'}}));await waitFor(()=>expect(screen.getByRole('alert')).toHaveFocus());expect(screen.getByLabelText(/^密碼/)).toHaveValue('Synthetic-Password-1');
 fireEvent.submit(form);await screen.findByRole('heading',{name:'帳號已建立'});expect(api.post).toHaveBeenCalledTimes(2);expect(localStorage.getItem('access_token')).toBeNull();
});
