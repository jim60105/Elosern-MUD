"""Fixture helpers for the isolated browser acceptance harness.

Provides per-instance runtime allocation (dynamic loopback ports, temporary
SQLite/log/media/static roots), the deterministic seed command, and the
``evennia`` launcher command runner. All subprocesses run through the locked
uv-managed environment and never read or write the developer database.

Chromium is installed out of band (never committed): the quality workflow runs
``uv run --locked playwright install --with-deps chromium`` before any runner
that can discover these tests.
"""

from __future__ import annotations

import os
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# The settings module importable by the launcher shim.
SETTINGS_NAME = "browser_settings"
# Settings module used by the one-off seed process.
SEED_SETTINGS_DOTPATH = "web.tests.browser.browser_settings"

# Distinct per-instance services that must never collide with 4000/4001/4002
# or with each other.
PORT_COUNT = 5
TELNET_PORT, HTTP_PORT, INTERNAL_PORT, WS_PORT, AMP_PORT = range(PORT_COUNT)

# The window every allocated port is drawn from. It sits BELOW the kernel's
# ephemeral range (``net.ipv4.ip_local_port_range`` defaults to 32768-60999;
# macOS starts at 49152), so the kernel never issues one of these ports to an
# unrelated socket: ``allocate_ports`` closes its verifying sockets before the
# launcher binds, and a port in the ephemeral range can be handed straight to
# an outgoing connection or a ``bind(..., 0)`` listener in that window. On a
# packed runner that cost the browser runtimes their late-binding internal
# server port (the server process starts after the portal), which no retry can
# recover from. ``PORT_ALLOCATION_FLOOR`` stays well above privileged ports.
PORT_ALLOCATION_FLOOR = 20000
PORT_ALLOCATION_CEILING = 32000

_READY_TIMEOUT_SECONDS = 180
_READY_POLL_SECONDS = 1.0


@dataclass
class BrowserRuntime:
    """One isolated runtime: temporary roots, (deferred) dynamic ports, env.

    Port allocation is deliberately deferred: the allocated ports are released
    by the allocator and rebound by the Evennia launcher, and a sibling harness
    process can bind one inside that window. The harness therefore allocates
    ports only inside its runner-local startup lock (``allocate`` below), never
    at construction time, and draws them from below the kernel's ephemeral
    range so no unrelated socket can be handed one automatically.
    """

    root_dir: Path
    database_path: Path
    log_dir: Path
    media_dir: Path
    static_dir: Path
    cache_dir: Path
    saves_dir: Path
    ports: list[int] | None = None
    env: dict[str, str] = field(default_factory=dict)

    @property
    def telnet_port(self) -> int:
        assert self.ports is not None, "runtime ports not allocated"
        return self.ports[TELNET_PORT]

    @property
    def http_port(self) -> int:
        assert self.ports is not None, "runtime ports not allocated"
        return self.ports[HTTP_PORT]

    @property
    def websocket_port(self) -> int:
        assert self.ports is not None, "runtime ports not allocated"
        return self.ports[WS_PORT]

    @property
    def webclient_url(self) -> str:
        return f"http://127.0.0.1:{self.http_port}/webclient/"

    def allocate_ports(self) -> None:
        """Allocate the dynamic port set and wire it into the env.

        Idempotent. MUST be called while the harness startup lock is held so
        the release-then-bind window never overlaps a sibling harness
        process's own allocation or boot. The ports themselves come from below
        the kernel's ephemeral range (see :func:`allocate_ports`).
        """
        if self.ports is not None:
            return
        self.ports = allocate_ports()
        self.env.update(port_env(self.ports))

    def cleanup(self) -> None:
        """Remove every temporary root created for this instance."""
        shutil.rmtree(self.root_dir, ignore_errors=True)


#: Every port this process has handed out; two runtimes in one process must
#: never draw the same port, including across a port-conflict retry.
_ISSUED_PORTS: set[int] = set()


def _ephemeral_port_floor() -> int:
    """The lowest port the kernel issues automatically.

    Read from ``/proc`` on Linux, where the range is configurable; otherwise
    the documented platform default (32768 on Linux, 49152 on macOS) is the
    safe assumption. Either way the allocation window stays below it.
    """
    try:
        first = (
            Path("/proc/sys/net/ipv4/ip_local_port_range")
            .read_text(encoding="ascii")
            .split()[0]
        )
        return int(first)
    except (OSError, ValueError, IndexError):
        return 32768


