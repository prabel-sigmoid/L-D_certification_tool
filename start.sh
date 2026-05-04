#!/usr/bin/env bash
# ============================================================
#  L&D Certificate Sync — One-Click Startup Script
#  Run this once to set up and launch the entire application.
#  Works on Linux and macOS.
# ============================================================

set -euo pipefail          # exit on error, treat unset vars as error
IFS=$'\n\t'

# ── Colours ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'   # No Colour

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=13   # Python 3.13.x is used in the project venv
REQUIRED_NODE_MAJOR=18     # Node 18+ is required by Vite

BACKEND_PID=""
FRONTEND_PID=""

# ── Helpers ───────────────────────────────────────────────────
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()     { error "$*"; echo -e "${RED}Aborting setup. Please fix the issue above and try again.${NC}" >&2; exit 1; }

# ── Banner ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   L&D Certificate Sync — Startup Script     ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Cleanup on Ctrl+C / exit ──────────────────────────────────
cleanup() {
  echo ""
  info "Shutting down..."
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null && info "Backend stopped."
  fi
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null && info "Frontend stopped."
  fi
  echo -e "${GREEN}Goodbye!${NC}"
  exit 0
}
trap cleanup INT TERM EXIT

# ════════════════════════════════════════════════════════════════
# 1. CHECK PYTHON
# ════════════════════════════════════════════════════════════════
info "Checking Python installation..."

PYTHON_CMD=""
for cmd in python3.13 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    VER=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
    MAJOR=$(echo "$VER" | cut -d. -f1)
    MINOR=$(echo "$VER" | cut -d. -f2)
    if [[ "$MAJOR" -eq "$REQUIRED_PYTHON_MAJOR" && "$MINOR" -ge "$REQUIRED_PYTHON_MINOR" ]]; then
      PYTHON_CMD="$cmd"
      success "Found compatible Python: $("$cmd" --version) at $(command -v "$cmd")"
      break
    fi
  fi
done

if [[ -z "$PYTHON_CMD" ]]; then
  error "Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+ is required but was not found."
  echo ""
  echo "  Please install Python 3.13 from:"
  echo "    https://www.python.org/downloads/"
  echo ""
  echo "  On Ubuntu/Debian you can run:"
  echo "    sudo apt update && sudo apt install python3.13 python3.13-venv"
  echo ""
  echo "  On macOS (using Homebrew):"
  echo "    brew install python@3.13"
  die "Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+ not found."
fi

# ════════════════════════════════════════════════════════════════
# 2. CHECK NODE.JS
# ════════════════════════════════════════════════════════════════
info "Checking Node.js installation..."

if ! command -v node &>/dev/null; then
  error "Node.js is not installed."
  echo ""
  echo "  Please install Node.js (LTS) from:"
  echo "    https://nodejs.org/en/download"
  echo ""
  echo "  On Ubuntu/Debian:"
  echo "    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
  echo "    sudo apt install -y nodejs"
  die "Node.js not found."
fi

NODE_MAJOR=$(node --version | grep -oP '\d+' | head -1)
if [[ "$NODE_MAJOR" -lt "$REQUIRED_NODE_MAJOR" ]]; then
  die "Node.js version is too old (found v$(node --version | tr -d 'v'), need v${REQUIRED_NODE_MAJOR}+). Please update: https://nodejs.org"
fi
success "Found Node.js: $(node --version) and npm: $(npm --version)"

# ════════════════════════════════════════════════════════════════
# 3. VALIDATE BACKEND .env
# ════════════════════════════════════════════════════════════════
info "Checking backend .env configuration..."

BACKEND_ENV="$BACKEND_DIR/.env"
if [[ ! -f "$BACKEND_ENV" ]]; then
  error "Backend .env file not found at: $BACKEND_ENV"
  echo ""
  echo "  Please create the file '$BACKEND_ENV' and fill in all required values."
  echo "  Refer to the README.md for a full list of required variables."
  die "Missing backend .env file."
fi

REQUIRED_ENV_VARS=(
  "AZURE_STORAGE_CONNECTION_STRING"
  "AZURE_STORAGE_CONTAINER"
  "AZURE_FORM_RECOGNIZER_ENDPOINT"
  "AZURE_FORM_RECOGNIZER_KEY"
  "AZURE_OPENAI_ENDPOINT"
  "AZURE_OPENAI_KEY"
  "AZURE_OPENAI_DEPLOYMENT"
  "AZURE_OPENAI_API_VERSION"
  "GOOGLE_CLIENT_ID"
  "GOOGLE_CLIENT_SECRET"
  "GOOGLE_REDIRECT_URI"
  "ALLOWED_DOMAIN"
  "AUTHORIZED_USERS"
  "JWT_SECRET"
)

