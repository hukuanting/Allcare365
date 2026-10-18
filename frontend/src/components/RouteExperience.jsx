import React, { Component, Suspense, useEffect, useLayoutEffect, useRef } from 'react';
import { Link, useLocation, useNavigationType } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const pageTitles = {
  '/': '健康，有跡可循', '/login': '登入工作空間', '/register': '申請帳號',
  '/launch': '連接醫療系統', '/dashboard': '臨床資料工作台', '/patients': '病患',
  '/health-data-input': '健檢輸入', '/bulk-import': '資料匯入', '/risk-analysis': '風險分析', '/disease-network': '疾病網絡',
  '/research-cohorts': '研究族群', '/research-reports': '研究報告',
  '/research-continuous-signals': '連續生理訊號', '/history': '健檢紀錄',
};
export const routeTitle = pathname => /^\/patients\/[^/]+\/?$/.test(pathname) ? '病患紀錄' : pageTitles[pathname.replace(/\/$/, '') || '/'] || '找不到頁面';

function PageLoadFailure() {
  const {isAuthenticated} = useAuth();
  return <section className="atlas-route-state" role="alert"><span className="atlas-eyebrow">PAGE UNAVAILABLE</span><h1>頁面無法載入</h1><p>請重新載入頁面，或{isAuthenticated ? "回到工作空間繼續操作。" : "回到首頁選擇工作入口。"}</p><div className="atlas-route-actions"><button type="button" className="atlas-button" onClick={() => window.location.reload()}>重新載入頁面</button><Link to={isAuthenticated ? "/dashboard" : "/"} className="atlas-text-link">{isAuthenticated ? "回到工作空間 →" : "回到首頁 →"}</Link></div></section>;
}

export class RouteErrorBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return this.props.fallback || <PageLoadFailure />;
    return this.props.children;
  }
}

function RouteCommit({ children, previousPath }) {
  const { pathname } = useLocation();
  const navigationType = useNavigationType();
  useLayoutEffect(() => {
    if (previousPath.current === pathname) return;
    previousPath.current = pathname;
    document.getElementById('main-content')?.focus({ preventScroll: true });
    if (navigationType !== 'POP') window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }, [pathname, navigationType]);
  return children;
}

export default function RouteExperience({ children }) {
  const { pathname } = useLocation();
  const previousPath = useRef(pathname);
  const workspaceKey = ['/risk-analysis', '/disease-network'].includes(pathname) ? '/risk-analysis' : pathname;
  useEffect(() => { document.title = routeTitle(pathname) + ' · AllCare365'; }, [pathname]);
  return <Suspense key={workspaceKey} fallback={<div className="atlas-route-loading" role="status">正在載入頁面…</div>}><RouteCommit previousPath={previousPath}><RouteErrorBoundary key={workspaceKey}>{children}</RouteErrorBoundary></RouteCommit></Suspense>;
}

export function PageNotFound() {
  const {isAuthenticated} = useAuth();
  return <section className="atlas-route-state"><span className="atlas-eyebrow">404 · PAGE NOT FOUND</span><h1>找不到這個頁面</h1><p>連結可能已變更。{isAuthenticated ? "回到工作空間，繼續您的資料與照護工作。" : "回到首頁，重新選擇您需要的工作入口。"}</p><Link to={isAuthenticated ? "/dashboard" : "/"} className="atlas-button">{isAuthenticated ? "回到工作空間 →" : "回到首頁 →"}</Link></section>;
}
