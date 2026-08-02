#!/usr/bin/env bash
# Serve the Elosern MUD Docsify documentation site for local development.
#
# Docsify resolves the sidebar and all navigation client-side, so a plain
# static file server is sufficient.
#
# Usage:
#   serve-docs.sh [port]
#
# Arguments:
#   port  Port number to listen on (default: 3000)
#
# Examples:
#   ./scripts/serve-docs.sh        # Serve on http://localhost:3000
#   ./scripts/serve-docs.sh 4000   # Serve on http://localhost:4000

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
DOCS_DIR="${SCRIPT_DIR}/../docs"

PORT="${1:-3000}"
if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( 10#$PORT < 1 || 10#$PORT > 65535 )); then
    echo "❌ Invalid port number: ${PORT} (must be 1~65535)" >&2
    exit 1
fi

if [[ ! -f "${DOCS_DIR}/index.html" ]]; then
    echo "❌ Docs directory not found: ${DOCS_DIR}" >&2
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "❌ uv is required but was not found in PATH" >&2
    exit 1
fi

echo "📚 Serving Elosern MUD docs"
echo "   → http://localhost:${PORT}/    (${DOCS_DIR})"
echo "   Press Ctrl+C to stop"
echo ""

exec uv run --locked python -m http.server --directory "${DOCS_DIR}" "${PORT}"
