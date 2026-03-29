#!/usr/bin/env bash
# Windows launcher for Git Bash / WSL
# Usage (Git Bash):
#   chmod +x windows.sh
#   ./windows.sh

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}${BOLD}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}${BOLD}[ OK ]${RESET}  $*"; }
warn()    { echo -e "${YELLOW}${BOLD}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}${BOLD}[ERR ]${RESET}  $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

info "Checking prerequisites…"

check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    error "'$1' not found. Please install it and re-run this script."
    exit 1
  fi
}

check_cmd python
check_cmd node
check_cmd npm

if command -v pip &>/dev/null; then
  PIP_CMD="pip"
elif command -v pip3 &>/dev/null; then
  PIP_CMD="pip3"
else
  error "Neither 'pip' nor 'pip3' was found. Please install pip and re-run this script."
  exit 1
fi

PYTHON_VER=$(python --version 2>&1)
NODE_VER=$(node --version 2>&1)
success "Found $PYTHON_VER"
success "Found Node.js $NODE_VER"
success "Using $PIP_CMD"

info "Setting up Python virtual environment…"
if [ ! -d "$VENV_DIR" ]; then
  python -m venv "$VENV_DIR"
  success "Virtual environment created at backend/.venv"
else
  success "Virtual environment already exists – skipping creation"
fi

# Activate venv for the rest of this script (Windows path)
# shellcheck source=/dev/null
source "$VENV_DIR/Scripts/activate"

info "Installing Python dependencies…"
"$PIP_CMD" install --quiet --upgrade pip
"$PIP_CMD" install --quiet -r "$BACKEND_DIR/requirements.txt"
success "Python dependencies installed"

info "Installing Node.js dependencies…"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  npm install --prefix "$FRONTEND_DIR" --silent
  success "Node.js dependencies installed"
else
  success "node_modules already exists – skipping npm install"
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  warn "Shutting down servers…"
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  success "All processes stopped. Goodbye!"
  exit 0
}
trap cleanup INT TERM

info "Starting FastAPI backend on http://localhost:8000 …"
cd "$BACKEND_DIR"
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

sleep 2

if kill -0 "$BACKEND_PID" 2>/dev/null; then
  success "Backend running  →  http://localhost:8000  (PID $BACKEND_PID)"
  success "API docs         →  http://localhost:8000/docs"
else
  error "Backend failed to start. Check the output above."
  exit 1
fi

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

wait
