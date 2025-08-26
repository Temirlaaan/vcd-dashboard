import React from 'react';
import { Cloud, Eye, List, Grid, Database, ChevronLeft, ChevronRight, Activity, Shield, X } from 'lucide-react';
import './Sidebar.css';

const Sidebar = ({ activeTab, onTabChange, collapsed, onToggleCollapse, mobileMenuOpen, onCloseMobile }) => {
  const menuItems = [
    { id: 'overview', label: 'Overview', icon: <Eye />, description: 'General statistics' },
    { id: 'allocations', label: 'Allocated IPs', icon: <List />, description: 'Used addresses' },
    { id: 'free', label: 'Free IPs', icon: <Grid />, description: 'Available pool' },
    { id: 'pools', label: 'Pool Details', icon: <Database />, description: 'Detailed analysis' }
  ];

  return (
    <div className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileMenuOpen ? 'mobile-open' : ''}`}>
      {/* Logo Section */}
      <div className="sidebar-header">
        <div className="logo-container">
          <Cloud className="logo-icon" />
          {!collapsed && (
            <div className="logo-text">
              <span className="logo-title">VCD Manager</span>
              <span className="logo-subtitle">IP Management</span>
            </div>
          )}
        </div>
        <button className="mobile-close" onClick={onCloseMobile}>
          <X />
        </button>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section">
          {!collapsed && <div className="nav-section-title">Navigation</div>}
          {menuItems.map(item => (
            <button
              key={item.id}
              className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => onTabChange(item.id)}
              title={collapsed ? item.label : ''}
            >
              <span className="nav-icon">{item.icon}</span>
              {!collapsed && (
                <div className="nav-content">
                  <span className="nav-label">{item.label}</span>
                  <span className="nav-description">{item.description}</span>
                </div>
              )}
            </button>
          ))}
        </div>

        {!collapsed && (
          <div className="nav-section">
            <div className="nav-section-title">Quick Stats</div>
            <div className="sidebar-stats">
              <div className="stat-item">
                <Activity className="stat-icon" />
                <div className="stat-info">
                  <span className="stat-label">Status</span>
                  <span className="stat-value">Active</span>
                </div>
              </div>
              <div className="stat-item">
              
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* Collapse Toggle */}
      <div className="sidebar-footer">
        <button className="collapse-toggle" onClick={onToggleCollapse}>
          {collapsed ? <ChevronRight /> : <ChevronLeft />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </div>
  );
};

export default Sidebar;