import React, { useState, useEffect } from 'react';
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

  // Проверка токена при загрузке
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      verifyToken(token);
    } else {
      setLoading(false);
    }
  }, []);

  // Настройка axios с токеном
  const setupAxios = (token) => {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  };

  // Проверка валидности токена
  const verifyToken = async (token) => {
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
  };

  // Обработка входа
  const handleLogin = (token) => {
    localStorage.setItem('token', token);
    setupAxios(token);
    setIsAuthenticated(true);
    loadDashboardData();
  };

  // Обработка выхода
  const handleLogout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setIsAuthenticated(false);
    setDashboardData(null);
    setCurrentUser(null);
    setLoading(false);
  };

  const loadDashboardData = async () => {
    try {
      setError(null);
      const response = await axios.get(`${API_BASE_URL}/api/dashboard`);
      setDashboardData(response.data);
      
      // Проверяем наличие конфликтов
      if (response.data.conflicts && Object.keys(response.data.conflicts).length > 0) {
        setShowConflicts(true);
      }
    } catch (err) {
      if (err.response && err.response.status === 401) {
        // Token expired or invalid
        handleLogout();
      } else {
        setError('Failed to load data. Please check if the backend is running.');
        console.error('Error loading dashboard data:', err);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
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

  // Если не авторизован, показываем форму входа
  if (!isAuthenticated) {
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
      {/* Mobile menu overlay */}
      {mobileMenuOpen && (
        <div className="mobile-overlay" onClick={() => setMobileMenuOpen(false)} />
      )}

      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        mobileMenuOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        hasConflicts={hasConflicts}
      />

      {/* Main Content */}
      <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        {/* Header */}
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
                title={`${Object.keys(dashboardData.conflicts).length} IP конфликтов обнаружено`}
              >
                <AlertTriangle />
                <span>{Object.keys(dashboardData.conflicts).length}</span>
              </button>
            )}
            {dashboardData && (
              <div className="last-update">
                Обновлено: {formatTime(dashboardData.last_update)}
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
              <span className="refresh-text">{refreshing ? 'Обновление...' : 'Обновить'}</span>
            </button>
            <button 
              className="logout-button"
              onClick={handleLogout}
              title="Выйти"
            >
              <LogOut size={18} />
              <span className="logout-text">Выйти</span>
            </button>
          </div>
        </header>

        {/* Conflict Alert */}
        {showConflicts && hasConflicts && (
          <ConflictAlert 
            conflicts={dashboardData.conflicts}
            onClose={() => setShowConflicts(false)}
          />
        )}

        {/* Content Area */}
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