import React, { useEffect, useMemo, useState } from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';

import Navigation from './components/Navigation';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import Login from './components/Login';
import Register from './components/Register';
import Launch from './components/Launch';
import HealthDataInput from './components/HealthDataInput';
import RiskAnalysis from './components/RiskAnalysis';
import ResearchCohorts from './components/ResearchCohorts';
import ResearchReports from './components/ResearchReports';
import ContinuousSignalReport from './components/ContinuousSignalReport';
import BulkHealthDataImport from './components/BulkHealthDataImport';
import PatientManagement from './components/PatientManagement';
import PatientChart from './components/PatientChart';
import HistoryRecords from './components/HistoryRecords';
import ProtectedRoute from './components/ProtectedRoute';
import sessionManager from './utils/sessionManager';
import { checkAuthStatus } from './utils/auth';
import { RESEARCH_ACCESS_ROLES } from './utils/roles';
import './App.css';

const createAppTheme = () => createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
      light: '#4ea3ff',
      dark: '#0d47a1',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#15d1c3',
      light: '#78ffeb',
      dark: '#008b84',
      contrastText: '#062a31',
    },
    success: {
      main: '#22c55e',
      light: '#78ff9b',
      dark: '#15803d',
    },
    background: {
      default: '#f6f9fc',
      paper: '#ffffff',
    },
    text: {
      primary: '#102033',
      secondary: '#5d6b7a',
    },
    divider: '#e3ebf4',
  },
  typography: {
    fontFamily: '"Noto Sans TC", "Microsoft JhengHei", "Segoe UI", sans-serif',
    h1: { letterSpacing: 0, fontWeight: 900 },
    h2: { letterSpacing: 0, fontWeight: 900 },
    h3: { letterSpacing: 0, fontWeight: 850 },
    h4: { letterSpacing: 0, fontWeight: 850 },
    h5: { letterSpacing: 0, fontWeight: 800 },
    h6: { letterSpacing: 0, fontWeight: 800 },
    button: { letterSpacing: 0, fontWeight: 800, textTransform: 'none' },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { minHeight: 38, borderRadius: 8 },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: '1px solid #e3ebf4',
          boxShadow: '0 10px 28px rgba(16, 32, 51, 0.06)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          color: '#5d6b7a',
          fontWeight: 800,
          background: '#f7fbff',
        },
      },
    },
  },
});

function ProtectedPage({ children, allowedRoles = [] }) {
  return <ProtectedRoute allowedRoles={allowedRoles}>{children}</ProtectedRoute>;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const theme = useMemo(() => createAppTheme(), []);

  useEffect(() => {
    const authResult = checkAuthStatus();
    setIsAuthenticated(authResult.isAuthenticated);

    if (authResult.isAuthenticated) {
      sessionManager.init();
    }

    const handleAuthChange = (event) => {
      setIsAuthenticated(Boolean(event.detail?.isAuthenticated));
    };

    window.addEventListener('auth-change', handleAuthChange);

    return () => {
      sessionManager.cleanup();
      window.removeEventListener('auth-change', handleAuthChange);
    };
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box className="app-shell">
          <Navigation />
          <Box component="main" className={isAuthenticated ? 'app-main app-main-authenticated' : 'app-main'}>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/launch" element={<Launch />} />
              <Route path="/dashboard" element={<ProtectedPage><Dashboard /></ProtectedPage>} />
              <Route path="/patients" element={<ProtectedPage><PatientManagement /></ProtectedPage>} />
              <Route path="/patients/:patientId" element={<ProtectedPage><PatientChart /></ProtectedPage>} />
              <Route path="/health-data-input" element={<ProtectedPage><HealthDataInput /></ProtectedPage>} />
              <Route path="/bulk-import" element={<ProtectedPage><BulkHealthDataImport /></ProtectedPage>} />
              <Route path="/risk-analysis" element={<ProtectedPage><RiskAnalysis /></ProtectedPage>} />
              <Route path="/research-cohorts" element={<ProtectedPage allowedRoles={RESEARCH_ACCESS_ROLES}><ResearchCohorts /></ProtectedPage>} />
              <Route path="/research-reports" element={<ProtectedPage allowedRoles={RESEARCH_ACCESS_ROLES}><ResearchReports /></ProtectedPage>} />
              <Route path="/research-continuous-signals" element={<ProtectedPage allowedRoles={RESEARCH_ACCESS_ROLES}><ContinuousSignalReport /></ProtectedPage>} />
              <Route path="/history" element={<ProtectedPage><HistoryRecords /></ProtectedPage>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Box>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;
