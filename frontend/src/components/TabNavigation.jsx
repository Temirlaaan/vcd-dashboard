import React from 'react';
import { Eye, List, Grid, Database } from 'lucide-react';
import './TabNavigation.css';

const TabNavigation = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'overview', label: 'Overview', icon: <Eye /> },
    { id: 'allocations', label: 'Allocated IPs', icon: <List /> },
    { id: 'free', label: 'Free IPs', icon: <Grid /> },
    { id: 'pools', label: 'Pool Details', icon: <Database /> }
  ];

  return (
    <div className="tab-navigation">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.icon}
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
};

export default TabNavigation;