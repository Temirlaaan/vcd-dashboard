import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Database, TrendingUp, TrendingDown } from 'lucide-react';
import CopyableIP from './CopyableIP';
import './PoolDetails.css';

const PoolDetails = ({ data }) => {
  const getUsageColor = (percentage) => {
    if (percentage < 50) return '#34d399';
    if (percentage < 80) return '#fbbf24';
    return '#f87171';
  };

  const chartData = [];
  data.clouds.forEach(cloud => {
    cloud.pools.forEach(pool => {
      chartData.push({
        name: `${cloud.cloud_name.toUpperCase()}-${pool.name.split('/')[0]}`,
        used: pool.used_ips,
        free: pool.free_ips,
        total: pool.total_ips,
        percentage: pool.usage_percentage
      });
    });
  });

  return (
    <div className="pool-details-container">
      <h2 className="section-title">
        <Database />
        Pool Details & Analytics
      </h2>

      <div className="chart-section">
        <h3>IP Usage by Pool</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="used" stackId="a" fill="#f87171" name="Used IPs" />
            <Bar dataKey="free" stackId="a" fill="#34d399" name="Free IPs" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="details-grid">
        {data.clouds.map((cloud) => (
          <div key={cloud.cloud_name} className="cloud-details">
            <h3 className="cloud-name">{cloud.cloud_name.toUpperCase()}</h3>

            <div className="pools-table">
              <table>
                <thead>
                  <tr>
                    <th>Pool Name</th>
                    <th>Network</th>
                    <th>Total IPs</th>
                    <th>Used</th>
                    <th>Free</th>
                    <th>Usage</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {cloud.pools.map((pool) => (
                    <tr key={`${cloud.cloud_name}-${pool.name}`}>
                      <td className="pool-name-cell">{pool.name}</td>
                      <td>
                        <CopyableIP ip={pool.network} />
                      </td>
                      <td className="number-cell">{pool.total_ips}</td>
                      <td className="number-cell">{pool.used_ips}</td>
                      <td className="number-cell free-cell">{pool.free_ips}</td>
                      <td>
                        <div className="usage-cell">
                          <div className="usage-bar-mini">
                            <div
                              className="usage-fill-mini"
                              style={{
                                width: `${pool.usage_percentage ?? 0}%`,
                                backgroundColor: getUsageColor(pool.usage_percentage ?? 0)
                              }}
                            />
                          </div>
                          <span className="usage-percentage">
                            {(pool.usage_percentage ?? 0).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td>
                        {(pool.usage_percentage ?? 0) > 80 ? (
                          <span className="status-badge critical">
                            <TrendingUp size={14} />
                            Critical
                          </span>
                        ) : (pool.usage_percentage ?? 0) > 50 ? (
                          <span className="status-badge warning">
                            <TrendingUp size={14} />
                            Warning
                          </span>
                        ) : (
                          <span className="status-badge healthy">
                            <TrendingDown size={14} />
                            Healthy
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="cloud-summary">
              <div className="summary-item">
                <span className="summary-label">Total Capacity:</span>
                <span className="summary-value">{cloud.total_ips} IPs</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Overall Usage:</span>
                <span className="summary-value">{(cloud.usage_percentage ?? 0).toFixed(1)}%</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Available IPs:</span>
                <span className="summary-value free">{cloud.free_ips}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PoolDetails;