MISSING_VARS=()
for var in "${REQUIRED_ENV_VARS[@]}"; do
  # Check the variable exists and is not just a comment or empty
  val=$(grep -E "^${var}=" "$BACKEND_ENV" | cut -d= -f2- | tr -d ' ')
  if [[ -z "$val" || "$val" == "<"* ]]; then
    MISSING_VARS+=("$var")
  fi
done

if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
  error "The following required settings are missing or empty in your backend .env file:"
  for v in "${MISSING_VARS[@]}"; do
    echo "    ✗  $v"
  done
  echo ""
  echo "  Open '$BACKEND_ENV' in a text editor and fill in all the values."
  echo "  See README.md for guidance on where to find each value."
  die "Incomplete .env configuration."
fi
success "Backend .env looks good."

# ════════════════════════════════════════════════════════════════
# 4. VALIDATE FRONTEND .env
# ════════════════════════════════════════════════════════════════
info "Checking frontend .env configuration..."

FRONTEND_ENV="$FRONTEND_DIR/.env"
if [[ ! -f "$FRONTEND_ENV" ]]; then
  warn "Frontend .env not found — creating it with default value."
  echo "VITE_API_URL=http://localhost:8000" > "$FRONTEND_ENV"
  success "Created frontend .env with VITE_API_URL=http://localhost:8000"
fi

# ════════════════════════════════════════════════════════════════
# 5. SET UP PYTHON VIRTUAL ENVIRONMENT
# ════════════════════════════════════════════════════════════════
info "Setting up Python virtual environment..."

VENV_DIR="$BACKEND_DIR/venv"

if [[ ! -d "$VENV_DIR" ]]; then
  info "No virtual environment found. Creating one with $PYTHON_CMD..."
  "$PYTHON_CMD" -m venv "$VENV_DIR" || die "Failed to create Python virtual environment. Make sure python3-venv is installed."
  success "Virtual environment created."