def allocate_ports(count: int = PORT_COUNT) -> list[int]:
    """Bind ``count`` free loopback ports from below the ephemeral range.

    All sockets are bound before any is released, so the returned ports are
    distinct within one call, and a port this process already handed out is
    never returned again, so successive runtimes in one process cannot
    collide either. Across processes the harness startup lock serializes
    allocation.

    The window sits below the kernel's ephemeral range on purpose. A port the
    kernel issues automatically (an outgoing connection's source port, a
    listener created with port 0) can be handed to any socket the moment the
    verifying socket closes, and the launcher binds these ports seconds later
    -- the server process binds the internal webserver port only after the
    portal is up. Ports below the ephemeral floor are never issued
    automatically, so only an explicit binder can still contend, and the
    harness's port-conflict retry covers that residual case.
    """
    ceiling = min(PORT_ALLOCATION_CEILING, _ephemeral_port_floor())
    span = ceiling - PORT_ALLOCATION_FLOOR
    if span < count:
        raise RuntimeError(
            f"{count} ports do not fit below the ephemeral range at {ceiling}"
        )
    # A random starting point keeps repeated runs and sibling processes from
    # scanning the window in the same order.
    offset = random.randrange(span)
    sockets: list[socket.socket] = []
    ports: list[int] = []
    try:
        # The scan is bounded by the window itself, so an exhausted window
        # fails loudly instead of returning a duplicate.
        for step in range(span):
            if len(ports) == count:
                break
            port = PORT_ALLOCATION_FLOOR + (offset + step) % span
            if port in _ISSUED_PORTS:
                continue
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                sock.close()
                continue
            _ISSUED_PORTS.add(port)
            sockets.append(sock)
            ports.append(port)
        if len(ports) != count:
            raise RuntimeError(
                f"could not allocate {count} free loopback ports below {ceiling}"
            )
        return ports
    finally:
        for sock in sockets:
            sock.close()


# Env keys the runtime itself owns (derived from its fresh allocation).
RUNTIME_ENV_KEYS = frozenset(
    {
        "ELOSERN_BROWSER_DB",
        "ELOSERN_BROWSER_LOG_DIR",
        "ELOSERN_BROWSER_MEDIA_ROOT",
        "ELOSERN_BROWSER_STATIC_ROOT",
        "ELOSERN_BROWSER_CACHE_DIR",
        "ELOSERN_BROWSER_ART_ROOT",
        "ELOSERN_BROWSER_SAVES_ROOT",
        "ELOSERN_BROWSER_TELNET_PORT",
        "ELOSERN_BROWSER_HTTP_PORT",
        "ELOSERN_BROWSER_INTERNAL_PORT",
        "ELOSERN_BROWSER_WS_PORT",
        "ELOSERN_BROWSER_AMP_PORT",
        "WEBSOCKET_CLIENT_PROXY_PORT",
    }
)


def create_runtime(prefix: str = "elosern-browser-") -> BrowserRuntime:
    """Create one isolated runtime WITHOUT dynamic ports.

    Ports are deliberately not allocated here: the harness allocates them
    under its runner-local startup lock (``BrowserRuntime.allocate_ports``),
    closing the release-then-bind race against sibling harness processes.

    The calling test process also reads map consumers directly (a journey
    that teleports to a registered gate room resolves its node through the
    published settlement world), so this is the one place that process
    publishes the authored map world. Nothing loads at import time by design,
    and one publication is enough for every test in the process.
    """
    from world.maps import runtime as map_runtime

    map_runtime.ensure_published()
    root_dir = Path(tempfile.mkdtemp(prefix=prefix))
    log_dir = root_dir / "logs"
    media_dir = root_dir / "media"
    static_dir = root_dir / "static"
    cache_dir = root_dir / "cache"
    saves_dir = root_dir / "saves"
    database_path = root_dir / "evennia.db3"
    for directory in (log_dir, media_dir, static_dir, cache_dir, saves_dir):
        directory.mkdir(parents=True, exist_ok=True)

    env = {
        "ELOSERN_BROWSER_DB": str(database_path),
        "ELOSERN_BROWSER_LOG_DIR": str(log_dir),
        "ELOSERN_BROWSER_MEDIA_ROOT": str(media_dir),
        "ELOSERN_BROWSER_STATIC_ROOT": str(static_dir),
        "ELOSERN_BROWSER_CACHE_DIR": str(cache_dir),
        "ELOSERN_BROWSER_ART_ROOT": str(cache_dir / "art"),
        # World saves: the GM console snapshots the private database and art
        # store into this invocation's own root before an intervention, so no
        # save can reach the developer's ``server/db/saves``.
        "ELOSERN_BROWSER_SAVES_ROOT": str(saves_dir),
        # Managed browser runtimes boot against the synthetic catalogs (kit
        # ``world.tests.synthetic_data``): the seed process installs them
        # before mirroring, and the server process installs them at
        # at_server_init (``browser_startstop``), so the seeded DB carries
        # t_-keyed catalog content only. Callers override to "0" per-runtime
        # for the harness's own shipped-mode checks.
        "ELOSERN_BROWSER_SYNTH_CATALOGS": "1",
    }
    return BrowserRuntime(
        root_dir=root_dir,
        database_path=database_path,
        log_dir=log_dir,
        media_dir=media_dir,
        static_dir=static_dir,
        cache_dir=cache_dir,
        saves_dir=saves_dir,
        env=env,
    )


