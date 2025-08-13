import React from 'react';
import { Cloud, Server, CheckCircle, AlertCircle } from 'lucide-react';
import './StatsCards.css';

const StatsCards = ({ data }) => {
  const getUsageClass = (percentage) => {
    if (percentage < 50) return 'low';
    if (percentage < 80) return 'medium';
    return 'high';
  };

  const stats = [
    {
      icon: <Cloud />,
      label: 'Total Clouds',
      value: data.total_clouds,
      color: 'blue'
    },
    {
      icon: <Server />,
      label: 'Total IP Addresses',
      value: data.total_ips,
      color: 'purple'
    },
    {
      icon: <AlertCircle />,
      label: 'Used IPs',
      value: data.used_ips,
      percentage: data.usage_percentage,
      color: 'orange'
    },
    {
      icon: <CheckCircle />,
      label: 'Free IPs',
      value: data.free_ips,
      color: 'green'
    }
  ];

  return (
    <div className="stats-grid">
      {stats.map((stat, index) => (
        <div key={index} className={`stat-card stat-${stat.color}`}>
          <div className="stat-icon">
            {stat.icon}
          </div>
          <div className="stat-content">
            <div className="stat-label">{stat.label}</div>
            <div className="stat-value">{stat.value.toLocaleString()}</div>
            {stat.percentage !== undefined && (
              <div className={`stat-percentage ${getUsageClass(stat.percentage)}`}>
                {stat.percentage.toFixed(1)}% used
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default StatsCards;