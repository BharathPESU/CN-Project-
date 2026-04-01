export default function Filters({ filters, onChange, onClear, logs }) {
  const uniqueIps = [...new Set(logs.map((log) => log.client_ip).filter(Boolean))].sort();
  const uniqueTargets = [...new Set(logs.map((log) => log.target).filter(Boolean))].sort();

  return (
    <div className="filters">
      <select
        className="filter-select"
        value={filters.clientIp}
        onChange={(e) => onChange({ ...filters, clientIp: e.target.value })}
      >
        <option value="">All Client IPs</option>
        {uniqueIps.map((ip) => (
          <option key={ip} value={ip}>{ip}</option>
        ))}
      </select>
      <select
        className="filter-select"
        value={filters.target}
        onChange={(e) => onChange({ ...filters, target: e.target.value })}
      >
        <option value="">All Targets</option>
        {uniqueTargets.map((target) => (
          <option key={target} value={target}>{target}</option>
        ))}
      </select>
      <select
        className="filter-select"
        value={filters.status}
        onChange={(e) => onChange({ ...filters, status: e.target.value })}
      >
        <option value="">All Statuses</option>
        <option value="complete">Complete</option>
        <option value="pending">Pending</option>
        <option value="failed">Failed</option>
      </select>
      <button className="btn btn--secondary" onClick={onClear}>
        Clear Filters
      </button>
    </div>
  );
}