def journey_settlement_scope() -> tuple[str, ...]:
    """Settlement map ids a browser runtime materializes.

    Publication stays complete: a runtime adopts the whole authored map world,
    so every panel a journey reads (world map, local map, travel, legibility)
    still resolves against the full bundle. Materialization -- the persistent
    rooms, roads and display cleanup that ``world.maps.bootstrap`` writes -- is
    declared here instead of covering the whole roster. A browser journey only
    ever stands in the settlements of the two sorted-first wilderness
    entrances: the seeded home settlement and the second map the relocation
    journeys cross into. Those are the maps that must exist as rooms, and
    materializing the rest costs every shard process more boot time than the
    journeys it serves.

    The declaration is derived from the shared entrance probe
    (``world.tests.geography_fixture.entrance_refs``), never copied from the
    roster. The seed process and the server process both read it, so seeding
    and booting cannot disagree, and ``sync_grid``/``sync_wilderness`` still
    converge these maps through the real planner, transaction and rollback.

    A shipped-catalog runtime (``ELOSERN_BROWSER_SYNTH_CATALOGS`` not ``1``) also
    runs the production guild-economy sync, which resolves every service host
    into the permanent interior room it anchors at. An interior only
    materializes beside the settlement its exterior opens onto, so every
    settlement owning a published interior joins the scope even when no
    journey walks it -- a conservative startup dependency closure, not the
    exact set of occupied host rooms. The synthetic install skips that startup
    step (``browser_startstop``) and needs no such settlement.

    A creation runtime (``ELOSERN_BROWSER_CREATION=1``) also materializes every
    subrace's start settlement, because activation there places the new
    character in its start room.
    """

    from world.tests.geography_fixture import (
        entrance_refs,
        publish_shipped_map_world,
    )

    scope = {ref.map_id for ref in entrance_refs(2)}
    if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") != "1":
        from world.maps import interiors

        publish_shipped_map_world()
        scope |= {
            document.exterior.settlement
            for document in interiors.current().documents.values()
            if document.exterior is not None
        }
    if os.environ.get("ELOSERN_BROWSER_CREATION") == "1":
        from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
        from world.maps.static_references import published_static_world

        # The published static world's subrace -> start anchor family, so the
        # scope follows whichever catalogs the runtime installed.
        scope |= {
            ANCHOR_PLACEMENT_REGISTRY[anchor_key].zcoord
            for anchor_key in published_static_world().start_locations.values()
        }
    return tuple(sorted(scope))


def port_env(ports: list[int]) -> dict[str, str]:
    """The runtime env entries pinning the allocated port set."""
    return {
        "ELOSERN_BROWSER_TELNET_PORT": str(ports[TELNET_PORT]),
        "ELOSERN_BROWSER_HTTP_PORT": str(ports[HTTP_PORT]),
        "ELOSERN_BROWSER_INTERNAL_PORT": str(ports[INTERNAL_PORT]),
        "ELOSERN_BROWSER_WS_PORT": str(ports[WS_PORT]),
        "ELOSERN_BROWSER_AMP_PORT": str(ports[AMP_PORT]),
        # WebSocket port encoded into the webclient page matches the listener.
        "WEBSOCKET_CLIENT_PROXY_PORT": str(ports[WS_PORT]),
    }


def recreate_runtime(previous: BrowserRuntime | None = None) -> BrowserRuntime:
    """Create a fresh runtime, carrying over caller-set env from ``previous``.

    Used by the harness port-conflict retry: a new runtime gets fresh
    temporary roots (and, when the harness allocates them under its startup
    lock, fresh ports), but keeps caller-configured mode variables (creation,
    services, exploration, minimap) that are not runtime-owned.
    """
    runtime = create_runtime()
    if previous is not None:
        for key, value in previous.env.items():
            if key not in RUNTIME_ENV_KEYS:
                runtime.env[key] = value
    return runtime


def _base_env(runtime: BrowserRuntime, extra: dict[str, str] | None = None) -> dict[str, str]:
    """The project's environment plus runtime overrides and the venv on PATH."""
    env = os.environ.copy()
    env.update(runtime.env)
    venv_bin = os.path.dirname(sys.executable)
    env["PATH"] = os.pathsep.join([venv_bin, env.get("PATH", "")])
    if extra:
        env.update(extra)
    return env


