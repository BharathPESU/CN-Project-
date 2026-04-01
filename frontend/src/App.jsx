import { useState, useRef } from "react";
import ScanForm from "./components/ScanForm";
import ResultsTable from "./components/ResultsTable";
import LoadingSpinner from "./components/LoadingSpinner";
import StatsPanel from "./components/StatsPanel";
import PerformancePanel from "./components/PerformancePanel";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export default function App() {
  const [scanMeta, setScanMeta] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [scanHistory, setScanHistory] = useState([]);
  const [batchThroughputs, setBatchThroughputs] = useState([]);
  const [progress, setProgress] = useState(0);
  const eventSourceRef = useRef(null);

  function handleScan({ target, startPort, endPort, useTlsServer, tlsHost, tlsPort }) {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setLoading(true);
    setError(null);
    setResults([]);
    setScanMeta(null);
    setBatchThroughputs([]);
    setProgress(0);

    if (useTlsServer) {
      handleTlsScan({ target, startPort, endPort, tlsHost, tlsPort });
      return;
    }

    const params = new URLSearchParams({
      target,
      start_port: startPort,
      end_port: endPort,
      batch_size: 50,
    });

    const es = new EventSource(`${API_BASE}/scan/stream?${params}`);
    eventSourceRef.current = es;

    let allResults = [];
    let scanInfo = {};

    es.addEventListener("start", (e) => {
      const data = JSON.parse(e.data);
      scanInfo = {
        target: data.target,
        resolvedIp: data.resolved_ip,
        totalPorts: data.total_ports,
        startPort: data.start_port,
        endPort: data.end_port,
      };
    });

    es.addEventListener("batch", (e) => {
      const data = JSON.parse(e.data);
      allResults = [...allResults, ...data.results];
      setResults([...allResults]);
      setProgress(data.progress_percent);
      setBatchThroughputs((prev) => [
        ...prev,
        {
          batch: data.batch_number,
          throughput: data.throughput,
          duration: data.batch_duration,
          portsScanned: data.ports_scanned,
        },
      ]);
    });

    es.addEventListener("complete", (e) => {
      const data = JSON.parse(e.data);
      es.close();
      eventSourceRef.current = null;

      const newScanMeta = {
        target: scanInfo.target,
        resolvedIp: scanInfo.resolvedIp,
        openPorts: data.open_ports,
        totalScanned: data.total_scanned,
        durationSeconds: data.total_duration,
        results: allResults,
      };
      setScanMeta(newScanMeta);
      setResults(allResults);
      setScanHistory((prev) => [...prev, newScanMeta]);
      setProgress(100);
      setLoading(false);
    });

    es.addEventListener("error", (e) => {
      try {
        const data = JSON.parse(e.data);
        setError(data.detail || "Scan failed");
      } catch {
        setError("Connection to server lost");
      }
      es.close();
      eventSourceRef.current = null;
      setLoading(false);
    });

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        return;
      }
      setError("Connection to server lost");
      es.close();
      eventSourceRef.current = null;
      setLoading(false);
    };
  }

  async function handleTlsScan({ target, startPort, endPort, tlsHost, tlsPort }) {
    try {
      const params = {
        target,
        start_port: startPort,
        end_port: endPort,
        use_tls_server: true,
        tls_server_host: tlsHost,
        tls_server_port: tlsPort,
      };

      const response = await fetch(
        `${API_BASE}/scan?${new URLSearchParams(params)}`
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Scan failed");
      }

      setResults(data.results ?? []);
      const newScanMeta = {
        target: data.target,
        resolvedIp: data.resolved_ip,
        openPorts: data.open_ports,
        totalScanned: data.total_scanned,
        durationSeconds: data.scan_duration_seconds,
        results: data.results ?? [],
      };
      setScanMeta(newScanMeta);
      setScanHistory((prev) => [...prev, newScanMeta]);
    } catch (err) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-wrapper">
      <header className="app-header">
        <span className="header-icon">🔍</span>
        <div>
          <h1 className="header-title">TCP Port Scanner</h1>
          <p className="header-subtitle">
            Scan open ports, detect services &amp; capture banners
          </p>
        </div>
      </header>

      <main className="app-main">
        <ScanForm onScan={handleScan} disabled={loading} />

        {error && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon">⚠️</span>
            {error}
          </div>
        )}

        {loading && <LoadingSpinner progress={progress} />}

        {scanMeta && !loading && (
          <StatsPanel scanMeta={scanMeta} results={results} />
        )}

        {(batchThroughputs.length > 0 || scanHistory.length > 0) && (
          <PerformancePanel
            scanHistory={scanHistory}
            currentScan={scanMeta}
            batchThroughputs={batchThroughputs}
            isScanning={loading}
          />
        )}

        {results.length > 0 && !loading && <ResultsTable results={results} />}

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
