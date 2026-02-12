import React, { useState, useMemo, useRef, useEffect } from 'react';
import { Search, Filter, Download, ChevronDown } from 'lucide-react';
import CopyableIP from './CopyableIP';
import './AllocatedIPs.css';

const AllocatedIPs = ({ data }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [cloudFilter, setCloudFilter] = useState('all');
  const [sortField, setSortField] = useState('ip_address');
  const [sortDirection, setSortDirection] = useState('asc');
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exportPoolFilter, setExportPoolFilter] = useState('all');
  const exportMenuRef = useRef(null);

  // Close export menu on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target)) {
        setShowExportMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredAndSortedData = useMemo(() => {
    let filtered = [...data.all_allocations];

    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(item =>
        item.ip_address.toLowerCase().includes(search) ||
        item.org_name.toLowerCase().includes(search) ||
        item.pool_name.toLowerCase().includes(search) ||
        (item.entity_name && item.entity_name.toLowerCase().includes(search))
      );
    }

    if (cloudFilter !== 'all') {
      filtered = filtered.filter(item => item.cloud_name === cloudFilter);
    }

    filtered.sort((a, b) => {
      let aVal = a[sortField] ?? '';
      let bVal = b[sortField] ?? '';

      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [data.all_allocations, searchTerm, cloudFilter, sortField, sortDirection]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const escapeCell = (cell) => `"${String(cell).replace(/"/g, '""')}"`;

  const downloadCSV = (csvContent, filename) => {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const exportAllocatedCSV = () => {
    const headers = ['IP Address', 'Organization', 'Cloud', 'Pool', 'Type', 'Entity'];
    const rows = filteredAndSortedData.map(item => [
      item.ip_address, item.org_name, item.cloud_name, item.pool_name,
      item.allocation_type, item.entity_name || ''
    ]);

    const csvContent = [headers.join(','), ...rows.map(row => row.map(escapeCell).join(','))].join('\n');
    const suffix = cloudFilter !== 'all' ? `_${cloudFilter}` : '';
    downloadCSV(csvContent, `allocated_ips${suffix}_${new Date().toISOString().split('T')[0]}.csv`);
    setShowExportMenu(false);
  };

  const exportFreeCSV = () => {
    const headers = ['IP Address', 'Cloud', 'Pool', 'Network'];
    const rows = [];

    data.clouds.forEach(cloud => {
      if (cloudFilter !== 'all' && cloud.cloud_name !== cloudFilter) return;
      cloud.pools.forEach(pool => {
        if (exportPoolFilter !== 'all' && pool.name !== exportPoolFilter) return;
        pool.free_addresses.forEach(ip => {
          rows.push([ip, cloud.cloud_name, pool.name, pool.network]);
        });
      });
    });

    const csvContent = [headers.join(','), ...rows.map(row => row.map(escapeCell).join(','))].join('\n');
    const suffix = cloudFilter !== 'all' ? `_${cloudFilter}` : '';
    downloadCSV(csvContent, `free_ips${suffix}_${new Date().toISOString().split('T')[0]}.csv`);
    setShowExportMenu(false);
  };

  const exportAllCSV = () => {
    const headers = ['IP Address', 'Status', 'Organization', 'Cloud', 'Pool', 'Network', 'Type', 'Entity'];
    const rows = [];

    // Add allocated
    filteredAndSortedData.forEach(item => {
      rows.push([item.ip_address, 'Allocated', item.org_name, item.cloud_name,
        item.pool_name, '', item.allocation_type, item.entity_name || '']);
    });

    // Add free
    data.clouds.forEach(cloud => {
      if (cloudFilter !== 'all' && cloud.cloud_name !== cloudFilter) return;
      cloud.pools.forEach(pool => {
        if (exportPoolFilter !== 'all' && pool.name !== exportPoolFilter) return;
        pool.free_addresses.forEach(ip => {
          rows.push([ip, 'Free', '', cloud.cloud_name, pool.name, pool.network, '', '']);
        });
      });
    });

    const csvContent = [headers.join(','), ...rows.map(row => row.map(escapeCell).join(','))].join('\n');
    const suffix = cloudFilter !== 'all' ? `_${cloudFilter}` : '';
    downloadCSV(csvContent, `all_ips${suffix}_${new Date().toISOString().split('T')[0]}.csv`);
    setShowExportMenu(false);
  };

  // Get available pools for current cloud filter
  const availablePools = useMemo(() => {
    const pools = [];
    data.clouds.forEach(cloud => {
      if (cloudFilter !== 'all' && cloud.cloud_name !== cloudFilter) return;
      cloud.pools.forEach(pool => {
        pools.push({ name: pool.name, cloud: cloud.cloud_name });
      });
    });
    return pools;
  }, [data.clouds, cloudFilter]);

  return (
    <div className="allocated-ips-container">
      <div className="section-header">
        <h2>Allocated IP Addresses</h2>
        <div className="export-dropdown" ref={exportMenuRef}>
          <button className="export-button" onClick={() => setShowExportMenu(!showExportMenu)}>
            <Download size={16} />
            Export CSV
            <ChevronDown size={14} />
          </button>
          {showExportMenu && (
            <div className="export-menu">
              <div className="export-menu-filter">
                <label>Pool filter:</label>
                <select
                  value={exportPoolFilter}
                  onChange={(e) => setExportPoolFilter(e.target.value)}
                >
                  <option value="all">All Pools</option>
                  {availablePools.map(pool => (
                    <option key={`${pool.cloud}-${pool.name}`} value={pool.name}>
                      {pool.cloud.toUpperCase()} - {pool.name}
                    </option>
                  ))}
                </select>
              </div>
              <button className="export-menu-item" onClick={exportAllocatedCSV}>
                <Download size={14} />
                Allocated IPs
                <span className="export-count">{filteredAndSortedData.length}</span>
              </button>
              <button className="export-menu-item" onClick={exportFreeCSV}>
                <Download size={14} />
                Free IPs
              </button>
              <button className="export-menu-item" onClick={exportAllCSV}>
                <Download size={14} />
                All IPs (Allocated + Free)
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="filters-section">
        <div className="search-box">
          <Search className="search-icon" />
          <input
            type="text"
            placeholder="Search by IP, Organization, Pool, or Entity..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="filter-group">
          <Filter className="filter-icon" />
          <select
            value={cloudFilter}
            onChange={(e) => { setCloudFilter(e.target.value); setExportPoolFilter('all'); }}
            className="filter-select"
          >
            <option value="all">All Clouds</option>
            {data.clouds.map(cloud => (
              <option key={cloud.cloud_name} value={cloud.cloud_name}>
                {cloud.cloud_name.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="results-info">
        Showing {filteredAndSortedData.length} of {data.all_allocations.length} allocations
      </div>

      <div className="table-container">
        <table className="allocations-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('ip_address')} className="sortable">
                IP Address
                {sortField === 'ip_address' && (
                  <span className="sort-indicator">{sortDirection === 'asc' ? ' \u2191' : ' \u2193'}</span>
                )}
              </th>
              <th onClick={() => handleSort('org_name')} className="sortable">
                Organization
                {sortField === 'org_name' && (
                  <span className="sort-indicator">{sortDirection === 'asc' ? ' \u2191' : ' \u2193'}</span>
                )}
              </th>
              <th onClick={() => handleSort('cloud_name')} className="sortable">
                Cloud
                {sortField === 'cloud_name' && (
                  <span className="sort-indicator">{sortDirection === 'asc' ? ' \u2191' : ' \u2193'}</span>
                )}
              </th>
              <th onClick={() => handleSort('pool_name')} className="sortable">
                Pool
                {sortField === 'pool_name' && (
                  <span className="sort-indicator">{sortDirection === 'asc' ? ' \u2191' : ' \u2193'}</span>
                )}
              </th>
              <th>Type</th>
              <th>Entity</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedData.map((allocation, index) => (
              <tr key={`${index}-${allocation.ip_address}-${allocation.cloud_name}-${allocation.pool_name}`}>
                <td>
                  <CopyableIP ip={allocation.ip_address} />
                </td>
                <td>
                  <span className="org-name">{allocation.org_name}</span>
                </td>
                <td>
                  <span className="cloud-badge">{allocation.cloud_name.toUpperCase()}</span>
                </td>
                <td>{allocation.pool_name}</td>
                <td>
                  <span className={`type-badge type-${allocation.allocation_type.toLowerCase()}`}>
                    {allocation.allocation_type}
                  </span>
                </td>
                <td>
                  {allocation.entity_name || '-'}
                  {allocation.allocation_type === 'VM_ALLOCATED' && allocation.vapp_name && (
                    <div className="entity-details">
                      <small>vApp: {allocation.vapp_name}</small>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredAndSortedData.length === 0 && (
          <div className="no-results">
            No allocations found matching your criteria
          </div>
        )}
      </div>
    </div>
  );
};

export default AllocatedIPs;
