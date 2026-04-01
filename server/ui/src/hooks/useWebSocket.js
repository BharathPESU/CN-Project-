import { useState, useEffect, useCallback, useRef } from "react";

export default function useWebSocket(url) {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState("disconnected");
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "initial") {
          setLogs(data.logs || []);
        } else if (data.type === "log") {
          setLogs((prev) => {
            const exists = prev.find((l) => l.id === data.log.id);
            if (exists) {
              return prev.map((l) => (l.id === data.log.id ? { ...l, ...data.log } : l));
            }
            return [data.log, ...prev].slice(0, 1000);
          });
        }
      } catch (err) {
        console.error("WebSocket parse error:", err);
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      wsRef.current = null;
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { logs, status, clearLogs, reconnect: connect };
}
