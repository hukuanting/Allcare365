import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { authorize } from 'fhirclient/browser';
import Launch from './Launch';
import API_CONFIG from '../config/api';
import { vi } from 'vitest';

vi.mock('fhirclient/browser', () => ({ authorize: vi.fn() }));
const mount = (strict = false) => render(<MemoryRouter>{strict ? <React.StrictMode><Launch /></React.StrictMode> : <Launch />}</MemoryRouter>);
beforeEach(() => { authorize.mockReset(); authorize.mockReturnValue(new Promise(() => {})); });

test('starts SMART authorization with the configured FHIR issuer', () => {
  mount();
  expect(authorize).toHaveBeenCalledWith({
    clientId: 'my_web_app',
    scope: 'launch patient/*.read openid fhirUser',
    redirectUri: `${window.location.origin}/dashboard`,
    iss: `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.FHIR_BASE}`,
  });
  expect(screen.getByRole('heading', { level: 1, name: '連接醫療系統' })).toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('正在開啟授權頁面');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('StrictMode effect replay launches only once and still handles rejection', async () => {
  let reject;
  authorize.mockReturnValue(new Promise((resolve, fail) => { reject = fail; }));
  mount(true);
  expect(authorize).toHaveBeenCalledTimes(1);
  await act(async () => { reject(new Error('Synthetic provider diagnostic')); });
  expect(await screen.findByRole('alert')).toHaveTextContent('目前無法啟動醫療系統授權');
});

test('failed launch offers an explicit retry without exposing provider diagnostics', async () => {
  authorize.mockRejectedValueOnce(new Error('Synthetic provider diagnostic'));
  mount();
  const alert = await screen.findByRole('alert');
  expect(alert).not.toHaveTextContent('Synthetic provider diagnostic');
  expect(screen.getByRole('link', { name: '返回登入' })).toHaveAttribute('href', '/login');
  fireEvent.click(screen.getByRole('button', { name: '重新連接' }));
  expect(authorize).toHaveBeenCalledTimes(2);
  expect(screen.getByRole('status')).toHaveTextContent('正在開啟授權頁面');
  expect(screen.queryByRole('button', { name: '重新連接' })).not.toBeInTheDocument();
});

test('synchronous SDK failure uses the same recovery state', async () => {
  authorize.mockImplementationOnce(() => { throw new Error('Synthetic synchronous failure'); });
  mount();
  expect(await screen.findByRole('alert')).toHaveTextContent('目前無法啟動醫療系統授權');
  expect(screen.queryByText('Synthetic synchronous failure')).not.toBeInTheDocument();
});

test('a rejected launch after unmount does not change a new launch screen', async () => {
  let reject;
  authorize.mockReturnValueOnce(new Promise((resolve, fail) => { reject = fail; }));
  const old = mount();
  old.unmount();
  mount();
  await act(async () => { reject(new Error('Synthetic obsolete failure')); });
  expect(screen.getByRole('status')).toHaveTextContent('正在開啟授權頁面');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
