import React from 'react';
import { Cloud } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import CopyableIP from './CopyableIP';
import './Overview.css';

const Overview = ({ data }) => {
  const COLORS = ['#667eea', '#34d399', '#fb923c'];

  const getUsageClass = (percentage) => {
    if (percentage < 50) return 'usage-low';
    if (percentage < 80) return 'usage-medium';
    return 'usage-high';
  };

  const chartData = data.clouds.map(cloud => ({
    name: cloud.cloud_name.toUpperCase(),
    value: cloud.used_ips,
    total: cloud.total_ips,
    free: cloud.free_ips
  }));

  return (
    <div className="overview-container">
      <h2 className="section-title">Cloud Infrastructure Overview</h2>

      <div className="overview-grid">
        <div className="chart-section">
          <h3>IP Usage Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={(entry) => `${entry.name}: ${entry.value}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${entry.name}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="clouds-section">
          {data.clouds.map((cloud) => (
            <div key={cloud.cloud_name} className="cloud-card">
              <div className="cloud-header">
                <div className="cloud-title">
                  <Cloud className="cloud-icon" />
                  <h3>{cloud.cloud_name.toUpperCase()}</h3>
                </div>
                <div className="cloud-stats">
                  <div className="cloud-stat">
                    <span className="stat-number">{cloud.total_pools}</span>
                    <span className="stat-label">Pools</span>
                  </div>
                  <div className="cloud-stat">
                    <span className="stat-number">{cloud.total_ips}</span>
                    <span className="stat-label">Total IPs</span>
                  </div>
                </div>
              </div>

              <div className="pools-list">
                {cloud.pools.map((pool) => (
                  <div key={`${cloud.cloud_name}-${pool.name}`} className="pool-item">
                    <div className="pool-info">
                      <div className="pool-name">{pool.name}</div>
                      <div className="pool-network"><CopyableIP ip={pool.network} /></div>
                    </div>
                    <div className="pool-usage">
                      <div className="usage-bar">
                        <div
                          className={`usage-fill ${getUsageClass(pool.usage_percentage ?? 0)}`}
                          style={{ width: `${pool.usage_percentage ?? 0}%` }}
                        >
                          <span className="usage-text">{(pool.usage_percentage ?? 0).toFixed(1)}%</span>
                        </div>
                      </div>
                      <div className="usage-details">
                        <span>Used: {pool.used_ips}/{pool.total_ips}</span>
                        <span className="free-count">Free: {pool.free_ips}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Overview;
