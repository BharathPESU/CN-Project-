#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="$SCRIPT_DIR/backend/certs"
SSL_CERT="$CERT_DIR/dev-cert.pem"
SSL_KEY="$CERT_DIR/dev-key.pem"

if ! command -v openssl &>/dev/null; then
  echo "[ERR ] openssl not found. Please install OpenSSL and retry." >&2
  exit 1
fi

mkdir -p "$CERT_DIR"

if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
  echo "[ OK ] TLS certificates already exist at backend/certs"
  exit 0
fi

openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$SSL_KEY" \
  -out "$SSL_CERT" \
  -days 365 \
  -subj "/CN=localhost" >/dev/null 2>&1

echo "[ OK ] Created self-signed TLS certificate: backend/certs/dev-cert.pem"
echo "[ OK ] Created self-signed TLS key: backend/certs/dev-key.pem"