import React, { lazy, useEffect, useState } from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';

import Navigation from './components/Navigation';
import RouteExperience, { PageNotFound } from './components/RouteExperience';
import sessionManager from './utils/sessionManager';
import { checkAuthStatus } from './utils/auth';
import { RESEARCH_ACCESS_ROLES, CLINICAL_WRITE_ROLES } from './utils/roles';
import appTheme from './config/theme';
import './App.css';

const ProtectedRoute = lazy(() => import('./components/ProtectedRoute'));
const LandingPage = lazy(() => import('./components/LandingPage'));
const Dashboard = lazy(() => import('./components/Dashboard'));
const Login = lazy(() => import('./components/Login'));
const Register = lazy(() => import('./components/Register'));
const Launch = lazy(() => import('./components/Launch'));
const HealthDataInput = lazy(() => import('./components/HealthDataInput'));
const RiskAnalysis = lazy(() => import('./components/RiskAnalysis'));
const ResearchCohorts = lazy(() => import('./components/ResearchCohorts'));
const ResearchReports = lazy(() => import('./components/ResearchReports'));
const ContinuousSignalReport = lazy(() => import('./components/ContinuousSignalReport'));
const BulkHealthDataImport = lazy(() => import('./components/BulkHealthDataImport'));
const PatientManagement = lazy(() => import('./components/PatientManagement'));
const PatientChart = lazy(() => import('./components/PatientChart'));
const HistoryRecords = lazy(() => import('./components/HistoryRecords'));


function ProtectedPage({ children, allowedRoles = [] }) {
  return <ProtectedRoute allowedRoles={allowedRoles}>{children}</ProtectedRoute>;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

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
    <ThemeProvider theme={appTheme}>
      <CssBaseline />
      <Router>
        <Box className="app-shell">
          <a className="atlas-skip" href="#main-content">跳至主要內容</a>
          <Navigation />
          <Box component="main" id="main-content" tabIndex={-1} className={isAuthenticated ? 'app-main app-main-authenticated' : 'app-main'}>
            <RouteExperience>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/launch" element={<Launch />} />
                <Route path="/dashboard" element={<ProtectedPage><Dashboard /></ProtectedPage>} />
                <Route path="/patients" element={<ProtectedPage><PatientManagement /></ProtectedPage>} />
                <Route path="/patients/:patientId" element={<ProtectedPage><PatientChart /></ProtectedPage>} />
                <Route path="/health-data-input" element={<ProtectedPage allowedRoles={CLINICAL_WRITE_ROLES}><HealthDataInput /></ProtectedPage>} />
                <Route path="/bulk-import" element={<ProtectedPage allowedRoles={CLINICAL_WRITE_ROLES}><BulkHealthDataImport /></ProtectedPage>} />
                <Route path="/disease-network" element={<ProtectedPage><RiskAnalysis network /></ProtectedPage>} />
                <Route path="/risk-analysis" element={<ProtectedPage><RiskAnalysis /></ProtectedPage>} />
                <Route path="/research-cohorts" element={<ProtectedPage allowedRoles={RESEARCH_ACCESS_ROLES}><ResearchCohorts /></ProtectedPage>} />
                <Route path="/research-reports" element={<ProtectedPage allowedRoles={RESEARCH_ACCESS_ROLES}><ResearchReports /></ProtectedPage>} />
                <Route path="/research-continuous-signals" element={<ProtectedPage allowedRoles={RESEARCH_ACCESS_ROLES}><ContinuousSignalReport /></ProtectedPage>} />
                <Route path="/history" element={<ProtectedPage><HistoryRecords /></ProtectedPage>} />
                <Route path="*" element={<PageNotFound />} />
              </Routes>
            </RouteExperience>
          </Box>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;
