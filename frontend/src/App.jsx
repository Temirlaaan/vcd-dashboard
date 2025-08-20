import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import Sidebar from './components/Sidebar';
import StatsCards from './components/StatsCards';
import Overview from './components/Overview';
import AllocatedIPs from './components/AllocatedIPs';
import FreeIPs from './components/FreeIPs';
import PoolDetails from './components/PoolDetails';
import ConflictAlert from './components/ConflictAlert';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import { RefreshCw, Menu, X, AlertTriangle } from 'lucide-react';
import { formatTime } from './utils/dateUtils';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [refreshing, setRefreshing] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showConflicts, setShowConflicts] = useState(false);

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
      setError('Failed to load data. Please check if the backend is running.');
      console.error('Error loading dashboard data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    // Auto-refresh every 5 minutes
    const interval = setInterval(loadDashboardData, 300000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
  };

  const renderContent = () => {
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

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
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
            <div className="last-update">
              Обновлено: {formatTime(dashboardData.last_update)}
            </div>
            <button 
              className={`refresh-button ${refreshing ? 'refreshing' : ''}`}
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw className={`refresh-icon ${refreshing ? 'spinning' : ''}`} />
              <span className="refresh-text">{refreshing ? 'Обновление...' : 'Обновить'}</span>
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
          {dashboardData && (
            <>
              <StatsCards data={dashboardData} />
              <div className="main-card">
                {renderContent()}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;