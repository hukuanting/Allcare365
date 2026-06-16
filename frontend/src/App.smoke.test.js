import React from 'react';
import { render, screen } from '@testing-library/react';
import Login from './components/Login';

jest.mock('react-router-dom', () => ({
  Link: ({ children, to }) => <a href={to}>{children}</a>,
  useLocation: () => ({ state: null }),
  useNavigate: () => jest.fn(),
}), { virtual: true });

test('renders the sign in screen for unauthenticated users', async () => {
  localStorage.clear();
  sessionStorage.clear();

  render(<Login />);

  expect(await screen.findByRole('heading', { name: '登入' })).toBeInTheDocument();
});
