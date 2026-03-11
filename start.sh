#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh  –  One-command installer & launcher for TCP Port Scanner
#
# Usage:
#   chmod +x start.sh   (first time only)
#   ./start.sh
#
# What it does:
#   1. Checks for required tools (python3, pip, node, npm)
#   2. Creates a Python virtual environment in backend/.venv
#   3. Installs Python dependencies (FastAPI, uvicorn, pydantic)
#   4. Installs Node.js dependencies (React, Vite, Chart.js, Axios)
#   5. Starts the FastAPI backend on  http://localhost:8000
#   6. Starts the React frontend on   http://localhost:5173
#   7. Cleans up both processes on Ctrl+C
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}${BOLD}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}${BOLD}[ OK ]${RESET}  $*"; }
warn()    { echo -e "${YELLOW}${BOLD}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}${BOLD}[ERR ]${RESET}  $*" >&2; }

# ── Resolve project root (directory containing this script) ───────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}         🔍  TCP Port Scanner  –  Setup & Launch              ${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# ── 1. Prerequisite checks ────────────────────────────────────────────────────
info "Checking prerequisites…"

check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    error "'$1' not found. Please install it and re-run this script."
    exit 1
  fi
}

check_cmd python3
check_cmd pip3
check_cmd node
check_cmd npm

PYTHON_VER=$(python3 --version 2>&1)
NODE_VER=$(node --version 2>&1)
success "Found $PYTHON_VER"
success "Found Node.js $NODE_VER"

# ── 2. Backend – Python virtual environment ───────────────────────────────────
echo ""
info "Setting up Python virtual environment…"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
  success "Virtual environment created at backend/.venv"
else
  success "Virtual environment already exists – skipping creation"
fi

# Activate venv for the rest of this script
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# ── 3. Backend – install Python packages ──────────────────────────────────────
info "Installing Python dependencies…"
pip install --quiet --upgrade pip
pip install --quiet -r "$BACKEND_DIR/requirements.txt"
success "Python dependencies installed"

# ── 4. Frontend – install Node packages ───────────────────────────────────────
echo ""
info "Installing Node.js dependencies…"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  npm install --prefix "$FRONTEND_DIR" --silent
  success "Node.js dependencies installed"
else
  success "node_modules already exists – skipping npm install"
fi

# ── 5. Cleanup handler (Ctrl+C) ───────────────────────────────────────────────
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  warn "Shutting down servers…"
  [ -n "$BACKEND_PID"  ] && kill "$BACKEND_PID"  2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  success "All processes stopped. Goodbye!"
  exit 0
}
trap cleanup INT TERM

# ── 6. Start FastAPI backend ──────────────────────────────────────────────────
echo ""
info "Starting FastAPI backend on http://localhost:8000 …"
cd "$BACKEND_DIR"
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

# Give uvicorn a moment to start before launching the frontend
sleep 2

if kill -0 "$BACKEND_PID" 2>/dev/null; then
  success "Backend running  →  http://localhost:8000  (PID $BACKEND_PID)"
  success "API docs         →  http://localhost:8000/docs"
else
  error "Backend failed to start. Check the output above."
  exit 1
fi

# ── 7. Start React frontend ───────────────────────────────────────────────────
info "Starting React frontend on http://localhost:5173 …"
npm run dev --prefix "$FRONTEND_DIR" &
FRONTEND_PID=$!

sleep 2

if kill -0 "$FRONTEND_PID" 2>/dev/null; then
  success "Frontend running  →  http://localhost:5173  (PID $FRONTEND_PID)"
else
  error "Frontend failed to start. Check the output above."
  kill "$BACKEND_PID" 2>/dev/null || true
  exit 1
fi

# ── 8. Summary ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  ${GREEN}${BOLD}✔  Both servers are running!${RESET}"
echo ""
echo -e "  🌐  Dashboard  →  ${CYAN}http://localhost:5173${RESET}"
echo -e "  ⚡  API        →  ${CYAN}http://localhost:8000${RESET}"
echo -e "  📖  API Docs   →  ${CYAN}http://localhost:8000/docs${RESET}"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${RESET} to stop both servers."
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# Keep script alive so Ctrl+C is caught by the trap
wait
