# AGENTS.md - AI Agent Guidelines for CN-Project

This document provides guidelines for AI coding agents working in this repository.

## Project Overview

TCP Port Scanner with React frontend and FastAPI backend. Includes optional TLS server for remote scanning.

## Project Structure

```
├── backend/          # Python FastAPI backend
│   ├── main.py       # API endpoints, CORS config
│   ├── scanner.py    # Port scanning logic (ThreadPoolExecutor)
│   ├── models.py     # Pydantic models
│   └── tls_client.py # TLS client for remote server
├── frontend/         # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx   # Root component, state management
│   │   └── components/
└── server/           # TLS scan server (standalone)
```

## Build & Run Commands

### Backend (Python)

```bash
# Setup
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run development server (HTTPS)
uvicorn main:app --reload --host 0.0.0.0 --port 8000 \
  --ssl-certfile certs/dev-cert.pem --ssl-keyfile certs/dev-key.pem

# Run without HTTPS
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (JavaScript/React)

```bash
cd frontend
npm install
npm run dev      # Development server
npm run build    # Production build
npm run preview  # Preview production build
```

### One-Command Launch

```bash
./start.sh       # Linux/macOS (HTTPS)
./windows.sh     # Windows Git Bash (HTTP)
```

### SSL Certificates

```bash
npm run ssl:cert          # From root
./generate_ssl_cert.sh    # Direct script
```

## Testing

**No test framework is currently configured.** If adding tests:
- Backend: Use `pytest` with `pytest-asyncio` for async tests
- Frontend: Use `vitest` (Vite-native) or `jest`

## Linting & Formatting

**No linters are currently configured.** If adding:
- Python: `ruff` (recommended) or `black` + `isort`
- JavaScript: `eslint` + `prettier`

## Code Style Guidelines

### General Rules

1. **DO NOT ADD COMMENTS** unless explicitly asked
2. Follow existing code patterns and conventions
3. Check for existing libraries before importing new ones
4. Never expose secrets or credentials in code
5. Security focus: defensive tools only

### Python (Backend)

**Import Order:**
```python
# 1. Standard library
import os
import socket

# 2. Third-party
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

# 3. Local modules
from models import ScanRequest, ScanResponse
from scanner import scan_ports
```

**Naming Conventions:**
- Functions/variables: `snake_case` (e.g., `scan_ports`, `resolved_ip`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `CONNECT_TIMEOUT`, `MAX_WORKERS`)
- Classes: `PascalCase` (e.g., `ScanRequest`, `PortResult`)
- Private functions: `_prefix` (e.g., `_run_scan`, `_probe_port`)

**Type Annotations:**
- Use Python 3.10+ union syntax: `str | None` instead of `Optional[str]`
- Annotate all function parameters and return types
- Use Pydantic models for request/response validation

**Error Handling:**
```python
# Raise ValueError for validation errors
if end_port < start_port:
    raise ValueError("end_port must be >= start_port")

# Use HTTPException for API errors
raise HTTPException(status_code=400, detail="Invalid target")

# Catch specific exceptions
try:
    result = scan_target(host)
except socket.timeout:
    return {"status": "timeout"}
except socket.error as exc:
    raise HTTPException(status_code=500, detail=str(exc)) from exc
```

### JavaScript/React (Frontend)

**Import Order:**
```javascript
// 1. React
import { useState, useMemo } from "react";
// 2. Third-party libraries
import axios from "axios";
// 3. Local components
import ScanForm from "./components/ScanForm";
```

**Naming Conventions:**
- Components: `PascalCase` (e.g., `ScanForm`, `ResultsTable`)
- Functions/variables: `camelCase` (e.g., `handleScan`, `scanMeta`)
- CSS classes: `kebab-case` with BEM modifiers (e.g., `stat-card--green`)

**Component Patterns:**
```javascript
// Use functional components with hooks
export default function ComponentName({ prop1, prop2 }) {
  const [state, setState] = useState(initialValue);
  // ...
}
```

**State Management:**
- Use `useState` for local state
- Use `useMemo` for derived/computed data
- Pass state down via props from App.jsx

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/`      | Health check |
| GET    | `/scan`  | Scan ports (query params) |
| POST   | `/scan`  | Scan ports (JSON body) |

**Request Parameters:**
- `target` (required): IP address or hostname
- `start_port` (required): 1-65535
- `end_port` (required): 1-65535, must be >= start_port
- `use_tls_server` (optional): Use remote TLS server
- `tls_server_host` (optional): TLS server hostname
- `tls_server_port` (optional): TLS server port

## Dependencies

### Backend (requirements.txt)
- fastapi>=0.111.0
- uvicorn[standard]>=0.29.0
- pydantic>=2.7.0

### Frontend (package.json)
- react ^18.3.1
- axios ^1.6.8
- chart.js ^4.4.3
- vite ^5.2.0

## Important Notes

1. **Security**: Only assist with defensive security tasks
2. **Conciseness**: Keep responses minimal - avoid preamble/postamble
3. **No Comments**: Do not add code comments unless asked
4. **Conventions First**: Always check existing code patterns before writing new code
5. **Library Check**: Verify libraries exist in package.json/requirements.txt before using
6. **No Auto-Commit**: Never commit changes unless explicitly asked
