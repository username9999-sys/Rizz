#!/usr/bin/env bash
# ============================================
# RIZZ — local dev one-shot setup
# ============================================
# Goal: from a fresh clone to a running API + supporting services in
# under 10 minutes, with one command.
#
# Usage:
#   ./scripts/dev.sh               # full local stack (api + db + redis + nginx)
#   ./scripts/dev.sh --api-only   # only the API + sqlite, no docker
#   ./scripts/dev.sh --reset      # nuke volumes and start fresh
#   ./scripts/dev.sh --test       # run pytest instead of starting services
#   ./scripts/dev.sh --stop       # stop the dev stack
#   ./scripts/dev.sh --logs       # tail logs of all services
#
# Prerequisites:
#   - Docker + docker compose plugin OR
#   - Python 3.11+, pip, virtualenv
#
# After this script, the API is at http://localhost:5000 and the
# web portfolio at http://localhost:3000.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
SECURE_FILE="$PROJECT_ROOT/docker-compose.secure.yml"
SECRETS_SCRIPT="$SCRIPT_DIR/generate-secrets.sh"

MODE="stack"
RESET=0
TEST=0
STOP=0
LOGS=0
API_ONLY=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-only) API_ONLY=1; shift ;;
        --reset)    RESET=1; shift ;;
        --test)     TEST=1; MODE="test"; shift ;;
        --stop)     STOP=1; shift ;;
        --logs)     LOGS=1; shift ;;
        -h|--help)
            sed -n '2,30p' "$0"
            exit 0 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

cd "$PROJECT_ROOT"

# ---------- Helpers ----------
log()  { echo -e "\033[1;34m[dev]\033[0m $*"; }
warn() { echo -e "\033[1;33m[dev]\033[0m $*"; }
err()  { echo -e "\033[1;31m[dev]\033[0m $*" >&2; }

# ---------- Docker available? ----------
docker_available() {
    command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
}

# ---------- Python available? ----------
python_available() {
    command -v python3 >/dev/null 2>&1 && python3 --version
}

# ---------- Stop mode ----------
if [[ $STOP -eq 1 ]]; then
    log "Stopping dev stack"
    if [[ -f "$COMPOSE_FILE" ]] && docker_available; then
        docker compose down --remove-orphans
    fi
    # Kill any local venv server
    pkill -f "gunicorn.*app:app" 2>/dev/null || true
    pkill -f "flask run" 2>/dev/null || true
    log "Done"
    exit 0
fi

# ---------- Logs mode ----------
if [[ $LOGS -eq 1 ]]; then
    if [[ -f "$COMPOSE_FILE" ]] && docker_available; then
        docker compose logs -f --tail=100
    else
        log "No docker stack to tail"
    fi
    exit 0
fi

# ---------- Reset ----------
if [[ $RESET -eq 1 ]]; then
    log "Resetting volumes and starting fresh"
    if [[ -f "$COMPOSE_FILE" ]] && docker_available; then
        docker compose down -v --remove-orphans
    fi
fi

# ---------- Secret generation ----------
if [[ ! -f "$PROJECT_ROOT/.env" ]] && [[ -x "$SECRETS_SCRIPT" ]]; then
    log "Generating .env (first run)"
    "$SECRETS_SCRIPT" --write
elif [[ ! -f "$PROJECT_ROOT/.env" ]]; then
    warn ".env missing and secrets generator not found"
    warn "Copy .env.example to .env and fill in the values manually"
fi

# ---------- Test mode ----------
if [[ $TEST -eq 1 ]]; then
    log "Running test suite"
    if docker_available; then
        docker compose --profile test run --rm api \
            bash -c "pip install pytest pytest-flask pytest-cov && python -m pytest tests/ -v"
    else
        cd "$PROJECT_ROOT/api-server"
        if [[ ! -d .venv ]]; then
            python3 -m venv .venv
        fi
        source .venv/bin/activate
        pip install -q -r requirements.txt
        pip install -q pytest pytest-flask pytest-cov flask flask-cors prometheus-client
        python -m pytest tests/ -v
    fi
    exit 0
fi

# ---------- API-only (no docker) ----------
if [[ $API_ONLY -eq 1 ]]; then
    log "Starting API in --api-only mode (no Docker)"

    if ! python_available; then
        err "python3 not found. Install Python 3.11+ or use Docker mode."
        exit 1
    fi

    cd "$PROJECT_ROOT/api-server"
    if [[ ! -d .venv ]]; then
        log "Creating venv"
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    log "Installing deps"
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    pip install -q flask flask-cors flask-limiter flask-sqlalchemy flask-migrate prometheus-client bcrypt PyJWT

    # Use SQLite for local dev
    export DATABASE_URL="${DATABASE_URL:-sqlite:///rizz_api_dev.db}"
    export FLASK_ENV=development
    export PORT=5000

    log "Initializing database"
    python -c "from app import create_app; a = create_app('development'); print('OK')" || true

    log "Starting API on http://localhost:5000"
    log "  Endpoints: /api/v2 (info), /api/auth/register, /api/auth/login"
    log "  Docs: see README.md and openapi.yaml"
    log ""
    log "Press Ctrl+C to stop"
    exec python app.py
fi

# ---------- Full Docker stack ----------
if ! docker_available; then
    err "Docker not found or not running. Use --api-only for Python-only mode."
    exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
    err "docker-compose.yml not found at $COMPOSE_FILE"
    exit 1
fi

# Use the secure overlay if available
COMPOSE_CMD=(docker compose)
if [[ -f "$SECURE_FILE" ]]; then
    COMPOSE_CMD+=( -f docker-compose.yml -f docker-compose.secure.yml )
else
    COMPOSE_CMD+=( -f docker-compose.yml )
fi

log "Building and starting dev stack"
log "  Using compose files: ${COMPOSE_CMD[*]:1}"

"${COMPOSE_CMD[@]}" up -d --build

log ""
log "✓ Dev stack is up. Endpoints:"
log "  API:        http://localhost:5000"
log "  Web:        http://localhost:3000"
log "  Nginx:      http://localhost:80 (HTTPS: 443 if cert present)"
log "  Postgres:   localhost:5432"
log "  Redis:      localhost:6379"
log "  Grafana:    http://localhost:3001 (if monitoring up)"
log ""
log "  Run tests:  $0 --test"
log "  Tail logs:  $0 --logs"
log "  Stop:       $0 --stop"
log ""
log "  Generate fresh secrets:  $SECRETS_SCRIPT"
