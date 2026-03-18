import { useState, useMemo } from "react";

/**
 * ResultsTable
 * ------------
 * Renders port scan results in a sortable, filterable table.
 *
 * Props
 *   results – array of { port, status, service, banner } dicts
 */
export default function ResultsTable({ results }) {
  const [filter,    setFilter]    = useState("all");   // "all" | "open" | "closed"
  const [sortField, setSortField] = useState("port");
  const [sortAsc,   setSortAsc]   = useState(true);
  const [search,    setSearch]    = useState("");

  // Filtered + searched + sorted rows
  const rows = useMemo(() => {
    let data = results;

    // Status filter
    if (filter !== "all") data = data.filter((r) => r.status === filter);

    // Search across port, service, banner
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      data = data.filter(
        (r) =>
          String(r.port).includes(q) ||
          r.service.toLowerCase().includes(q) ||
          (r.banner ?? "").toLowerCase().includes(q)
      );
    }

    // Sort
    data = [...data].sort((a, b) => {
      let va = a[sortField] ?? "";
      let vb = b[sortField] ?? "";
      if (typeof va === "number") return sortAsc ? va - vb : vb - va;
      return sortAsc
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va));
    });

    return data;
  }, [results, filter, sortField, sortAsc, search]);

  function handleSort(field) {
    if (sortField === field) setSortAsc((prev) => !prev);
    else { setSortField(field); setSortAsc(true); }
  }

  function sortIcon(field) {
    if (sortField !== field) return <span className="sort-icon">↕</span>;
    return <span className="sort-icon sort-icon--active">{sortAsc ? "↑" : "↓"}</span>;
  }

  const openCount   = results.filter((r) => r.status === "open").length;
  const closedCount = results.length - openCount;

  return (
    <section className="results-section">
      <div className="results-header">
        <h2 className="results-title">
          Scan Results&nbsp;
          <span className="results-count">({results.length} ports)</span>
        </h2>

        {/* Toolbar */}
        <div className="results-toolbar">
          {/* Status filter tabs */}
          <div className="filter-tabs" role="group" aria-label="Filter by status">
            {[
              { key: "all",    label: `All (${results.length})` },
              { key: "open",   label: `Open (${openCount})` },
              { key: "closed", label: `Closed (${closedCount})` },
            ].map(({ key, label }) => (
              <button
                key={key}
                className={`filter-tab${filter === key ? " filter-tab--active" : ""}`}
                onClick={() => setFilter(key)}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Search */}
          <input
            className="form-input search-input"
            type="search"
            placeholder="Search port / service / banner…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search results"
          />
        </div>
      </div>

      {/* Table */}
      <div className="table-wrapper">
        <table className="results-table">
          <thead>
            <tr>
              {[
                { field: "port",    label: "Port" },
                { field: "status",  label: "Status" },
                { field: "service", label: "Service" },
                { field: "banner",  label: "Banner" },
              ].map(({ field, label }) => (
                <th
                  key={field}
                  className="th-sortable"
                  onClick={() => handleSort(field)}
                  aria-sort={
                    sortField === field
                      ? sortAsc ? "ascending" : "descending"
                      : "none"
                  }
                >
                  {label} {sortIcon(field)}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="td-empty">
                  No results match the current filter.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.port} className={r.status === "open" ? "row-open" : "row-closed"}>
                  <td className="td-port">{r.port}</td>
                  <td>
                    <span className={`status-badge status-badge--${r.status}`}>
                      {r.status === "open" ? "● Open" : "○ Closed"}
                    </span>
                  </td>
                  <td className="td-service">{r.service}</td>
                  <td className="td-banner">
                    {r.banner ? (
                      <span className="banner-text" title={r.banner}>
                        {r.banner.slice(0, 80)}
                        {r.banner.length > 80 ? "…" : ""}
                      </span>
                    ) : (
                      <span className="banner-empty">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="results-footer">
        Showing {rows.length} of {results.length} ports
      </p>
    </section>
  );
}
