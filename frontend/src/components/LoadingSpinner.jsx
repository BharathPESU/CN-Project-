/**
 * LoadingSpinner
 * --------------
 * Full-width loading card shown while a scan request is in flight.
 */
export default function LoadingSpinner() {
  return (
    <div className="loading-card" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <p className="loading-text">
        Scanning ports… this may take a few seconds.
      </p>
    </div>
  );
}
