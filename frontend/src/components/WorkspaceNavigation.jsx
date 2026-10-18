import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import useMediaQuery from '@mui/material/useMediaQuery';
import CloseIcon from '@mui/icons-material/Close';
import Avatar from '@mui/material/Avatar';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import BiotechIcon from '@mui/icons-material/Biotech';
import DashboardIcon from '@mui/icons-material/Dashboard';
import HistoryIcon from '@mui/icons-material/History';
import LogoutIcon from '@mui/icons-material/Logout';
import MenuIcon from '@mui/icons-material/Menu';
import TimelineIcon from '@mui/icons-material/Timeline';
import PeopleIcon from '@mui/icons-material/People';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import { hasAnyRole, RESEARCH_ACCESS_ROLES, CLINICAL_WRITE_ROLES, getAccessLevel } from '../utils/roles';

import { Link as RouterLink } from 'react-router-dom';
import Brand from './Brand';
const primaryNav = [
  { label: '總覽', path: '/dashboard', icon: <DashboardIcon /> },
  { label: '病患', path: '/patients', icon: <PeopleIcon /> },
  { label: '健檢輸入', path: '/health-data-input', icon: <AddCircleOutlineIcon />, allowedRoles: CLINICAL_WRITE_ROLES },
  { label: '資料匯入', path: '/bulk-import', icon: <UploadFileIcon />, allowedRoles: CLINICAL_WRITE_ROLES },
  { label: '疾病網絡', path: '/disease-network', icon: <TimelineIcon /> },
  { label: '風險分析', path: '/risk-analysis', icon: <AnalyticsIcon /> },
  { label: '研究 Cohort', path: '/research-cohorts', icon: <BiotechIcon />, allowedRoles: RESEARCH_ACCESS_ROLES, group: 'research' },
  { label: '研究報告', path: '/research-reports', icon: <AssignmentTurnedInIcon />, allowedRoles: RESEARCH_ACCESS_ROLES, group: 'research' },
  { label: '連續訊號', path: '/research-continuous-signals', icon: <TimelineIcon />, allowedRoles: RESEARCH_ACCESS_ROLES, group: 'research' },
  { label: '健檢紀錄', path: '/history', icon: <HistoryIcon /> },
];

function WorkspaceNavigation({ userInfo, logout }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();
  const desktop = useMediaQuery('(min-width:1200px)');
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
  const menuTrigger = useRef(null);
  const focusTarget = useRef('trigger');
  const closeDrawer = () => { focusTarget.current = 'trigger'; setDrawerOpen(false); };
  const selectDestination = () => { focusTarget.current = 'main'; setDrawerOpen(false); };
  const restoreDrawerFocus = () => {
    const target = focusTarget.current === 'main' ? document.getElementById('main-content') : menuTrigger.current;
    target?.focus({ preventScroll: true });
  };
  useEffect(() => { if (desktop) { focusTarget.current = 'main'; setDrawerOpen(false); } }, [desktop]);
  useEffect(() => { focusTarget.current = 'main'; setDrawerOpen(false); }, [location.pathname]);
  const visibleNav = primaryNav.filter(item => hasAnyRole(userInfo, item.allowedRoles));
  const active = path => location.pathname === path || location.pathname.startsWith(path + '/');
  const current = visibleNav.find(item => active(item.path));
  const renderLinks = items => items.map(item => <RouterLink key={item.path} to={item.path} aria-current={active(item.path) ? 'page' : undefined} className={'atlas-nav-link' + (active(item.path) ? ' is-active' : '')} onClick={selectDestination}>{item.icon}<span>{item.label}</span></RouterLink>);
  const sidebar = <div className="atlas-sidebar-inner"><RouterLink to="/dashboard" className="atlas-brand-link" aria-label="AllCare365 總覽" onClick={selectDestination}><Brand /></RouterLink><div className="atlas-workspace-label">專業工作空間</div><nav aria-label="工作空間導覽"><div role="group" aria-label="照護與資料"><div className="atlas-nav-group-label">照護與資料</div>{renderLinks(visibleNav.filter(item => item.group !== 'research'))}</div>{visibleNav.some(item=>item.group === 'research') && <div role="group" aria-label="研究"><div className="atlas-nav-group-label">研究</div>{renderLinks(visibleNav.filter(item => item.group === 'research'))}</div>}</nav><div className="atlas-sidebar-foot"><span className="atlas-small-cross">+</span><span>以人為中心的健康資料</span></div></div>;

  return <><aside className="atlas-sidebar">{sidebar}</aside><header className="atlas-app-header"><IconButton ref={menuTrigger} className="atlas-drawer-trigger" aria-label="開啟導覽" aria-haspopup="dialog" aria-expanded={drawerOpen} aria-controls={drawerOpen ? 'workspace-drawer' : undefined} onClick={()=>{focusTarget.current = 'trigger';setDrawerOpen(true);}}><MenuIcon /></IconButton><span className="atlas-breadcrumb">工作空間 <span aria-hidden="true">/</span> <b>{current?.label || '總覽'}</b></span><div className="atlas-account"><span>{userInfo?.first_name || userInfo?.username || '使用者'}</span><IconButton aria-label="帳號選單" aria-haspopup="menu" aria-expanded={Boolean(menuAnchor)} onClick={event=>setMenuAnchor(event.currentTarget)}><Avatar sx={{width:30,height:30,bgcolor:'#e2ebe5',color:'#245747',fontSize:13}}>{(userInfo?.first_name || userInfo?.username || 'U').slice(0,1).toUpperCase()}</Avatar></IconButton></div></header><Menu transitionDuration={reducedMotion ? 0 : undefined} anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={()=>setMenuAnchor(null)}><MenuItem disabled>{userInfo?.username || '使用者'} · {getAccessLevel(userInfo)}</MenuItem><Divider /><MenuItem onClick={async()=>{setMenuAnchor(null);await logout();navigate('/');}}><ListItemIcon><LogoutIcon fontSize="small" /></ListItemIcon>登出</MenuItem></Menu><Drawer transitionDuration={reducedMotion ? 0 : undefined} open={drawerOpen && !desktop} onClose={closeDrawer} ModalProps={{disableRestoreFocus:true}} slotProps={{paper:{id:'workspace-drawer',role:'dialog','aria-modal':true,'aria-label':'工作空間導覽',sx:{width:'min(288px,100vw)',bgcolor:'#f1f3ee'}},transition:{onExited:restoreDrawerFocus}}}><div className="atlas-drawer-heading"><span>工作空間導覽</span><IconButton aria-label="關閉導覽" onClick={closeDrawer}><CloseIcon/></IconButton></div>{sidebar}</Drawer></>;
}
export default WorkspaceNavigation;
