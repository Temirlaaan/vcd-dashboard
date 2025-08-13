import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Copy, CheckCircle } from 'lucide-react';
import './FreeIPs.css';

const FreeIPs = ({ data }) => {
  const [expandedPools, setExpandedPools] = useState({});
  const [copiedIP, setCopiedIP] = useState(null);

  const togglePool = (poolKey) => {
    setExpandedPools(prev => ({
      ...prev,
      [poolKey]: !prev[poolKey]
    }));
  };

  const copyToClipboard = (ip) => {
    navigator.clipboard.writeText(ip);
    setCopiedIP(ip);
    setTimeout(() => setCopiedIP(null), 2000);
  };

  const copyAllIPs = (ips) => {
    const ipList = ips.join('\n');
    navigator.clipboard.writeText(ipList);
    setCopiedIP('all');
    setTimeout(() => setCopiedIP(null), 2000);
  };

  return (
    <div className="free-ips-container">
      <h2 className="section-title">Free IP Addresses</h2>
      
      <div className="summary-cards">
        <div className="summary-card">
          <div className="summary-value">{data.free_ips.toLocaleString()}</div>
          <div className="summary-label">Total Free IPs</div>
        </div>
        <div className="summary-card">
          <div className="summary-value">
            {((data.free_ips / data.total_ips) * 100).toFixed(1)}%
          </div>
          <div className="summary-label">Available</div>
        </div>
      </div>

      <div className="pools-grid">
        {data.clouds.map((cloud) =>
          cloud.pools.map((pool) => {
            const poolKey = `${cloud.cloud_name}-${pool.name}`;
            const isExpanded = expandedPools[poolKey];
            
            if (pool.free_ips === 0) return null;
            
            return (
              <div key={poolKey} className="pool-card">
                <div className="pool-header">
                  <div className="pool-info">
                    <div className="pool-cloud">{cloud.cloud_name.toUpperCase()}</div>
                    <div className="pool-name">{pool.name}</div>
                    <div className="pool-network">{pool.network}</div>
                  </div>
                  <div className="pool-stats">
                    <div className="free-count">{pool.free_ips} free</div>
                    <button
                      className="expand-button"
                      onClick={() => togglePool(poolKey)}
                    >
                      {isExpanded ? <ChevronUp /> : <ChevronDown />}
                    </button>
                  </div>
                </div>
                
                {isExpanded && (
                  <div className="pool-content">
                    <div className="pool-actions">
                      <button
                        className="copy-all-button"
                        onClick={() => copyAllIPs(pool.free_addresses)}
                      >
                        {copiedIP === 'all' ? (
                          <>
                            <CheckCircle size={14} />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy size={14} />
                            Copy All
                          </>
                        )}
                      </button>
                      <span className="ip-count">
                        Showing {Math.min(100, pool.free_addresses.length)} of {pool.free_ips} IPs
                      </span>
                    </div>
                    
                    <div className="ip-grid">
                      {pool.free_addresses.slice(0, 100).map((ip, index) => (
                        <div
                          key={index}
                          className={`ip-item ${copiedIP === ip ? 'copied' : ''}`}
                          onClick={() => copyToClipboard(ip)}
                          title="Click to copy"
                        >
                          {ip}
                          {copiedIP === ip && <CheckCircle className="copied-icon" size={12} />}
                        </div>
                      ))}
                    </div>
                    
                    {pool.free_addresses.length > 100 && (
                      <div className="more-ips">
                        ... and {pool.free_ips - 100} more IPs available
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default FreeIPs;