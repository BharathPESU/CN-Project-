import { useState } from "react";

/**
 * ScanForm
 * --------
 * Controlled form for entering scan parameters.
 *
 * Props
 *   onScan(params)  – called with { target, startPort, endPort } on submit
 *   disabled        – when true, all inputs and the button are disabled
 */
export default function ScanForm({ onScan, disabled }) {
  const [target,    setTarget]    = useState("");
  const [startPort, setStartPort] = useState(1);
  const [endPort,   setEndPort]   = useState(1024);
  const [formError, setFormError] = useState(null);

  function validate() {
    if (!target.trim()) return "Please enter a target IP address or hostname.";
    const s = Number(startPort);
    const e = Number(endPort);
    if (!Number.isInteger(s) || s < 1 || s > 65535)
      return "Start port must be an integer between 1 and 65535.";
    if (!Number.isInteger(e) || e < 1 || e > 65535)
      return "End port must be an integer between 1 and 65535.";
    if (e < s)
      return "End port must be greater than or equal to start port.";
    if (e - s > 9999)
      return "Port range cannot exceed 10 000 ports per scan.";
    return null;
  }

  function handleSubmit(e) {
    e.preventDefault();
    const err = validate();
    if (err) { setFormError(err); return; }
    setFormError(null);
    onScan({ target: target.trim(), startPort: Number(startPort), endPort: Number(endPort) });
  }

  return (
    <form className="scan-form" onSubmit={handleSubmit} noValidate>
      <h2 className="form-title">Scan Configuration</h2>

      {/* Target */}
      <div className="form-group">
        <label className="form-label" htmlFor="target">
          Target Host
        </label>
        <input
          id="target"
          className="form-input"
          type="text"
          placeholder="e.g. 192.168.1.1 or example.com"
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          disabled={disabled}
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      {/* Port range */}
      <div className="form-row">
        <div className="form-group">
          <label className="form-label" htmlFor="startPort">
            Start Port
          </label>
          <input
            id="startPort"
            className="form-input"
            type="number"
            min={1}
            max={65535}
            value={startPort}
            onChange={(e) => setStartPort(e.target.value)}
            disabled={disabled}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="endPort">
            End Port
          </label>
          <input
            id="endPort"
            className="form-input"
            type="number"
            min={1}
            max={65535}
            value={endPort}
            onChange={(e) => setEndPort(e.target.value)}
            disabled={disabled}
          />
        </div>
      </div>

      {/* Inline form validation error */}
      {formError && (
        <p className="form-error" role="alert">
          ⚠ {formError}
        </p>
      )}

      <button className="btn-scan" type="submit" disabled={disabled}>
        {disabled ? (
          <>
            <span className="btn-spinner" aria-hidden="true" />
            Scanning…
          </>
        ) : (
          "▶ Start Scan"
        )}
      </button>
    </form>
  );
}
