"""``python -m elosern_map_editor``: run the local editor service."""

from __future__ import annotations

import argparse
import ipaddress
import sys
from collections.abc import Sequence
from pathlib import Path

from .config import DEFAULT_FRONTEND_DIST, DEFAULT_HOST, DEFAULT_PORT, DEFAULT_WORKSPACE, EditorConfig


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="elosern-map-editor",
        description="Serve the standalone map editor for one workspace on a loopback address.",
    )
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE, help="workspace (repository) root")
    parser.add_argument("--host", default=DEFAULT_HOST, help="loopback address to bind (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="TCP port (1-65535; 0 is refused)")
    parser.add_argument("--frontend-dist", type=Path, default=DEFAULT_FRONTEND_DIST, help="built frontend directory")
    return parser


def parse_config(argv: Sequence[str] | None = None) -> EditorConfig:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if not _is_loopback(arguments.host):
        parser.error(f"--host {arguments.host!r} is not a loopback address; the editor is local-only")
    if not 1 <= arguments.port <= 65535:
        parser.error("--port must be between 1 and 65535 (an ephemeral port 0 is refused)")
    if not arguments.workspace.is_dir():
        parser.error(f"--workspace {arguments.workspace} is not a directory")
    return EditorConfig(
        workspace_root=arguments.workspace,
        host=arguments.host,
        port=arguments.port,
        frontend_dist=arguments.frontend_dist,
    )


def main(argv: Sequence[str] | None = None) -> int:
    config = parse_config(argv)

    import uvicorn

    from .app import create_app, service_of

    app = create_app(config)
    service = service_of(app)

    class EditorServer(uvicorn.Server):
        def handle_exit(self, sig, frame) -> None:  # pragma: no cover - signal path
            # End open event streams so shutdown does not wait on them.
            loop = getattr(self, "_editor_loop", None)
            if loop is not None:
                loop.call_soon_threadsafe(service.broadcaster.close)
            super().handle_exit(sig, frame)

        async def startup(self, sockets=None) -> None:
            import asyncio

            self._editor_loop = asyncio.get_running_loop()
            await super().startup(sockets=sockets)

    server = EditorServer(
        uvicorn.Config(
            app,
            host=config.host,
            port=config.port,
            access_log=False,
            log_level="info",
            timeout_graceful_shutdown=2,
            ws="none",
            lifespan="on",
        )
    )
    print(
        f"elosern-map-editor: serving {config.workspace_root} at http://{_display_host(config.host)}:{config.port}/",
        file=sys.stderr,
        flush=True,
    )
    server.run()
    return 0


def _display_host(host: str) -> str:
    return f"[{host}]" if ":" in host else host


if __name__ == "__main__":
    sys.exit(main())
