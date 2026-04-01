import { useState, useMemo } from "react";
import useWebSocket from "./hooks/useWebSocket";
import ConnectionStatus from "./components/ConnectionStatus";
import StatsCards from "./components/StatsCards";
import Filters from "./components/Filters";
import LogsTable from "./components/LogsTable";

const WS_URL = `ws://${window.location.hostname}:8080/ws/logs`;

export default function App() {
  const { logs, status, clearLogs } = useWebSocket(WS_URL);
  const [filters, setFilters] = useState({ clientIp: "", target: "", status: "" });

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (filters.clientIp && log.client_ip !== filters.clientIp) return false;
      if (filters.target && log.target !== filters.target) return false;
      if (filters.status && log.status !== filters.status) return false;
      return true;
    });
  }, [logs, filters]);

  const handleClearFilters = () => {
    setFilters({ clientIp: "", target: "", status: "" });
  };

  return (
    <div className="app-wrapper">
      <header className="app-header">
        <div className="header-left">
          <span className="header-icon">🔐</span>
          <div>
            <h1 className="header-title">TLS Server Logs</h1>
            <p className="header-subtitle">Real-time connection monitoring</p>
          </div>
        </div>
        <ConnectionStatus status={status} />
      </header>

      <main className="app-main">
        <section className="card">
          <h2 className="card-title">Statistics</h2>
          <StatsCards logs={filteredLogs} />
        </section>

        <section className="card">
          <h2 className="card-title">Filters</h2>
          <Filters filters={filters} onChange={setFilters} onClear={handleClearFilters} logs={logs} />
        </section>

        <section className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h2 className="card-title" style={{ marginBottom: 0 }}>
              Connection Logs ({filteredLogs.length})
            </h2>
            <button className="btn btn--secondary" onClick={clearLogs}>
              Clear Logs
            </button>
          </div>
          <LogsTable logs={filteredLogs} />
        </section>
      </main>
    </div>
  );
}
