"""Frozen launch configuration and the service's input bounds."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from elosern_map_core.schema import MAX_DOCUMENT_BYTES

PACKAGE_ROOT = Path(__file__).resolve().parent
#: ``tools/map-editor`` inside a repository checkout.
PROJECT_ROOT = PACKAGE_ROOT.parent
#: The repository checkout that contains this project (the default workspace).
DEFAULT_WORKSPACE = PROJECT_ROOT.parent.parent
DEFAULT_FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


@dataclass(frozen=True, slots=True)
class Limits:
    """Every size/count bound checked before parsing or expensive work."""

    #: One HTTP request body (commands and reload carry small JSON envelopes).
    max_body_bytes: int = 64 * 1024
    #: One authored YAML document; the core codec enforces the same bound.
    max_document_bytes: int = MAX_DOCUMENT_BYTES
    #: One generated artifact (partition / reference context).
    max_artifact_bytes: int = 8 * 1024 * 1024
    #: Documents discovered in one workspace read.
    max_documents: int = 4096
    #: One external static source hashed for reference-context freshness.
    max_external_file_bytes: int = 4 * 1024 * 1024
    #: External static sources hashed in one freshness check.
    max_external_files: int = 20000
    #: Total bytes hashed in one freshness check.
    max_external_total_bytes: int = 256 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class EditorConfig:
    """Where the service reads from and which origin it answers for."""

    workspace_root: Path
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    frontend_dist: Path = DEFAULT_FRONTEND_DIST
    limits: Limits = field(default_factory=Limits)
    #: Seconds between SSE keep-alive comments.
    heartbeat_seconds: float = 15.0
    #: Follow the workspace files continuously (directory watching).
    watch: bool = True
    #: Settle interval: notifications are coalesced until the directories
    #: stay quiet this long, and a failed watcher read is retried once after it.
    settle_seconds: float = 0.15
    #: Wall-clock bound of one partition job's generation process; a job
    #: that exceeds it fails (``timeout``) and leaves the artifact unchanged.
    partition_timeout_seconds: float = 900.0

    def __post_init__(self) -> None:
        if not isinstance(self.port, int) or isinstance(self.port, bool) or not (
            1 <= self.port <= 65535
        ):
            # Port 0 would leave the Host/Origin allowlist naming the wrong port.
            raise ValueError("port must be an explicit TCP port between 1 and 65535")
        object.__setattr__(
            self, "workspace_root", Path(os.path.realpath(self.workspace_root))
        )
        object.__setattr__(self, "frontend_dist", Path(self.frontend_dist))

    @property
    def allowed_hosts(self) -> frozenset[str]:
        """Exact ``Host`` header values this service answers."""

        hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}", f"[::1]:{self.port}"}
        if self.host not in LOOPBACK_HOSTS:
            bracketed = f"[{self.host}]" if ":" in self.host else self.host
            hosts.add(f"{bracketed}:{self.port}")
        return frozenset(hosts)

    @property
    def allowed_origins(self) -> frozenset[str]:
        return frozenset(f"http://{host}" for host in self.allowed_hosts)
