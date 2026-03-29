import { useState } from "react";
import axios from "axios";
import ScanForm from "./components/ScanForm";
import ResultsTable from "./components/ResultsTable";
import LoadingSpinner from "./components/LoadingSpinner";
import StatsPanel from "./components/StatsPanel";

// Base URL for the FastAPI backend.
// In development Vite proxies /scan → http://localhost:8000/scan.
// In production, set VITE_API_BASE in your environment.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export default function App() {
  const [scanMeta, setScanMeta]   = useState(null);   // scan summary info
  const [results, setResults]     = useState([]);      // array of port result dicts
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);

  /**
   * Called by ScanForm when the user submits valid input.
   * Sends a GET request to /scan and stores the results.
   */
  async function handleScan({ target, startPort, endPort, useTlsServer, tlsHost, tlsPort }) {
    setLoading(true);
    setError(null);
    setResults([]);
    setScanMeta(null);

    try {
      const params = {
        target,
        start_port: startPort,
        end_port: endPort,
      };
      if (useTlsServer) {
        params.use_tls_server = true;
        params.tls_server_host = tlsHost;
        params.tls_server_port = tlsPort;
      }

      const { data } = await axios.get(`${API_BASE}/scan`, { params });

      setResults(data.results ?? []);
      setScanMeta({
        target:          data.target,
        resolvedIp:      data.resolved_ip,
        openPorts:       data.open_ports,
        totalScanned:    data.total_scanned,
        durationSeconds: data.scan_duration_seconds,
      });
    } catch (err) {
      const detail =
        err.response?.data?.detail ??
        err.response?.data?.message ??
        err.message ??
        "An unexpected error occurred.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-wrapper">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <header className="app-header">
        <span className="header-icon">🔍</span>
        <div>
          <h1 className="header-title">TCP Port Scanner</h1>
          <p className="header-subtitle">
            Scan open ports, detect services &amp; capture banners
          </p>
        </div>
      </header>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <main className="app-main">
        <ScanForm onScan={handleScan} disabled={loading} />

        {/* Error banner */}
        {error && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon">⚠️</span>
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && <LoadingSpinner />}

        {/* Stats panel (replaces plain summary badges) */}
        {scanMeta && !loading && (
          <StatsPanel scanMeta={scanMeta} results={results} />
        )}

        {/* Results table */}
        {results.length > 0 && !loading && (
          <ResultsTable results={results} />
        )}

        {/* Empty state after a completed scan with zero results */}
        {scanMeta && results.length === 0 && !loading && (
          <div className="empty-state">
            <span className="empty-icon">🔒</span>
            <p>No ports found in the scanned range.</p>
          </div>
        )}
      </main>
    </div>
  );
}
