#!/usr/bin/env bash
# Start the Elosern MUD (Evennia) server locally for development.
#
# Applies any pending database migrations, then launches Evennia in the
# foreground. Ports are fixed by server/conf/settings.py (telnet 4000,
# web client 4001) and are not configurable at runtime.
#
# Usage:
#   serve.sh
#
# Requires uv 0.12.0 or newer with the locked environment synced
# (`uv sync --locked`). Connect through telnet at localhost:4000 or the
# web client at http://localhost:4001.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

if ! command -v uv >/dev/null 2>&1; then
    echo "❌ uv is required but was not found in PATH" >&2
    exit 1
fi

if [[ ! -f "$PROJECT_DIR/uv.lock" ]]; then
    echo "❌ Locked environment not synced; run 'uv sync --locked' first" >&2
    exit 1
fi

echo "🚀 Elosern MUD starting"
echo "   Project: ${PROJECT_DIR}"
echo "   Telnet  → localhost:4000"
echo "   Web     → http://localhost:4001"
echo "   Press Ctrl+C to stop"
echo ""

cd "$PROJECT_DIR"
uv run --locked evennia migrate --noinput
exec uv run --locked evennia start --log
