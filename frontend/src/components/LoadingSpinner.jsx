export default function LoadingSpinner({ progress = 0 }) {
  return (
    <div className="loading-card" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <div className="loading-content">
        <p className="loading-text">
          Scanning ports… {progress > 0 && `${progress}% complete`}
        </p>
        {progress > 0 && (
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
