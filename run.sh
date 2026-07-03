#!/usr/bin/env bash
# ==============================================================================
# Sampark AI Platform — Local Development Runner
# ==============================================================================
# Starts the FastAPI backend (ADK-powered) and Vite frontend concurrently.
# Press Ctrl+C to stop both services.
#
# Usage:
#   chmod +x run.sh
#   ./run.sh
#
# Prerequisites:
#   - Python 3.12+
#   - Node.js 20+
#   - A Google Gemini API key (set GOOGLE_API_KEY in .env or export it)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Helpers ───────────────────────────────────────────────────────────────────

log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "\n${CYAN}═══ $1 ═══${NC}\n"; }

cleanup() {
    echo ""
    log_step "Shutting down services"

    if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
        log_info "Stopped backend (PID $BACKEND_PID)"
    fi

    if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null
        log_info "Stopped frontend (PID $FRONTEND_PID)"
    fi

    # Kill any lingering uvicorn/node processes started by this script
    # (safety net in case PIDs changed or children weren't killed)
    if command -v lsof &>/dev/null; then
        kill $(lsof -t -i:8000 2>/dev/null) 2>/dev/null || true
        kill $(lsof -t -i:5173 2>/dev/null) 2>/dev/null || true
    fi

    echo ""
    log_ok "All services stopped. Goodbye!"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ── 1. Check Prerequisites ────────────────────────────────────────────────────

log_step "Checking prerequisites"

# Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    log_error "Python 3.12+ is required but not found."
    log_info "Install it from https://www.python.org/downloads/"
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)
PYTHON_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
log_ok "Python $PYTHON_VERSION ($PYTHON)"

# Node.js
if ! command -v node &>/dev/null; then
    log_error "Node.js 20+ is required but not found."
    log_info "Install it from https://nodejs.org/"
    exit 1
fi
NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
log_ok "Node.js $(node --version) ($(command -v node))"

# npm
if ! command -v npm &>/dev/null; then
    log_error "npm is required but not found."
    exit 1
fi
log_ok "npm $(npm --version)"

# ── 2. Environment Configuration ──────────────────────────────────────────────

log_step "Environment configuration"

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        log_warn "No .env file found — created from .env.example"
        log_warn "⚠  Edit .env and set your GOOGLE_API_KEY before the ADK pipeline will work!"
        echo ""
        log_info "Quick setup: open .env and set:"
        log_info "  GOOGLE_API_KEY=your-gemini-api-key-here"
        log_info "Get a free key at: https://aistudio.google.com/apikey"
        echo ""
    else
        log_error "No .env or .env.example found."
        log_info "Create a .env file with at least:"
        log_info "  GOOGLE_API_KEY=your-gemini-api-key"
        exit 1
    fi
else
    log_ok ".env file found"
fi

# Source .env so child processes inherit the vars
set -a
source .env
set +a

# ── 3. Install Backend Dependencies ──────────────────────────────────────────

log_step "Backend dependencies"

if $PYTHON -c "import fastapi" 2>/dev/null; then
    log_ok "Python packages already installed"
else
    log_info "Installing Python packages (pip install -e '.[dev]')..."
    $PYTHON -m pip install -e ".[dev]" 2>&1 | tail -5
    log_ok "Python packages installed"
fi

# ── 4. Install Frontend Dependencies ─────────────────────────────────────────

log_step "Frontend dependencies"

if [ -d frontend/node_modules ]; then
    log_ok "Node modules already installed"
else
    log_info "Installing npm packages..."
    cd frontend && npm install 2>&1 | tail -5 && cd "$SCRIPT_DIR"
    log_ok "npm packages installed"
fi

# ── 5. Start Services ─────────────────────────────────────────────────────────

log_step "Starting services"

# Backend — FastAPI on port 8000
log_info "Starting backend API server (uvicorn)..."
$PYTHON -m uvicorn backend.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    2>&1 &
BACKEND_PID=$!
log_ok "Backend starting on http://localhost:8000 (PID $BACKEND_PID)"

# Wait for backend to be ready
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        log_ok "Backend is ready!"
        break
    fi
    if [ "$i" -eq 15 ]; then
        log_warn "Backend health check timed out — it may still be starting up."
    fi
    sleep 1
done

# Frontend — Vite dev server on port 5173
log_info "Starting frontend dev server (Vite)..."
cd frontend && npm run dev -- --host 2>&1 &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"
log_ok "Frontend starting on http://localhost:5173 (PID $FRONTEND_PID)"

# ── 6. Show Status ───────────────────────────────────────────────────────────

echo ""
log_step "🚀 Sampark AI Platform is running!"
echo ""
echo -e "  ${GREEN}Frontend:${NC}  http://localhost:5173"
echo -e "  ${GREEN}Backend:${NC}   http://localhost:8000"
echo -e "  ${GREEN}API Docs:${NC}  http://localhost:8000/docs"
echo -e "  ${GREEN}Health:${NC}    http://localhost:8000/health"
echo ""
echo -e "  ${YELLOW}Demo Login:${NC}"
echo -e "    Admin:     admin / password"
echo -e "    Leader:    leader_w1 / password"
echo ""
echo -e "  ${YELLOW}Dashboard:${NC}"
echo -e "    1. Open http://localhost:5173"
echo -e "    2. Login as admin (admin / password)"
echo -e "    3. Click 'Report Issue' to submit a complaint"
echo -e "    4. Switch to 'Dashboard' to see analytics"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

# ── 7. Wait for either process to exit ────────────────────────────────────────

wait
