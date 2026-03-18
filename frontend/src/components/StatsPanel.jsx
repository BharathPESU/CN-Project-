import { useMemo } from "react";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Pie } from "react-chartjs-2";

// Register the Chart.js components we need.
ChartJS.register(ArcElement, Tooltip, Legend);

/**
 * StatsPanel
 * ----------
 * Displays scan statistics (stat cards) and a pie chart of open vs closed ports.
 *
 * Props
 *   scanMeta – object from App state:
 *     { target, resolvedIp, openPorts, totalScanned, durationSeconds }
 *   results  – full array of port result dicts
 */
export default function StatsPanel({ scanMeta, results }) {
  const openCount   = scanMeta.openPorts;
  const totalCount  = scanMeta.totalScanned;
  const closedCount = totalCount - openCount;
  const openPct     = totalCount > 0 ? ((openCount / totalCount) * 100).toFixed(1) : 0;

  // ── Chart data ────────────────────────────────────────────────────────────
  const chartData = useMemo(
    () => ({
      labels: ["Open", "Closed"],
      datasets: [
        {
          data: [openCount, closedCount],
          backgroundColor: ["rgba(34,197,94,0.82)", "rgba(99,112,145,0.55)"],
          borderColor:     ["rgba(34,197,94,1)",    "rgba(99,112,145,0.9)"],
          borderWidth: 2,
          hoverOffset: 6,
        },
      ],
    }),
    [openCount, closedCount]
  );

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "bottom",
        labels: {
          color: "#8892a4",
          font: { size: 12 },
          padding: 16,
          usePointStyle: true,
        },
      },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const val = ctx.parsed;
            const pct = totalCount > 0 ? ((val / totalCount) * 100).toFixed(1) : 0;
            return ` ${ctx.label}: ${val} (${pct}%)`;
          },
        },
      },
    },
  };

  // ── Top-5 open services ───────────────────────────────────────────────────
  const topServices = useMemo(() => {
    const freq = {};
    results
      .filter((r) => r.status === "open")
      .forEach((r) => {
        const svc = r.service ?? "Unknown";
        freq[svc] = (freq[svc] ?? 0) + 1;
      });
    return Object.entries(freq)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  }, [results]);

  return (
    <section className="stats-panel">
      <h2 className="stats-title">Scan Statistics</h2>

      <div className="stats-body">
        {/* ── Left: stat cards ─────────────────────────────────────── */}
        <div className="stat-cards">
          <StatCard
            label="Total Scanned"
            value={totalCount}
            icon="🔢"
            color="blue"
          />
          <StatCard
            label="Open Ports"
            value={openCount}
            sub={`${openPct}% of total`}
            icon="🟢"
            color="green"
          />
          <StatCard
            label="Closed Ports"
            value={closedCount}
            sub={`${(100 - openPct).toFixed(1)}% of total`}
            icon="🔴"
            color="red"
          />
          <StatCard
            label="Duration"
            value={`${scanMeta.durationSeconds}s`}
            icon="⏱️"
            color="purple"
          />
          <StatCard
            label="Target"
            value={scanMeta.target}
            sub={`IP: ${scanMeta.resolvedIp}`}
            icon="🎯"
            color="blue"
          />

          {/* Top services list */}
          {topServices.length > 0 && (
            <div className="stat-card stat-card--wide">
              <span className="stat-card-icon">⚡</span>
              <div className="stat-card-body">
                <span className="stat-card-label">Top Open Services</span>
                <ul className="top-services-list">
                  {topServices.map(([svc, count]) => (
                    <li key={svc} className="top-service-item">
                      <span className="top-service-name">{svc}</span>
                      <span className="top-service-count">{count}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* ── Right: pie chart ──────────────────────────────────────── */}
        <div className="chart-container">
          <h3 className="chart-title">Open vs Closed</h3>
          {openCount === 0 && closedCount === 0 ? (
            <p className="chart-empty">No data to display.</p>
          ) : (
            <div className="chart-canvas-wrapper">
              <Pie data={chartData} options={chartOptions} />
            </div>
          )}
          <div className="chart-legend-custom">
            <span className="legend-dot legend-dot--open" />
            <span className="legend-text">Open&nbsp;&nbsp;<b>{openCount}</b></span>
            <span className="legend-dot legend-dot--closed" />
            <span className="legend-text">Closed&nbsp;&nbsp;<b>{closedCount}</b></span>
          </div>
        </div>
      </div>
    </section>
  );
}

function StatCard({ label, value, sub, icon, color = "blue" }) {
  return (
    <div className={`stat-card stat-card--${color}`}>
      <span className="stat-card-icon">{icon}</span>
      <div className="stat-card-body">
        <span className="stat-card-label">{label}</span>
        <span className="stat-card-value">{value}</span>
        {sub && <span className="stat-card-sub">{sub}</span>}
      </div>
    </div>
  );
}
