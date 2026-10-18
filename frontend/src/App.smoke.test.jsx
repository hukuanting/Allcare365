import { vi } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import Login from './components/Login';

vi.mock('react-router-dom', () => ({
  Link: ({ children, to }) => <a href={to}>{children}</a>,
  useLocation: () => ({ state: null }), useNavigate: () => vi.fn(),
}));

test('renders the sign in screen for unauthenticated users', async () => {
  localStorage.clear(); sessionStorage.clear(); render(<Login />);
  expect(await screen.findByRole('heading', { name: '登入工作空間', level: 1 })).toBeInTheDocument();
});
