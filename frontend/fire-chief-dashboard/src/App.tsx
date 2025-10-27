import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';

import { RootState } from './store/store';
import { checkAuthStatus } from './store/slices/authSlice';
import LoginPage from './pages/LoginPage';
import DashboardLayout from './components/Layout/DashboardLayout';
import DashboardPage from './pages/DashboardPage';
import IncidentsPage from './pages/IncidentsPage';
import ResourcesPage from './pages/ResourcesPage';
import AlertsPage from './pages/AlertsPage';
import ReportsPage from './pages/ReportsPage';
import DataPortalPage from './pages/DataPortalPage';
import WildfireSituationalAwarenessPage from './pages/WildfireSituationalAwarenessPage';
import VisualizationsPage from './pages/VisualizationsPage';
import DataCatalogPage from './pages/DataCatalogPage';
import SecurityGovernancePage from './pages/SecurityGovernancePage';
import SplitScreenFireChiefDashboard from './pages/SplitScreenFireChiefDashboard';
import ComprehensiveSplitScreenDashboard from './pages/ComprehensiveSplitScreenDashboard';
import LoadingScreen from './components/Common/LoadingScreen';

function App() {
  const dispatch = useDispatch();
  const { isAuthenticated, isLoading } = useSelector((state: RootState) => state.auth);

  useEffect(() => {
    dispatch(checkAuthStatus() as any);
  }, [dispatch]);

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Box sx={{ display: 'flex' }}>
      <DashboardLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/resources" element={<ResourcesPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/data-portal" element={<DataPortalPage />} />
          <Route path="/situational-awareness" element={<WildfireSituationalAwarenessPage />} />
          <Route path="/visualizations" element={<VisualizationsPage />} />
          <Route path="/data-catalog" element={<DataCatalogPage />} />
          <Route path="/security-governance" element={<SecurityGovernancePage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </DashboardLayout>
    </Box>
  );
}

export default App;