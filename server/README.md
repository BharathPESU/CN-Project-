# SSL Port Status Server

This folder contains a standalone Python server for your **server laptop**.

- Accepts multiple SSL/TLS client connections concurrently
- Scans requested TCP port ranges
- Returns how many ports are open (plus the open port list)
- Writes detailed TLS handshake logs to `server/logs/connections.log`

## Run on server laptop

From project root:

```bash
python3 server/ssl_port_status_server.py
```

Default bind: `0.0.0.0:9443`

The script auto-generates self-signed certs (if missing):

- `server/certs/server-cert.pem`
- `server/certs/server-key.pem`

## Request format (from clients)

Send one line JSON (newline-terminated):

```json
{"start_port":1,"end_port":1024,"target":"127.0.0.1"}
```

- `target` is optional (default: `127.0.0.1`)

## Response format

```json
{
  "ok": true,
  "request_id": "a1b2c3d4",
  "target": "127.0.0.1",
  "resolved_ip": "127.0.0.1",
  "start_port": 1,
  "end_port": 1024,
      "open_ports": 5,
      "total_scanned": 1024,
      "scan_duration_seconds": 1.23,
      "results": [{"port": 22, "status": "open", "service": "ssh", "banner": "..."}, ...]
}
```

On errors:

```json
{"ok":false,"request_id":"...","error":"..."}
```

## Quick test client (optional)

```bash
printf '{"start_port":1,"end_port":200}\n' | \
openssl s_client -connect 127.0.0.1:9443 -quiet -ign_eof

## Handshake logs

Each TLS connection writes a log line with handshake info, for example:

```
2026-03-29 10:25:32 | INFO | [a1b2c3d4] connect client=192.168.1.39:53588 tls=TLSv1.3 cipher=TLS_AES_256_GCM_SHA384 session_reused=False client_cert=absent
```

## Logs UI (HTML + JavaScript)

The UI reads `server/logs/connections.log` and renders a dashboard in the browser.

1. Start the TLS server (same as above).
2. From the `server` folder, run a simple static file server:

```bash
python3 -m http.server 8080
```

3. Open the UI in your browser:

```
http://<server-laptop-ip>:8080/logs_ui.html
```

Notes:
- Closed ports are derived from total scanned minus open ports.
- Timeout counts are not logged by the server and are shown as "n/a" in the UI.
```
