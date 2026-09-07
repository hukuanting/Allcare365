import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Toolbar from '@mui/material/Toolbar';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import BiotechIcon from '@mui/icons-material/Biotech';
import DashboardIcon from '@mui/icons-material/Dashboard';
import HistoryIcon from '@mui/icons-material/History';
import LogoutIcon from '@mui/icons-material/Logout';
import MenuIcon from '@mui/icons-material/Menu';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import TimelineIcon from '@mui/icons-material/Timeline';
import PeopleIcon from '@mui/icons-material/People';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import { useAuth } from '../hooks/useAuth';
import { hasAnyRole, RESEARCH_ACCESS_ROLES } from '../utils/roles';

const primaryNav = [
  { label: '總覽', path: '/dashboard', icon: <DashboardIcon /> },
  { label: '病患', path: '/patients', icon: <PeopleIcon /> },
  { label: '健檢輸入', path: '/health-data-input', icon: <AddCircleOutlineIcon /> },
  { label: '資料匯入', path: '/bulk-import', icon: <UploadFileIcon /> },
  { label: '風險分析', path: '/risk-analysis', icon: <AnalyticsIcon /> },
  { label: '研究 Cohort', path: '/research-cohorts', icon: <BiotechIcon />, allowedRoles: RESEARCH_ACCESS_ROLES },
  { label: '研究報告', path: '/research-reports', icon: <AssignmentTurnedInIcon />, allowedRoles: RESEARCH_ACCESS_ROLES },
  { label: '連續訊號', path: '/research-continuous-signals', icon: <TimelineIcon />, allowedRoles: RESEARCH_ACCESS_ROLES },
  { label: '健檢紀錄', path: '/history', icon: <HistoryIcon /> },
];

function Navigation() {
  const { isAuthenticated, userInfo, logout } = useAuth();
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const initials = (userInfo?.first_name || userInfo?.username || 'U').slice(0, 1).toUpperCase();
  const isActive = (path) => location.pathname === path;
  const visibleNav = primaryNav.filter((item) => hasAnyRole(userInfo, item.allowedRoles));

  const goTo = (path) => {
    navigate(path);
    setDrawerOpen(false);
  };

  const handleLogout = async () => {
    setMenuAnchor(null);
    await logout();
    navigate('/');
  };

  const navButton = (item) => (
    <Button
      key={item.path}
      startIcon={item.icon}
      onClick={() => goTo(item.path)}
      sx={{
        px: 1.2,
        color: isActive(item.path) ? 'primary.main' : 'text.secondary',
        bgcolor: isActive(item.path) ? 'rgba(25,118,210,0.08)' : 'transparent',
        '&:hover': { bgcolor: 'rgba(25,118,210,0.08)' },
      }}
    >
      {item.label}
    </Button>
  );

  const drawerContent = (
    <Box sx={{ width: 292, pt: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, px: 2, py: 2 }}>
        <MonitorHeartIcon color="primary" />
        <Box>
          <Typography variant="subtitle1" fontWeight={900}>AllCare365</Typography>
          <Typography variant="caption" color="text.secondary">FHIR EHR/EMR</Typography>
        </Box>
      </Box>
      <Divider />
      <List dense>
        {visibleNav.map((item) => (
          <ListItemButton key={item.path} selected={isActive(item.path)} onClick={() => goTo(item.path)}>
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        bgcolor: 'rgba(255,255,255,0.92)',
        color: 'text.primary',
        borderBottom: '1px solid #e3ebf4',
        backdropFilter: 'blur(16px)',
      }}
    >
      <Toolbar sx={{ minHeight: 68, gap: 2 }}>
        {isAuthenticated && (
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setDrawerOpen(true)}
            sx={{ display: { xs: 'inline-flex', lg: 'none' } }}
            aria-label="開啟導覽"
          >
            <MenuIcon />
          </IconButton>
        )}

        <Box
          role="button"
          tabIndex={0}
          onClick={() => goTo(isAuthenticated ? '/dashboard' : '/')}
          onKeyDown={(event) => event.key === 'Enter' && goTo(isAuthenticated ? '/dashboard' : '/')}
          sx={{ display: 'flex', alignItems: 'center', gap: 1.25, cursor: 'pointer', minWidth: { lg: 180 } }}
        >
          <Box sx={{
            width: 36,
            height: 36,
            borderRadius: 2,
            display: 'grid',
            placeItems: 'center',
            color: '#ffffff',
            bgcolor: 'primary.main',
            boxShadow: '0 10px 24px rgba(25,118,210,0.22)',
          }}
          >
            <MonitorHeartIcon fontSize="small" />
          </Box>
          <Box sx={{ lineHeight: 1 }}>
            <Typography variant="subtitle1" fontWeight={900}>AllCare365</Typography>
            <Typography variant="caption" color="text.secondary">FHIR EHR/EMR</Typography>
          </Box>
        </Box>

        <Box sx={{ display: { xs: 'none', lg: 'flex' }, alignItems: 'center', gap: 0.35, flex: 1 }}>
          {isAuthenticated && visibleNav.map(navButton)}
        </Box>

        <Box sx={{ flex: { xs: 1, lg: 0 } }} />

        {isAuthenticated ? (
          <>
            <Tooltip title="帳號">
              <IconButton onClick={(event) => setMenuAnchor(event.currentTarget)} sx={{ p: 0 }}>
                <Avatar sx={{ width: 36, height: 36, bgcolor: 'secondary.main', color: '#062a31', fontWeight: 900 }}>
                  {initials}
                </Avatar>
              </IconButton>
            </Tooltip>
            <Menu
              anchorEl={menuAnchor}
              open={Boolean(menuAnchor)}
              onClose={() => setMenuAnchor(null)}
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
              transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            >
              <MenuItem disabled>
                <Box>
                  <Typography variant="body2" fontWeight={900}>{userInfo?.username || '使用者'}</Typography>
                  <Typography variant="caption" color="text.secondary">{userInfo?.role || '未指定角色'}</Typography>
                </Box>
              </MenuItem>
              <Divider />
              <MenuItem onClick={handleLogout}>
                <ListItemIcon><LogoutIcon fontSize="small" /></ListItemIcon>
                登出
              </MenuItem>
            </Menu>
          </>
        ) : (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button onClick={() => navigate('/login')}>登入</Button>
            <Button variant="contained" onClick={() => navigate('/register')}>註冊</Button>
          </Box>
        )}

        <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} ModalProps={{ keepMounted: true }}>
          {drawerContent}
        </Drawer>
      </Toolbar>
    </AppBar>
  );
}

export default Navigation;
