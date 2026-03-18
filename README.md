# TCP Port Scanner

A full-stack network port scanner built with a **FastAPI** backend and a **React** frontend.  
Scan any IP address or hostname, detect open ports, identify running services, and capture service banners — all from a modern web dashboard.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│  React + Vite  →  ScanForm  →  Axios GET /scan              │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────┐
│                    FastAPI  (port 8000)                      │
│  GET /scan  →  scanner.py  →  ThreadPoolExecutor            │
│               (100 concurrent TCP probes)                    │
└────────────────────────────┬────────────────────────────────┘
                             │ Raw TCP sockets
              ┌──────────────▼──────────────┐
              │        Target Host           │
              │  port 20 … port 65535        │
              └─────────────────────────────┘
```

### Backend (`backend/`)

| File               | Role                                                                                                                         |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `main.py`          | FastAPI app — exposes `GET /scan` and `POST /scan` endpoints, CORS middleware, input validation                              |
| `scanner.py`       | Core scanning logic — DNS resolution, concurrent TCP connect via `socket.connect_ex()`, banner grabbing with `socket.recv()` |
| `port_scanner.py`  | Standalone CLI port scanner module — can be run independently from the terminal                                              |
| `models.py`        | Pydantic request/response models (`ScanRequest`, `PortResult`, `ScanResponse`)                                               |
| `requirements.txt` | Python dependencies                                                                                                          |

**Scan flow:**

1. The API resolves the target hostname to an IP address.
2. A `ThreadPoolExecutor` (up to 200 workers) fires one TCP `connect_ex()` call per port simultaneously.
3. On each open port the same socket is reused to attempt a banner grab (`recv(1024)`).
4. Results are sorted by port number and returned as JSON.

### Frontend (`frontend/`)

| File                                | Role                                                                  |
| ----------------------------------- | --------------------------------------------------------------------- |
| `src/App.jsx`                       | Root component — holds all state, calls the API with Axios            |
| `src/components/ScanForm.jsx`       | Controlled form with client-side validation                           |
| `src/components/ResultsTable.jsx`   | Sortable, filterable results table (Port / Status / Service / Banner) |
| `src/components/StatsPanel.jsx`     | Stat cards + Chart.js pie chart (open vs closed)                      |
| `src/components/LoadingSpinner.jsx` | Animated loading card shown during in-flight scans                    |
| `src/index.css`                     | Dark-theme design system using CSS custom properties                  |

---

## Project Structure

```
CN/
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── port_scanner.py
│   ├── scanner.py
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── index.css
        └── components/
            ├── ScanForm.jsx
            ├── ResultsTable.jsx
            ├── StatsPanel.jsx
            └── LoadingSpinner.jsx
```

---

## Quick Start

The fastest way to install and run the entire project is with the included shell script:

```bash
./start.sh
```

This single command will:

1. Check for required tools (`python3`, `pip` or `pip3`, `node`, `npm`, `openssl`)
2. Create a Python virtual environment and install backend dependencies
3. Install frontend Node.js dependencies
4. Generate local self-signed TLS certificates in `backend/certs/`
5. Start the FastAPI backend on **https://localhost:8000**
6. Start the React frontend on **https://localhost:5173**

Press **Ctrl+C** to stop both servers.

> **First time only** — make the script executable before running:
>
> ```bash
> chmod +x start.sh
> ./start.sh
> ```

To generate the SSL certificate manually at any time:

```bash
./generate_ssl_cert.sh
```

or

```bash
npm run ssl:cert
```

---

## Prerequisites

| Tool    | Minimum version |
| ------- | --------------- |
| Python  | 3.11+           |
| Node.js | 18+             |
| npm     | 9+              |
| OpenSSL | 1.1+            |

---

## How SSL Works in This Project

This project uses **local self-signed TLS certificates** for development.

1. `generate_ssl_cert.sh` creates `backend/certs/dev-cert.pem` and `backend/certs/dev-key.pem` with OpenSSL (if they do not already exist).
2. `start.sh` automatically runs `./generate_ssl_cert.sh` before starting servers.
3. FastAPI/Uvicorn uses these files via `--ssl-certfile` and `--ssl-keyfile`, so the API runs on `https://localhost:8000`.
4. Vite dev server uses the same cert/key through `VITE_HTTPS=true`, `VITE_SSL_CERT`, and `VITE_SSL_KEY`, so the frontend runs on `https://localhost:5173`.
5. Vite proxy forwards `/scan` to `https://localhost:8000` with `secure: false` to allow the local self-signed certificate in dev.
6. API tools like `curl` use `-k` for local testing (`curl -k ...`) to skip CA verification for this self-signed cert.

