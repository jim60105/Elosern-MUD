#!/usr/bin/env bash
# Build and run the standalone map editor container with Podman.
#
# The editor is a local, game-free tool: it reads and autosaves the authored map
# YAML directly in this checkout and needs no Evennia, Django, game database or
# Node runtime. It is independent of the game container
# (scripts/podman-build-run.sh) and can run at the same time.
#
# Usage:
#   podman-map-editor.sh [options]
#
# Options:
#   --port PORT       Host port to serve on (default: 8765)
#   --workspace DIR   Checkout the editor reads and writes (default: this repo)
#   --no-build        Reuse the local image instead of rebuilding it
#   -h, --help        Show this help
#
# The container shares the host network namespace: the service binds loopback
# only, and its Host/Origin allowlist names 127.0.0.1:<port>, so a published
# port would never reach it. The checkout is mounted read-write at /workspace
# and is owned by the invoking user (--userns=keep-id), because every editor
# command autosaves one source document.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd)"

readonly IMAGE="localhost/elosern-map-editor:dev"
readonly CONTAINER="elosern-map-editor"
readonly CONTAINERFILE="tools/map-editor/Containerfile"
readonly IGNOREFILE="tools/map-editor/.containerignore"
readonly READY_TIMEOUT_SECONDS=90

PORT=8765
WORKSPACE="$PROJECT_DIR"
BUILD=1

usage() {
    cat << 'EOF'
Build and run the standalone map editor container with Podman.

Usage:
  podman-map-editor.sh [options]

Options:
  --port PORT       Host port to serve on (default: 8765)
  --workspace DIR   Checkout the editor reads and writes (default: this repo)
  --no-build        Reuse the local image instead of rebuilding it
  -h, --help        Show this help

The container shares the host network namespace: the service binds loopback
only, and its Host/Origin allowlist names 127.0.0.1:<port>, so a published
port would never reach it. The checkout is mounted read-write at /workspace
and is owned by the invoking user (--userns=keep-id), because every editor
command autosaves one source document.
EOF
}

die() {
    echo "❌ $*" >&2
    exit 1
}

require_podman() {
    command -v podman > /dev/null 2>&1 || die "podman is required but was not found in PATH"
    [[ "$(uname -s)" == "Linux" ]] ||
        die "the map editor container needs Linux host networking (--network host); current host is $(uname -s)"
}

parse_args() {
    while (( $# )); do
        case "$1" in
            --port)
                [[ $# -ge 2 ]] || die "--port needs a value"
                PORT="$2"
                shift 2
                ;;
            --port=*)
                PORT="${1#*=}"
                shift
                ;;
            --workspace)
                [[ $# -ge 2 ]] || die "--workspace needs a value"
                WORKSPACE="$2"
                shift 2
                ;;
            --workspace=*)
                WORKSPACE="${1#*=}"
                shift
                ;;
            --no-build)
                BUILD=0
                shift
                ;;
            -h | --help)
                usage
                exit 0
                ;;
            *)
                usage >&2
                die "unknown option: $1"
                ;;
        esac
    done

    [[ "$PORT" =~ ^[0-9]+$ ]] || die "--port must be a TCP port number, got: $PORT"
    (( PORT >= 1 && PORT <= 65535 )) || die "--port must be between 1 and 65535, got: $PORT"
    [[ -d "$WORKSPACE" ]] || die "--workspace is not a directory: $WORKSPACE"
    WORKSPACE="$(cd -- "$WORKSPACE" &> /dev/null && pwd)"
    [[ -d "$WORKSPACE/content" ]] ||
        die "$WORKSPACE does not look like the Elosern checkout (no content/ directory)"
}

port_in_use() {
    (exec 3<> "/dev/tcp/127.0.0.1/$PORT") > /dev/null 2>&1
}

build_image() {
    echo "=== Building image ($IMAGE) ==="
    podman build \
        --ignorefile "$PROJECT_DIR/$IGNOREFILE" \
        -f "$PROJECT_DIR/$CONTAINERFILE" \
        -t "$IMAGE" \
        "$PROJECT_DIR"
}

replace_container() {
    echo ""
    echo "=== Stopping existing editor container ==="
    if podman container exists "$CONTAINER" 2> /dev/null; then
        podman rm --force "$CONTAINER" > /dev/null
    else
        echo "   No running editor container"
    fi
}

start_container() {
    local -a args=(--rm --detach --name "$CONTAINER"
        --security-opt no-new-privileges
        --network host
        --volume "$WORKSPACE:/workspace:Z")

    if (( EUID != 0 )); then
        args+=(--userns=keep-id --user "$(id -u):$(id -g)")
    else
        echo "⚠️  Running as root: autosaved files in $WORKSPACE will be owned by root"
    fi

    echo ""
    echo "=== Starting the editor in the background ==="
    podman run "${args[@]}" "$IMAGE" --port "$PORT" > /dev/null
}

wait_until_ready() {
    local deadline=$((SECONDS + READY_TIMEOUT_SECONDS))

    echo ""
    echo "=== Waiting for the editor to answer on 127.0.0.1:$PORT ==="
    while (( SECONDS < deadline )); do
        if ! podman container exists "$CONTAINER" 2> /dev/null; then
            podman logs "$CONTAINER" 2>&1 || true
            die "the editor container exited during startup"
        fi
        if curl --fail --silent --show-error --output /dev/null \
            "http://127.0.0.1:$PORT/api/workspace" 2> /dev/null; then
            return 0
        fi
        sleep 0.5
    done
    podman logs --tail 40 "$CONTAINER" 2>&1 || true
    die "the editor did not answer within ${READY_TIMEOUT_SECONDS}s; see 'podman logs $CONTAINER'"
}

report() {
    echo ""
    if curl --fail --silent --output /dev/null "http://127.0.0.1:$PORT/" 2> /dev/null; then
        echo "✅ Map editor running — open http://127.0.0.1:$PORT/"
    else
        echo "⚠️  Editor service is up but the browser workspace is missing from the image."
        echo "   Rebuild without --no-build; the frontend build lives in the image."
    fi
    echo "   Workspace (read/write): $WORKSPACE"
    echo "   Logs:  podman logs --follow $CONTAINER"
    echo "   Stop:  podman stop $CONTAINER"
}

main() {
    parse_args "$@"
    require_podman

    if (( BUILD )); then
        build_image
    else
        echo "=== Reusing image ($IMAGE) ==="
        podman image exists "$IMAGE" || die "image $IMAGE does not exist; run without --no-build"
    fi

    replace_container

    if port_in_use; then
        die "port $PORT is already in use on 127.0.0.1; stop that process or pass --port"
    fi

    start_container
    wait_until_ready
    report
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
