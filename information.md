# TCP Port Scanner with Service Detection - Project Documentation

## Project Overview

A custom TCP port scanner with service detection, implementing concurrent scanning, timeout logic, banner grabbing, and scan efficiency evaluation. Built with a **Python FastAPI backend** and **React frontend**.

---

## 1. Concurrent Scanning

### What is Concurrent Scanning?

Concurrent scanning allows multiple ports to be scanned simultaneously using multiple threads, dramatically reducing total scan time compared to sequential scanning.

### Implementation

**Technology Used:** Python's `concurrent.futures.ThreadPoolExecutor`

**File:** `backend/scanner.py`

```python
# Configuration (lines 9-12)
CONNECT_TIMEOUT = 1.0   # Timeout for each connection attempt
BANNER_TIMEOUT = 2.0    # Timeout for banner grabbing
MAX_WORKERS = 200       # Maximum concurrent threads
BATCH_SIZE = 50         # Ports scanned per batch
```

### How It Works

**Standard Scanning (lines 114-120):**
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(scan_port, resolved_ip, port): port for port in ports}
    results: List[PortResult] = []
    for future in concurrent.futures.as_completed(futures):
        results.append(future.result())
```

**Batched Scanning for Large Ranges (lines 161-175):**
- Divides ports into batches of 50
- Each batch runs with up to 200 concurrent threads
- Results are streamed to frontend after each batch completes

### Why 200 Workers?

- Balances speed vs system resource usage
- Prevents socket exhaustion
- Avoids overwhelming target system
- Can scan ~200 ports simultaneously

### Performance Impact

| Method | 1000 Ports (approx) |
|--------|---------------------|
| Sequential | ~1000 seconds |
| Concurrent (200 workers) | ~5-10 seconds |

---

## 2. Timeout & Retry Logic

### Timeout Configuration

**File:** `backend/scanner.py:9-10`

| Timeout Type | Value | Purpose |
|--------------|-------|---------|
| CONNECT_TIMEOUT | 1.0s | Maximum wait time for TCP handshake |
| BANNER_TIMEOUT | 2.0s | Maximum wait time for service banner |

### How Timeouts Work

**Connection Attempt (lines 86-93):**
```python
def scan_port(ip: str, port: int) -> PortResult:
    try:
        with socket.create_connection((ip, port), timeout=CONNECT_TIMEOUT):
            service = get_service_name(port)
            banner = grab_banner(ip, port)
            return PortResult(port=port, status="open", service=service, banner=banner)
    except (ConnectionRefusedError, socket.timeout, OSError):
        service = get_service_name(port)
        return PortResult(port=port, status="closed", service=service, banner=None)
```

### Timeout Scenarios

1. **Port Open:** Connection succeeds within 1 second -> grab banner
2. **Port Closed:** `ConnectionRefusedError` received -> mark closed
3. **Port Filtered/No Response:** `socket.timeout` after 1 second -> mark closed
4. **Network Error:** `OSError` -> mark closed

### Retry Logic

The current implementation does **NOT** include retry logic. Each port is scanned exactly once. This design choice:
- Keeps scans fast
- Avoids aggressive probing
- Reduces network load

**Potential Enhancement:** Add configurable retry count for filtered ports.

---

## 3. Banner Grabbing

### What is Banner Grabbing?

Banner grabbing is a technique to identify services running on open ports by reading the initial response (banner) sent by the service.

### Implementation

**File:** `backend/scanner.py:63-78`

```python
def grab_banner(ip: str, port: int) -> str | None:
    try:
        with socket.create_connection((ip, port), timeout=BANNER_TIMEOUT) as sock:
            # Some services (e.g. HTTP) require a nudge before sending a banner
            try:
                sock.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
            except OSError:
                pass
            raw = sock.recv(1024)
            return raw.decode(errors="replace").strip() or None
    except OSError:
        return None
