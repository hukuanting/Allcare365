import { useCallback, useEffect, useState } from 'react';
import { checkAuthStatus as readAuthStatus, performLogout } from '../utils/auth';

export function useAuth() {
  const [state, setState] = useState({
    isAuthenticated: false,
    userInfo: null,
    loading: true,
  });

  const checkAuthStatus = useCallback(() => {
    const result = readAuthStatus();
    setState({
      isAuthenticated: result.isAuthenticated,
      userInfo: result.userInfo || null,
      loading: false,
    });
    return result;
  }, []);

  const logout = useCallback(async () => {
    await performLogout('manual');
    setState({ isAuthenticated: false, userInfo: null, loading: false });
  }, []);

  useEffect(() => {
    checkAuthStatus();

    const handleAuthChange = (event) => {
      setState({
        isAuthenticated: Boolean(event.detail?.isAuthenticated),
        userInfo: event.detail?.userInfo || null,
        loading: false,
      });
    };

    const handleSessionLogout = () => {
      setState({ isAuthenticated: false, userInfo: null, loading: false });
    };

    const handleStorageChange = (event) => {
      if (event.key === 'access_token' || event.key === 'user_info') {
        checkAuthStatus();
      }
    };

    window.addEventListener('auth-change', handleAuthChange);
    window.addEventListener('session-logout', handleSessionLogout);
    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('auth-change', handleAuthChange);
      window.removeEventListener('session-logout', handleSessionLogout);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [checkAuthStatus]);

  return {
    isAuthenticated: state.isAuthenticated,
    userInfo: state.userInfo,
    loading: state.loading,
    logout,
    checkAuthStatus,
  };
}