> Browser certificate warnings are expected the first time in local development because the certificate is self-signed.
> For production, use a CA-signed certificate and remove insecure dev options (for example `curl -k` and relaxed TLS settings).

---

## Installation

### 1. Clone / open the project

```bash
cd /path/to/CN
```

### 2. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:

- `fastapi` — web framework
- `uvicorn[standard]` — ASGI server
- `pydantic` — data validation

### 3. Install frontend dependencies

```bash
cd ../frontend
npm install
```

This installs:

- `react` / `react-dom`
- `axios` — HTTP client
- `chart.js` + `react-chartjs-2` — pie chart
- `vite` + `@vitejs/plugin-react` — build tooling

---

## Running the Project

You need **two terminals** running simultaneously.

### Terminal 1 — Start the FastAPI backend

```bash
cd backend
../generate_ssl_cert.sh
uvicorn main:app --reload --host 0.0.0.0 --port 8000 \
  --ssl-certfile certs/dev-cert.pem \
  --ssl-keyfile certs/dev-key.pem
```

The API will be available at:

- **Base URL:** `https://localhost:8000`
- **Interactive docs (Swagger):** `https://localhost:8000/docs`
- **Scan endpoint:** `GET https://localhost:8000/scan?target=...&start_port=...&end_port=...`

### Terminal 2 — Start the React frontend

```bash
cd frontend
VITE_HTTPS=true \
VITE_SSL_CERT=../backend/certs/dev-cert.pem \
VITE_SSL_KEY=../backend/certs/dev-key.pem \
npm run dev
```

The dashboard will be available at:

- **URL:** `https://localhost:5173`

> In development, Vite automatically proxies all `/scan` requests to the FastAPI backend on port 8000 over HTTPS, so no manual CORS configuration is needed.

---

## API Usage

### `GET /scan`

```
GET /scan?target=127.0.0.1&start_port=20&end_port=100
```

### `POST /scan`

```bash
curl -k -X POST https://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"target": "127.0.0.1", "start_port": 20, "end_port": 100}'
```

### Example Response

```json
{
  "target": "127.0.0.1",
  "resolved_ip": "127.0.0.1",
  "start_port": 20,
  "end_port": 100,
  "open_ports": 2,
  "total_scanned": 81,
  "scan_duration_seconds": 1.042,
  "results": [
    {
      "port": 22,
      "status": "open",
      "service": "SSH",
      "banner": "SSH-2.0-OpenSSH_8.9"
    },
    {
      "port": 80,
      "status": "open",
      "service": "HTTP",
      "banner": "HTTP/1.1 200 OK..."
    },
    { "port": 21, "status": "closed", "service": "FTP Control", "banner": null }
  ]
}
```

### Validation Rules

| Rule                      | Detail                    |
| ------------------------- | ------------------------- |
| Port range                | 1 – 65535                 |
| Max ports per request     | 10 000                    |
| `end_port` ≥ `start_port` | Required                  |
| Unresolvable hostname     | Returns `400 Bad Request` |

---

## Using the CLI Scanner (optional)

`port_scanner.py` can be run directly without the web server:

```bash
cd backend
python port_scanner.py
```

This interactive mode asks for target IP/hostname, start port, and end port in the terminal, then prints full scan results (including total, open, and closed counts).

Or pass values directly as arguments:

```bash
cd backend
python port_scanner.py <target> <start_port> <end_port>
```

**Example:**

```bash
python port_scanner.py 127.0.0.1 1 1024
```

**Output:**

```
Scanning 127.0.0.1  ports 1–1024 …

Port       Status     Service                   Banner
────────────────────────────────────────────────────────────────────────────────
22         open       SSH                       SSH-2.0-OpenSSH_8.9p1 ◀
80         open       HTTP                      HTTP/1.1 200 OK ... ◀
443        closed     HTTPS                     -
────────────────────────────────────────────────────────────────────────────────
Total scanned : 1024
Open ports    : 2
```

---

## Building for Production

### Frontend

```bash
cd frontend
npm run build        # outputs to frontend/dist/
npm run preview      # local preview of the production build
```

Set the backend URL for production by creating `frontend/.env`:

```
VITE_API_BASE=https://your-backend-domain.com
```