```

### How It Works

1. **Open Connection:** Creates new TCP socket with 2-second timeout
2. **Send Probe:** Sends HTTP HEAD request to trigger response
3. **Receive Banner:** Reads up to 1024 bytes from socket
4. **Decode:** Converts bytes to string, replacing invalid characters
5. **Return:** Returns banner text or `None` if failed

### HTTP Probe Explanation

```
HEAD / HTTP/1.0\r\n\r\n
```

- `HEAD`: HTTP method requesting headers only
- `/`: Request root path
- `HTTP/1.0`: Protocol version
- `\r\n\r\n`: End of HTTP headers

This probe works for:
- HTTP/HTTPS servers (returns HTTP headers)
- Other services often respond with their own banner

### Service Detection

**File:** `backend/scanner.py:55-61`

```python
def get_service_name(port: int) -> str:
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return "unknown"
```

Uses the system's `/etc/services` database to map port numbers to service names.

### Example Banners

| Port | Service | Example Banner |
|------|---------|----------------|
| 22 | SSH | `SSH-2.0-OpenSSH_8.9p1 Ubuntu-3` |
| 80 | HTTP | `HTTP/1.1 200 OK\r\nServer: nginx/1.18.0` |
| 21 | FTP | `220 ProFTPD Server ready` |
| 25 | SMTP | `220 mail.example.com ESMTP Postfix` |

---

## 4. Scan Efficiency Evaluation

### Metrics Tracked

| Metric | Description | Calculation |
|--------|-------------|-------------|
| **Throughput** | Ports scanned per second | `ports_scanned / duration_seconds` |
| **Total Time** | Complete scan duration | Sum of all batch durations |
| **Average Throughput** | Mean throughput across batches | `sum(throughputs) / batch_count` |
| **Progress** | Completion percentage | `(scanned / total) * 100` |

### Backend Implementation

**Throughput Calculation (scanner.py:180-181):**
```python
batch_duration = time.perf_counter() - batch_start_time
throughput = len(batch_ports) / batch_duration if batch_duration > 0 else 0
```

**Batch Event Data (scanner.py:183-192):**
```python
yield {
    "type": "batch",
    "batch_number": batch_number,
    "ports_scanned": len(batch_ports),
    "ports_scanned_total": len(all_results),
    "results": [r.model_dump() for r in batch_results],
    "batch_duration": round(batch_duration, 4),
    "throughput": round(throughput, 2),
    "progress_percent": round((len(all_results) / total_ports) * 100, 1),
}
```

### Frontend Visualization

**File:** `frontend/src/components/PerformancePanel.jsx`

**Metrics Displayed:**
- Total Scan Time (seconds)
- Latest Throughput (ports/second)
- Average Throughput (ports/second)
- Batches Completed
- Ports Scanned
- Open Ports Found
- Precision (accuracy metric)

**Charts:**
1. **Throughput Line Chart:** Shows throughput variation across batches
2. **Batch Time Bar Chart:** Shows time taken per batch

### Real-Time Streaming (SSE)

**Server-Sent Events Endpoint:** `GET /scan/stream`

**File:** `backend/main.py:107-155`

```python
@app.get("/scan/stream")
async def scan_stream(
    target: str,
    start_port: int,
    end_port: int,
    batch_size: int = 50,
):
    def event_generator():
        for event in scan_ports_batched(target, start_port, end_port, batch_size):
            event_type = event.get("type", "message")
            data = json.dumps(event)
            yield f"event: {event_type}\ndata: {data}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Event Types:**
