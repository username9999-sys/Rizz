#!/usr/bin/env bash
# ============================================
# RIZZ — secrets generator
# ============================================
# Generates strong random values for every env var that docker-compose
# declares as required (:-? substitution). Writes to .env in the project
# root, gitignored. Re-run anytime to rotate.
#
# Usage:
#   ./scripts/generate-secrets.sh            # writes .env (overwrites)
#   ./scripts/generate-secrets.sh --stdout   # prints to stdout instead
#   ./scripts/generate-secrets.sh --check    # only checks if .env is complete
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Args
MODE="write"
for arg in "$@"; do
    case "$arg" in
        --stdout) MODE="stdout" ;;
        --check)  MODE="check" ;;
        -h|--help)
            sed -n '2,16p' "$0"
            exit 0
            ;;
    esac
done

# Required env var names (must match :? substitutions in compose files)
REQUIRED_VARS=(
    POSTGRES_PASSWORD
    MONGO_PASSWORD
    REDIS_PASSWORD
    MINIO_ROOT_USER
    MINIO_ROOT_PASSWORD
    RABBITMQ_DEFAULT_USER
    RABBITMQ_PASSWORD
    JWT_SECRET_KEY
    SECRET_KEY
    GRAFANA_ADMIN_USER
    GRAFANA_PASSWORD
    TEMPORAL_PASSWORD
    ANALYTICS_PASSWORD
    TIMESCALE_PASSWORD
    UNLEASH_PASSWORD
    ELASTIC_PASSWORD
)

# Optional vars (have sane dev defaults)
OPTIONAL_VARS=(
    POSTGRES_USER
    POSTGRES_DB
    ALLOWED_HOSTS
    CORS_ORIGINS
    FLASK_ENV
    NODE_ENV
)

# Use openssl when available, fall back to /dev/urandom
random_secret() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 48 | tr -d '\n=' | head -c 64
    else
        head -c 48 /dev/urandom | base64 | tr -d '\n=' | head -c 64
    fi
}

random_user() {
    echo "rizz_$(head -c 6 /dev/urandom | xxd -p | head -c 8)"
}

# Check mode: ensure every REQUIRED var is set and not a placeholder
if [[ "$MODE" == "check" ]]; then
    if [[ ! -f "$ENV_FILE" ]]; then
        echo "✗ .env not found at $ENV_FILE"
        exit 1
    fi
    missing=()
    placeholders=()
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
    for v in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!v:-}" ]]; then
            missing+=("$v")
        elif [[ "${!v}" == CHANGE_ME_* ]] || [[ "${!v}" == "changeme" ]] || [[ "${!v}" == "minioadmin" ]] || [[ "${!v}" == "minio" ]]; then
            placeholders+=("$v")
        fi
    done
    if (( ${#missing[@]} > 0 )); then
        echo "✗ Missing required vars: ${missing[*]}"
        exit 1
    fi
    if (( ${#placeholders[@]} > 0 )); then
        echo "✗ Placeholder values for: ${placeholders[*]}"
        exit 1
    fi
    echo "✓ .env is complete and all values look strong"
    exit 0
fi

# Generate new values
declare -A VALUES
for v in "${REQUIRED_VARS[@]}"; do
    case "$v" in
        *_USER)
            VALUES[$v]="$(random_user)"
            ;;
        *_PASSWORD)
            VALUES[$v]="$(random_secret)"
            ;;
        *_KEY)
            VALUES[$v]="$(random_secret | tr -d '/+=' | head -c 64)"
            ;;
        *)
            VALUES[$v]="$(random_secret)"
            ;;
    esac
done

# Build output
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OUTPUT="# ===================================
# RIZZ — generated secrets
# Created: $TIMESTAMP
# DO NOT COMMIT. .gitignore excludes .env.
# ===================================

# === Database ===
POSTGRES_USER=${VALUES[POSTGRES_USER]:-rizz_admin}
POSTGRES_DB=${VALUES[POSTGRES_DB]:-rizz_api}
POSTGRES_PASSWORD=${VALUES[POSTGRES_PASSWORD]}

MONGO_INITDB_ROOT_USERNAME=${VALUES[POSTGRES_USER]:-rizz_admin}
MONGO_PASSWORD=${VALUES[MONGO_PASSWORD]}

# === Cache / Queue ===
REDIS_PASSWORD=${VALUES[REDIS_PASSWORD]}
RABBITMQ_DEFAULT_USER=${VALUES[RABBITMQ_DEFAULT_USER]}
RABBITMQ_PASSWORD=${VALUES[RABBITMQ_PASSWORD]}

# === Object storage ===
MINIO_ROOT_USER=${VALUES[MINIO_ROOT_USER]}
MINIO_ROOT_PASSWORD=${VALUES[MINIO_ROOT_PASSWORD]}

# === Application secrets ===
SECRET_KEY=${VALUES[SECRET_KEY]}
JWT_SECRET_KEY=${VALUES[JWT_SECRET_KEY]}

# === Observability ===
ELASTIC_PASSWORD=${VALUES[ELASTIC_PASSWORD]}
GRAFANA_ADMIN_USER=${VALUES[GRAFANA_ADMIN_USER]}
GRAFANA_PASSWORD=${VALUES[GRAFANA_PASSWORD]}

# === Workflow / analytics / feature flags ===
TEMPORAL_PASSWORD=${VALUES[TEMPORAL_PASSWORD]}
ANALYTICS_PASSWORD=${VALUES[ANALYTICS_PASSWORD]}
TIMESCALE_PASSWORD=${VALUES[TIMESCALE_PASSWORD]}
UNLEASH_PASSWORD=${VALUES[UNLEASH_PASSWORD]}

# === HTTP / CORS ===
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ORIGINS=http://localhost:3000,http://localhost:5000

# === Runtime ===
FLASK_ENV=production
NODE_ENV=production
"

if [[ "$MODE" == "stdout" ]]; then
    echo "$OUTPUT"
    exit 0
fi

# Write mode
if [[ -f "$ENV_FILE" ]]; then
    BACKUP="$ENV_FILE.bak.$(date +%s)"
    cp "$ENV_FILE" "$BACKUP"
    echo "• Existing .env backed up to $BACKUP"
fi

echo "$OUTPUT" > "$ENV_FILE"
chmod 600 "$ENV_FILE"
echo "✓ Wrote $ENV_FILE (mode 600)"
echo "  Run './scripts/generate-secrets.sh --check' to verify before docker compose up"
