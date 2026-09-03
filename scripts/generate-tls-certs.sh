#!/usr/bin/env bash
# ============================================
# RIZZ — TLS cert generator
# ============================================
# Generates either a self-signed cert (dev) or prepares a Let's Encrypt
# workflow (prod) for the nginx reverse proxy.
#
# Usage:
#   ./scripts/generate-tls-certs.sh dev   [domain]   # self-signed, default localhost
#   ./scripts/generate-tls-certs.sh prod  <domain>   # Let's Encrypt via certbot
#
# Output:
#   dev  -> ssl/selfsigned.crt + ssl/selfsigned.key  (relative to project root)
#   prod -> issues via certbot and symlinks to ssl/<domain>.{crt,key}
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SSL_DIR="$PROJECT_ROOT/ssl"

MODE="${1:-dev}"
DOMAIN="${2:-localhost}"
EMAIL="${LETSENCRYPT_EMAIL:-admin@${DOMAIN}}"

mkdir -p "$SSL_DIR"

if [[ "$MODE" == "dev" ]]; then
    CRT="$SSL_DIR/selfsigned.crt"
    KEY="$SSL_DIR/selfsigned.key"
    echo "→ Generating self-signed cert for $DOMAIN (valid 365 days)"

    if ! command -v openssl >/dev/null 2>&1; then
        echo "✗ openssl not found. Install it first." >&2
        exit 1
    fi

    openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout "$KEY" \
        -out "$CRT" \
        -days 365 \
        -subj "/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:127.0.0.1" \
        2>&1 | grep -v "^writing" || true

    chmod 600 "$KEY"
    chmod 644 "$CRT"
    echo "✓ Wrote $CRT"
    echo "✓ Wrote $KEY (mode 600)"
    echo
    echo "Configure nginx to use these paths:"
    echo "  ssl_certificate     /etc/nginx/ssl/selfsigned.crt;"
    echo "  ssl_certificate_key /etc/nginx/ssl/selfsigned.key;"
    echo
    echo "Browsers will warn about self-signed certs. Click through for local dev."

elif [[ "$MODE" == "prod" ]]; then
    if [[ -z "${LETSENCRYPT_EMAIL:-}" && -z "${2:-}" ]]; then
        echo "✗ For prod mode, provide a domain as 2nd arg or set LETSENCRYPT_EMAIL." >&2
        exit 1
    fi
    if ! command -v certbot >/dev/null 2>&1; then
        echo "✗ certbot not found. Install it: pkg install certbot (Termux) or apt install certbot (Debian/Ubuntu)" >&2
        exit 1
    fi

    echo "→ Requesting Let's Encrypt cert for $DOMAIN (email: $EMAIL)"
    echo "  Make sure DNS A/AAAA record for $DOMAIN points to this server's public IP."
    echo "  Port 80 must be reachable from the internet for HTTP-01 challenge."
    read -rp "Continue? [y/N] " yn
    [[ "$yn" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }

    certbot certonly --standalone \
        --non-interactive --agree-tos \
        -d "$DOMAIN" \
        --email "$EMAIL"

    CRT_SRC="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    KEY_SRC="/etc/letsencrypt/live/$DOMAIN/privkey.pem"
    CRT_DST="$SSL_DIR/$DOMAIN.crt"
    KEY_DST="$SSL_DIR/$DOMAIN.key"

    cp "$CRT_SRC" "$CRT_DST"
    cp "$KEY_SRC" "$KEY_DST"
    chmod 644 "$CRT_DST"
    chmod 600 "$KEY_DST"

    echo "✓ Wrote $CRT_DST"
    echo "✓ Wrote $KEY_DST (mode 600)"
    echo
    echo "Renewal: certbot renew --post-hook 'docker restart rizz-nginx'"
    echo "Cron example: 0 3 * * * certbot renew --quiet --post-hook 'docker restart rizz-nginx'"

else
    echo "Usage: $0 {dev [domain] | prod <domain>}" >&2
    exit 1
fi