def evennia_command(*args: str) -> list[str]:
    """The ``evennia`` launcher command with the browser-test settings."""
    return [sys.executable, "-m", "evennia", "--settings", SETTINGS_NAME, *args]


def run_launcher(
    runtime: BrowserRuntime,
    *args: str,
    timeout: int = 300,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one ``evennia --settings browser_settings <args>`` command."""
    env = _base_env(runtime, env_extra)
    return subprocess.run(
        evennia_command(*args),
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def run_migrate(runtime: BrowserRuntime) -> subprocess.CompletedProcess[str]:
    """Initialize the temporary SQLite database schema."""
    return run_launcher(runtime, "migrate")


def run_seed(runtime: BrowserRuntime) -> subprocess.CompletedProcess[str]:
    """Seed the deterministic account and activated character."""
    env = _base_env(
        runtime,
        {"DJANGO_SETTINGS_MODULE": SEED_SETTINGS_DOTPATH},
    )
    return subprocess.run(
        [sys.executable, "-m", "web.tests.browser.seed"],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )


_READY_BODY_MARKER = "id=\"main-sub\""


def webclient_ready(runtime: BrowserRuntime, timeout: float = _READY_TIMEOUT_SECONDS) -> bool:
    """Poll the allocated WebClient URL until it returns the real shell page.

    The project webclient template always contains ``id="main-sub"``; a 200
    without that marker (for example while the server is mid-restart during
    its first boot) is not considered ready.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(runtime.webclient_url, timeout=5) as response:
                if response.status == 200:
                    body = response.read(65536).decode("utf-8", "replace")
                    if _READY_BODY_MARKER in body:
                        return True
        except (urllib.error.URLError, OSError, ConnectionError):
            pass
        time.sleep(_READY_POLL_SECONDS)
    return False


# The last FAIL-LOUD startup step (``server.conf.at_server_startstop``'s
# ordered catalog). Every step logs one ``startup_step`` event into the
# runtime's ``server.log``; this one is logged on every healthy boot, and only
# after the map syncs and the official art catalog have finished.
_WORLD_BOOTSTRAP_MARKER = "step=narrative_projection_init"


def world_bootstrapped(
    runtime: BrowserRuntime, timeout: float = 120.0, poll: float = 0.5
) -> bool:
    """Wait until the server process finished its ordered startup steps.

    :func:`webclient_ready` proves the PORTAL answers; the server's own world
    bootstrap runs a few seconds later in the other process (map syncs, the
    official artwork catalog, the art sync and the art push). A session that
    logs in inside that window receives the snapshot resolved BEFORE those
    steps ran — a scene descriptor without the operator catalog's room
    position, for instance — and nothing republishes it, so a server that has
    not logged its bootstrap is not ready for a journey that reads world facts.
    """
    log_path = runtime.log_dir / "server.log"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if _WORLD_BOOTSTRAP_MARKER in log_path.read_text(
                encoding="utf-8", errors="replace"
            ):
                return True
        except OSError:
            pass
        time.sleep(poll)
    return False


def web_server_settled(
    runtime: BrowserRuntime, timeout: float = 120.0, poll: float = 1.0
) -> bool:
    """Wait until the Django website renders, proving server-side web is up.

    The Evennia server finishes its world bootstrap a few seconds after the
    portal proxy first answers the webclient URL; during that window Django
    pages can return an empty 200. The browser login journey waits for the
    real login form instead of guessing.
    """
    login_url = f"http://127.0.0.1:{runtime.http_port}/auth/login/"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(login_url, timeout=5) as response:
                body = response.read(65536).decode("utf-8", "replace")
                if response.status == 200 and "id_username" in body:
                    return True
        except (urllib.error.URLError, OSError, ConnectionError):
            pass
        time.sleep(poll)
    return False


def process_is_alive(pid: int) -> bool:
    """Return True when ``pid`` refers to a live process we may own.

    A zombie has already closed its descriptors and released its memory; only
    its parent's ``wait()`` is outstanding, and a container's PID 1 need not
    perform it, so the entry would otherwise read as alive forever. ``kill(0)``
    cannot tell that state apart, so the kernel's own report decides it.
    """
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, ProcessLookupError):
        # The PID left the table between the probe and the read; without
        # procfs there is nothing to read, so the probe stands.
        return not Path("/proc").is_dir()
    except OSError:
        return True
    fields = stat.rsplit(")", 1)[-1].split()
    # Z is a corpse no one reaped; X/x is one already fully dead.
    return bool(fields) and fields[0] not in ("Z", "X", "x")