else
  # Verify existing venv uses a compatible Python version
  VENV_PYTHON="$VENV_DIR/bin/python"
  if [[ -f "$VENV_PYTHON" ]]; then
    VENV_VER=$("$VENV_PYTHON" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
    VENV_MAJOR=$(echo "$VENV_VER" | cut -d. -f1)
    VENV_MINOR=$(echo "$VENV_VER" | cut -d. -f2)
    if [[ "$VENV_MAJOR" -ne "$REQUIRED_PYTHON_MAJOR" || "$VENV_MINOR" -lt "$REQUIRED_PYTHON_MINOR" ]]; then
      warn "Existing virtual environment uses Python $VENV_VER which is outdated."
      warn "Recreating virtual environment with $PYTHON_CMD ($($PYTHON_CMD --version))..."
      rm -rf "$VENV_DIR"
      "$PYTHON_CMD" -m venv "$VENV_DIR" || die "Failed to recreate Python virtual environment."
      success "Virtual environment recreated."
    else
      success "Existing virtual environment is compatible (Python $VENV_VER)."
    fi
  fi
fi

VENV_PIP="$VENV_DIR/bin/pip"
VENV_PYTHON="$VENV_DIR/bin/python"

# ════════════════════════════════════════════════════════════════
# 6. INSTALL PYTHON DEPENDENCIES
# ════════════════════════════════════════════════════════════════
info "Installing Python backend dependencies..."

REQUIREMENTS="$BACKEND_DIR/requirements.txt"
if [[ ! -f "$REQUIREMENTS" ]]; then
  die "requirements.txt not found at $REQUIREMENTS. The project files may be incomplete."
fi

"$VENV_PIP" install --upgrade pip --quiet
"$VENV_PIP" install -r "$REQUIREMENTS" --quiet \
  || die "Failed to install Python dependencies. Check your internet connection and try again."
success "Python dependencies are ready."

# ════════════════════════════════════════════════════════════════
# 7. INSTALL NODE DEPENDENCIES
# ════════════════════════════════════════════════════════════════
info "Installing frontend Node.js dependencies..."

if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
  die "package.json not found at $FRONTEND_DIR. The project files may be incomplete."
fi

# Only run npm install if node_modules doesn't exist or package.json changed
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  info "node_modules not found — running npm install (this may take a minute)..."
  npm install --prefix "$FRONTEND_DIR" --silent \
    || die "Failed to install Node.js dependencies. Check your internet connection and try again."
  success "Node.js dependencies installed."
else
  success "Node.js dependencies already installed."
fi

# ════════════════════════════════════════════════════════════════
# 8. CHECK PORT AVAILABILITY
# ════════════════════════════════════════════════════════════════
info "Checking port availability..."

check_port() {
  local port="$1"
  local name="$2"
  if lsof -i :"$port" &>/dev/null 2>&1 || ss -tlnp "sport = :$port" 2>/dev/null | grep -q LISTEN; then
    warn "Port $port ($name) is already in use."
    echo "    You may have another instance running. It will likely still work."
    echo "    If the app doesn't start, close whatever is using port $port and try again."
  else
    success "Port $port ($name) is available."
  fi
}

check_port 8000 "Backend"
check_port 5173 "Frontend"

# ════════════════════════════════════════════════════════════════
# 9. START BACKEND
# ════════════════════════════════════════════════════════════════
echo ""
info "Starting backend server..."

"$VENV_DIR/bin/uvicorn" main:app --reload \
  --app-dir "$BACKEND_DIR" \
  >> "$BACKEND_DIR/app.log" 2>&1 &
BACKEND_PID=$!

# Wait up to 10 seconds for the backend to become healthy
BACKEND_READY=false
for i in {1..20}; do
  sleep 0.5
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    error "Backend process crashed on startup. Check logs below:"
    echo ""
    tail -30 "$BACKEND_DIR/app.log" | sed 's/^/    /'
    die "Backend failed to start."
  fi
  if grep -q "Application startup complete" "$BACKEND_DIR/app.log" 2>/dev/null; then
    BACKEND_READY=true
    break
  fi
done

if [[ "$BACKEND_READY" == false ]]; then
  error "Backend did not become ready in time. Check logs at: $BACKEND_DIR/app.log"
  echo ""
  tail -20 "$BACKEND_DIR/app.log" | sed 's/^/    /'
  die "Backend startup timed out."
fi

success "Backend is running at http://localhost:8000"

# ════════════════════════════════════════════════════════════════
# 10. START FRONTEND
# ════════════════════════════════════════════════════════════════
info "Starting frontend dev server..."

npm run dev --prefix "$FRONTEND_DIR" \
  >> "$FRONTEND_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

# Wait up to 15 seconds for Vite to become ready
FRONTEND_READY=false
FRONTEND_PORT=5173
for i in {1..30}; do
  sleep 0.5
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    error "Frontend process crashed on startup. Check logs below:"
    echo ""
    tail -20 "$FRONTEND_DIR/frontend.log" | sed 's/^/    /'
    die "Frontend failed to start."
  fi
  # Vite might pick 5173 or 5174 if 5173 is busy
  if grep -qE "Local:.*localhost" "$FRONTEND_DIR/frontend.log" 2>/dev/null; then
    FRONTEND_PORT=$(grep -oP 'localhost:\K\d+' "$FRONTEND_DIR/frontend.log" | head -1)
    FRONTEND_READY=true
    break
  fi
done

if [[ "$FRONTEND_READY" == false ]]; then
  error "Frontend did not become ready in time. Check logs at: $FRONTEND_DIR/frontend.log"
  die "Frontend startup timed out."
fi

success "Frontend is running at http://localhost:${FRONTEND_PORT}"

# ════════════════════════════════════════════════════════════════
# 11. DONE — OPEN BROWSER
# ════════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║   ✅  Application is ready!                  ║${NC}"
echo -e "${BOLD}${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}${GREEN}║   🌐  Open in browser:                       ║${NC}"
echo -e "${BOLD}${GREEN}║       http://localhost:${FRONTEND_PORT}              ║${NC}"
echo -e "${BOLD}${GREEN}║                                              ║${NC}"
echo -e "${BOLD}${GREEN}║   📋  Logs:                                  ║${NC}"
echo -e "${BOLD}${GREEN}║       Backend:  backend/app.log              ║${NC}"
echo -e "${BOLD}${GREEN}║       Frontend: frontend/frontend.log        ║${NC}"
echo -e "${BOLD}${GREEN}║                                              ║${NC}"
echo -e "${BOLD}${GREEN}║   🛑  Press Ctrl+C to stop everything        ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# Try to auto-open browser (works on most Linux desktops and macOS)
if command -v xdg-open &>/dev/null; then
  xdg-open "http://localhost:${FRONTEND_PORT}" &>/dev/null &
elif command -v open &>/dev/null; then
  open "http://localhost:${FRONTEND_PORT}" &>/dev/null &
fi

# ── Keep script alive — both processes die when we Ctrl+C ────
wait "$BACKEND_PID" "$FRONTEND_PID"