1. `start`: Scan initialized with target info
2. `batch`: Batch completed with results and throughput
3. `complete`: All batches done with final summary
4. `error`: Error occurred during scan

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │   ScanForm   │  │ ResultsTable │  │ PerformancePanel   │    │
│  │              │  │              │  │ - Throughput Chart │    │
│  │ - Target     │  │ - Port List  │  │ - Time Chart       │    │
│  │ - Port Range │  │ - Status     │  │ - Metrics Cards    │    │
│  │ - TLS Option │  │ - Banners    │  │                    │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
│                            │                                    │
│                     EventSource (SSE)                           │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    /scan/stream (SSE)                     │  │
│  │  - Streams batch results in real-time                     │  │
│  │  - Yields: start → batch → batch → ... → complete         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                scan_ports_batched()                       │  │
│  │  - Divides range into 50-port batches                     │  │
│  │  - ThreadPoolExecutor (200 workers)                       │  │
│  │  - Calculates throughput per batch                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     scan_port()                           │  │
│  │  - TCP connection with 1s timeout                         │  │
│  │  - Service name lookup                                    │  │
│  │  - Banner grabbing (2s timeout)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Configuration Values

| Parameter | Value | File Location |
|-----------|-------|---------------|
| MAX_WORKERS | 200 | backend/scanner.py:11 |
| BATCH_SIZE | 50 | backend/scanner.py:12 |
| CONNECT_TIMEOUT | 1.0s | backend/scanner.py:9 |
| BANNER_TIMEOUT | 2.0s | backend/scanner.py:10 |
| Banner Buffer | 1024 bytes | backend/scanner.py:75 |
| HTTP Probe | `HEAD / HTTP/1.0\r\n\r\n` | backend/scanner.py:72 |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/scan` | Scan ports (query params) |
| POST | `/scan` | Scan ports (JSON body) |
| GET | `/scan/stream` | SSE streaming scan |

---

## Technologies Used

### Backend
- **Python 3.10+**
- **FastAPI** - Web framework
- **Pydantic** - Data validation
- **concurrent.futures** - Thread pool
- **socket** - TCP connections

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **Chart.js** - Visualizations
- **EventSource API** - SSE client

---

## Q&A - Potential Questions

### Q1: Why use ThreadPoolExecutor instead of AsyncIO?

**Answer:** Port scanning is I/O-bound but uses blocking socket calls. ThreadPoolExecutor:
- Works with standard `socket` library
- Simple to implement and debug
- 200 threads handle 200 concurrent connections
- AsyncIO would require `asyncio.open_connection()` rewrite

### Q2: Why batch size of 50?

**Answer:** 
- Small enough for real-time progress updates
- Large enough to be efficient (less overhead)
- Balances UI responsiveness vs performance
- Configurable via API parameter (1-500)

### Q3: How does banner grabbing handle non-HTTP services?

**Answer:** The HTTP probe (`HEAD / HTTP/1.0`) is sent to all services:
- HTTP servers respond with headers
- Non-HTTP services often respond with their own banner
- Some services ignore invalid input and send welcome message
- If no response, banner is `None`

### Q4: What happens if a port is filtered by firewall?

**Answer:** Filtered ports don't respond (no RST packet). The scanner:
1. Waits for CONNECT_TIMEOUT (1 second)
2. Catches `socket.timeout` exception
3. Marks port as "closed"
4. No retry is attempted

### Q5: How is scan efficiency measured?

**Answer:** Efficiency is measured by throughput:
- **Formula:** `throughput = ports_scanned / time_seconds`
- **Per-batch:** Calculated after each 50-port batch
- **Average:** Mean of all batch throughputs
- **Visualization:** Real-time charts show throughput variation

### Q6: Why use Server-Sent Events (SSE) instead of WebSocket?

**Answer:** SSE is simpler for this use case:
- One-way communication (server → client)
- Built-in browser support via `EventSource`
- Automatic reconnection
- Text-based (JSON events)
- WebSocket overkill for unidirectional streaming

### Q7: What is the maximum port range supported?

**Answer:** Full range 1-65535:
- No artificial limits in current implementation
- Scanned in batches of 50 for memory efficiency
- 65535 ports ÷ 50 = 1311 batches
- Estimated time: ~10-15 minutes depending on network
