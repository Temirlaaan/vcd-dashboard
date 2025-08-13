import React, { useState, useMemo } from 'react';
import { Search, Filter, Download } from 'lucide-react';
import './AllocatedIPs.css';

const AllocatedIPs = ({ data }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [cloudFilter, setCloudFilter] = useState('all');
  const [sortField, setSortField] = useState('ip_address');
  const [sortDirection, setSortDirection] = useState('asc');

  const filteredAndSortedData = useMemo(() => {
    let filtered = data.all_allocations;

    // Apply search filter
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(item =>
        item.ip_address.toLowerCase().includes(search) ||
        item.org_name.toLowerCase().includes(search) ||
        item.pool_name.toLowerCase().includes(search) ||
        (item.entity_name && item.entity_name.toLowerCase().includes(search))
      );
    }

    // Apply cloud filter
    if (cloudFilter !== 'all') {
      filtered = filtered.filter(item => item.cloud_name === cloudFilter);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aVal = a[sortField] || '';
      let bVal = b[sortField] || '';
      
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
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

  const exportToCSV = () => {
    const headers = ['IP Address', 'Organization', 'Cloud', 'Pool', 'Type', 'Entity'];
    const rows = filteredAndSortedData.map(item => [
      item.ip_address,
      item.org_name,
      item.cloud_name,
      item.pool_name,
      item.allocation_type,
      item.entity_name || ''
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `allocated_ips_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  return (
    <div className="allocated-ips-container">
      <div className="section-header">
        <h2>Allocated IP Addresses</h2>
        <button className="export-button" onClick={exportToCSV}>
          <Download size={16} />
          Export CSV
        </button>
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
            onChange={(e) => setCloudFilter(e.target.value)}
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
                  <span className="sort-indicator">{sortDirection === 'asc' ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('org_name')} className="sortable">
                Organization
                {sortField === 'org_name' && (
                  <span className="sort-indicator">{sortDirection === 'asc' ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('cloud_name')} className="sortable">
                Cloud
                {sortField === 'cloud_name' && (
                  <span className="sort-indicator">{sortDirection === 'asc' ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('pool_name')} className="sortable">
                Pool
                {sortField === 'pool_name' && (
                  <span className="sort-indicator">{sortDirection === 'asc' ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th>Type</th>
              <th>Entity</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedData.map((allocation, index) => (
              <tr key={index}>
                <td>
                  <span className="ip-address">{allocation.ip_address}</span>
                </td>
                <td>
                  <span className="org-name">{allocation.org_name}</span>
                </td>
                <td>
                  <span className="cloud-badge">{allocation.cloud_name.toUpperCase()}</span>
                </td>
                <td>{allocation.pool_name}</td>
                <td>
                  <span className="type-badge">{allocation.allocation_type}</span>
                </td>
                <td>{allocation.entity_name || '-'}</td>
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