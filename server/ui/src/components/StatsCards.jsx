export default function StatsCards({ logs }) {
  const stats = logs.reduce(
    (acc, log) => {
      acc.totalRequests += 1;
      if (log.open_ports !== null && log.open_ports !== undefined) {
        acc.openPorts += log.open_ports;
      }
      if (log.total_scanned !== null && log.total_scanned !== undefined) {
        acc.closedPorts += Math.max(log.total_scanned - (log.open_ports || 0), 0);
      }
      if (log.duration !== null && log.duration !== undefined) {
        acc.totalDuration += log.duration;
        acc.durationCount += 1;
      }
      return acc;
    },
    { totalRequests: 0, openPorts: 0, closedPorts: 0, totalDuration: 0, durationCount: 0 }
  );

  const avgDuration = stats.durationCount > 0 
    ? (stats.totalDuration / stats.durationCount).toFixed(3) 
    : "0.000";

  return (
    <div className="stats-grid">
      <div className="stat-card stat-card--blue">
        <span className="stat-icon">📊</span>
        <div className="stat-content">
          <span className="stat-label">Total Requests</span>
          <span className="stat-value">{stats.totalRequests}</span>
        </div>
      </div>
      <div className="stat-card stat-card--green">
        <span className="stat-icon">🔓</span>
        <div className="stat-content">
          <span className="stat-label">Open Ports</span>
          <span className="stat-value">{stats.openPorts}</span>
        </div>
      </div>
      <div className="stat-card stat-card--red">
        <span className="stat-icon">🔒</span>
        <div className="stat-content">
          <span className="stat-label">Closed Ports</span>
          <span className="stat-value">{stats.closedPorts}</span>
        </div>
      </div>
      <div className="stat-card stat-card--yellow">
        <span className="stat-icon">⏱️</span>
        <div className="stat-content">
          <span className="stat-label">Avg Duration</span>
          <span className="stat-value">{avgDuration}s</span>
        </div>
      </div>
    </div>
  );
}
