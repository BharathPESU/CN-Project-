export default function ConnectionStatus({ status }) {
  const labels = {
    connected: "Connected",
    connecting: "Connecting...",
    disconnected: "Disconnected",
  };

  return (
    <div className="connection-status">
      <span className={`status-dot status-dot--${status}`} />
      <span>{labels[status]}</span>
    </div>
  );
}
