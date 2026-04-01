export default function LogsTable({ logs }) {
  if (logs.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📋</div>
        <p>No logs yet. Waiting for connections...</p>
      </div>
    );
  }

  return (
    <div className="table-wrapper">
      <table className="logs-table">
        <thead>
          <tr>
            <th>Request ID</th>
            <th>Timestamp</th>
            <th>Client</th>
            <th>Target</th>
            <th>Port Range</th>
            <th>Open</th>
            <th>Scanned</th>
            <th>Duration</th>
            <th>TLS</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td className="td-mono td-id">{log.id}</td>
              <td>{log.timestamp || "-"}</td>
              <td className="td-mono">
                {log.client_ip ? `${log.client_ip}:${log.client_port}` : "-"}
              </td>
              <td>{log.target || "-"}</td>
              <td className="td-mono">{log.port_range || "-"}</td>
              <td>{log.open_ports ?? "-"}</td>
              <td>{log.total_scanned ?? "-"}</td>
              <td>{log.duration !== null && log.duration !== undefined ? `${log.duration}s` : "-"}</td>
              <td className="tls-info">
                {log.tls_version ? (
                  <>
                    <span className="tls-version">{log.tls_version}</span>
                    {log.cipher && <span className="cipher"> / {log.cipher.slice(0, 20)}</span>}
                  </>
                ) : (
                  "-"
                )}
              </td>
              <td>
                <span className={`badge badge--${log.status || "pending"}`}>
                  {log.status || "pending"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
