import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import Dashboard from './components/Dashboard';
import StatsCards from './components/StatsCards';
import TabNavigation from './components/TabNavigation';
import Overview from './components/Overview';
import AllocatedIPs from './components/AllocatedIPs';
import FreeIPs from './components/FreeIPs';
import PoolDetails from './components/PoolDetails';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import { RefreshCw, Cloud } from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboardData = async () => {
    try {
      setError(null);
      const response = await axios.get(`${API_BASE_URL}/api/dashboard`);
      setDashboardData(response.data);
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

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-title">
            <Cloud className="header-icon" />
            <div>
              <h1>VCD IP Manager</h1>
              <p className="header-subtitle">VMware vCloud Director - IP Address Management</p>
            </div>
          </div>
          <button 
            className={`refresh-button ${refreshing ? 'refreshing' : ''}`}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`refresh-icon ${refreshing ? 'spinning' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </div>
      </header>

      <div className="app-content">
        {dashboardData && (
          <>
            <StatsCards data={dashboardData} />
            <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
            <div className="tab-content">
              {renderContent()}
            </div>
          </>
        )}
      </div>

      {dashboardData && (
        <footer className="app-footer">
          <span>Last updated: {new Date(dashboardData.last_update).toLocaleString()}</span>
          <span>•</span>
          <span>{dashboardData.total_clouds} clouds monitored</span>
        </footer>
      )}
    </div>
  );
}

export default App;