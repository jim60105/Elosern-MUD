#!/usr/bin/env bash
# Build and run the Elosern MUD container with Podman Compose.
#
# Builds the image and starts the `evennia` service in the background. On a
# first run against a fresh database volume, pass --bootstrap to run the
# one-shot superuser bootstrap service first (interactive).
#
# Usage:
#   podman-build-run.sh [--bootstrap]
#
# Options:
#   --bootstrap  Run `podman compose --profile bootstrap run --rm bootstrap`
#                before starting the service (first-run superuser setup).

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

echo "=== Building image ==="
podman compose build

echo ""
echo "=== Preparing first-run superuser (bootstrap) ==="
if [[ "${1:-}" == "--bootstrap" ]]; then
    podman compose --profile bootstrap run --rm bootstrap
    echo ""
else
    echo "   Skipping (pass --bootstrap to create the first superuser)"
fi

echo ""
echo "=== Stopping existing service ==="
podman compose down

echo ""
echo "=== Starting service in the background ==="
podman compose up -d

echo ""
echo "=== Waiting for server startup ==="
sleep 3
podman compose logs --since 30s 2>&1 | grep -E "Server successfully started|SERVERS started" || true

echo ""
echo "✅ Container running — connect via telnet to localhost:4000 or"
echo "   open the web client at http://localhost:4001"
