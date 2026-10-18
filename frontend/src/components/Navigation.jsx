import React, { lazy, Suspense } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { RouteErrorBoundary } from './RouteExperience';
import Brand from './Brand';

const WorkspaceNavigation = lazy(() => import('./WorkspaceNavigation'));
function Navigation() {
  const { isAuthenticated, userInfo, logout, loading } = useAuth();
  if (loading) return <header className="atlas-public-header"><Brand/><span role="status" className="atlas-header-caption">正在確認工作空間…</span></header>;
  if (!isAuthenticated) return <header className="atlas-public-header"><RouterLink to="/" aria-label="AllCare365 首頁" className="atlas-brand-link"><Brand /></RouterLink><span className="atlas-header-caption">健康，有跡可循。</span><nav aria-label="帳號導覽"><RouterLink to="/login" className="atlas-text-link">登入</RouterLink><RouterLink to="/register" className="atlas-header-cta">申請帳號 <span>↗</span></RouterLink></nav></header>;
  const failure = <header className="atlas-app-header"><RouterLink to="/" className="atlas-brand-link" aria-label="AllCare365 首頁"><Brand compact/></RouterLink><span role="alert" className="atlas-breadcrumb">導覽無法載入</span><button className="atlas-nav-reload" type="button" onClick={()=>window.location.reload()}>重新載入頁面</button></header>;
  return <RouteErrorBoundary fallback={failure}><Suspense fallback={<header className="atlas-app-header"><span role="status" className="atlas-breadcrumb">正在載入工作空間導覽…</span></header>}><WorkspaceNavigation userInfo={userInfo} logout={logout}/></Suspense></RouteErrorBoundary>;
}
export default Navigation;
