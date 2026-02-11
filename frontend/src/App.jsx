// frontend/src/App.jsx
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import StatsCards from './components/StatsCards';
import Overview from './components/Overview';
import AllocatedIPs from './components/AllocatedIPs';
import FreeIPs from './components/FreeIPs';
import PoolDetails from './components/PoolDetails';
import ConflictAlert from './components/ConflictAlert';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import { RefreshCw, Menu, X, AlertTriangle, LogOut, User } from 'lucide-react';
import { formatTime } from './utils/dateUtils';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [refreshing, setRefreshing] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showConflicts, setShowConflicts] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);

  // Настройка axios с токеном
  const setupAxios = useCallback((token) => {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }, []);

  const loadDashboardData = useCallback(async () => {
    try {
      setError(null);
      const response = await axios.get(`${API_BASE_URL}/api/dashboard`);
      setDashboardData(response.data);

      if (response.data.conflicts && Object.keys(response.data.conflicts).length > 0) {
        setShowConflicts(true);
      }
    } catch (err) {
      if (err.response && err.response.status === 401) {
        handleLogout();
      } else {
        setError('Failed to load data. Please check if the backend is running.');
        console.error('Error loading dashboard data:', err);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []); // handleLogout is stable — defined below

  // Обработка выхода
  const handleLogout = useCallback(async () => {
    const storedRefresh = localStorage.getItem('refresh_token');
    if (storedRefresh) {
      try {
        await axios.post(`${API_BASE_URL}/api/logout`, { refresh_token: storedRefresh });
      } catch (err) {
        console.error('Logout error:', err);
      }
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    delete axios.defaults.headers.common['Authorization'];
    setIsAuthenticated(false);
    setDashboardData(null);
    setCurrentUser(null);
    setRefreshToken(null);
    setLoading(false);
  }, []);

  // Проверка валидности токена
  const verifyToken = useCallback(async (token) => {
    try {
      setupAxios(token);
      const response = await axios.get(`${API_BASE_URL}/api/verify`);
      if (response.data.valid) {
        setIsAuthenticated(true);
        setCurrentUser(response.data.username);
        await loadDashboardData();
      } else {
        handleLogout();
      }
    } catch (err) {
      console.error('Token verification failed:', err);
      handleLogout();
    }
  }, [setupAxios, loadDashboardData, handleLogout]);

  // Обработка callback (если URL содержит ?code=)
  const handleCallback = useCallback(async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    if (!code) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/callback?code=${encodeURIComponent(code)}`);
      const { access_token, refresh_token } = response.data;

      localStorage.setItem('access_token', access_token);
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token);
      }
      setRefreshToken(refresh_token);

      // Очищаем URL от params
      window.history.replaceState({}, document.title, '/');

      setupAxios(access_token);
      setIsAuthenticated(true);
      await loadDashboardData();
    } catch (err) {
      setError('Failed to exchange code for token.');
      console.error('Callback error:', err);
    } finally {
      setLoading(false);
    }
  }, [setupAxios, loadDashboardData]);

  // Проверка токена при загрузке + обработка callback
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const storedRefresh = localStorage.getItem('refresh_token');
    if (token) {
      setRefreshToken(storedRefresh);
      verifyToken(token);
    } else {
      // handleCallback сам управляет loading state
      handleCallback();
    }
  }, [verifyToken, handleCallback]);

  // Обработка входа (fallback для username/password)
  const handleLogin = (tokenData) => {
    localStorage.setItem('access_token', tokenData.access_token);
    if (tokenData.refresh_token) {
      localStorage.setItem('refresh_token', tokenData.refresh_token);
    }
    setRefreshToken(tokenData.refresh_token);
    setupAxios(tokenData.access_token);
    setIsAuthenticated(true);
    loadDashboardData();
  };

  // Refresh токена + данных
  const handleRefresh = async () => {
    const currentRefresh = refreshToken || localStorage.getItem('refresh_token');
    if (currentRefresh) {
      try {
        setRefreshing(true);
        const response = await axios.post(`${API_BASE_URL}/api/refresh`, {
          refresh_token: currentRefresh
        });
        const { access_token, refresh_token: newRefresh } = response.data;

        localStorage.setItem('access_token', access_token);
        if (newRefresh) localStorage.setItem('refresh_token', newRefresh);
        setRefreshToken(newRefresh || currentRefresh);

        setupAxios(access_token);
        await loadDashboardData();
      } catch (err) {
        console.error('Token refresh failed:', err);
        if (err.response?.status === 401) handleLogout();
      } finally {
        setRefreshing(false);
      }
    } else {
      handleLogout();
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
  };

  const renderContent = () => {
    if (!dashboardData) return null;

    switch (activeTab) {
      case 'overview':
        return <Overview data={dashboardData} />;
      case 'allocations':
        return <AllocatedIPs data={dashboardData} />;
      case 'free':
        return <FreeIPs data={dashboardData} />;
      case 'pools':
        return <PoolDetails data={dashboardData} />;
      default:
        return <Overview data={dashboardData} />;
    }
  };

  if (!isAuthenticated) {
    if (loading) return <LoadingSpinner />;
    return <Login onLogin={handleLogin} />;
  }

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error && !dashboardData) {
    return <ErrorMessage message={error} onRetry={loadDashboardData} />;
  }

  const hasConflicts = dashboardData?.conflicts && Object.keys(dashboardData.conflicts).length > 0;

  return (
    <div className="app">
      {mobileMenuOpen && (
        <div className="mobile-overlay" onClick={() => setMobileMenuOpen(false)} />
      )}

      <Sidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        mobileMenuOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        hasConflicts={hasConflicts}
      />

      <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <header className="app-header">
          <div className="header-left">
            <button
              className="mobile-menu-toggle"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X /> : <Menu />}
            </button>
            <div className="header-title">
              <h1>IP Address Management</h1>
              <p className="header-subtitle">VMware vCloud Director</p>
            </div>
          </div>
          <div className="header-right">
            {hasConflicts && (
              <button
                className="conflict-indicator"
                onClick={() => setShowConflicts(!showConflicts)}
                title={`${Object.keys(dashboardData.conflicts).length} IP conflicts detected`}
              >
                <AlertTriangle />
                <span>{Object.keys(dashboardData.conflicts).length}</span>
              </button>
            )}
            {dashboardData && (
              <div className="last-update">
                Updated: {formatTime(dashboardData.last_update)}
              </div>
            )}
            {currentUser && (
              <div className="user-info">
                <User className="user-icon" size={16} />
                <span className="user-name">{currentUser}</span>
              </div>
            )}
            <button
              className={`refresh-button ${refreshing ? 'refreshing' : ''}`}
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw className={`refresh-icon ${refreshing ? 'spinning' : ''}`} />
              <span className="refresh-text">{refreshing ? 'Updating...' : 'Refresh'}</span>
            </button>
            <button
              className="logout-button"
              onClick={handleLogout}
              title="Logout"
            >
              <LogOut size={18} />
              <span className="logout-text">Logout</span>
            </button>
          </div>
        </header>

        {showConflicts && hasConflicts && (
          <ConflictAlert
            conflicts={dashboardData.conflicts}
            onClose={() => setShowConflicts(false)}
          />
        )}

        <div className="content-wrapper">
          {dashboardData ? (
            <>
              <StatsCards data={dashboardData} />
              <div className="main-card">
                {renderContent()}
              </div>
            </>
          ) : (
            <div className="main-card">
              <p style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                No data available. Please try refreshing.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
