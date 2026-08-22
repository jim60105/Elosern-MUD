"""Playwright helpers for the browser acceptance tests.

Provides localhost-only request guarding, deterministic login, outbound-message
recording, shell readiness waits, and small DOM/store helpers. All fixtures are
deterministic and never invoke an LLM, image generator, or other external
service.
"""

from __future__ import annotations

import time

from playwright.sync_api import Error, Page

# Deterministic seeded account (see seed.py).
BROWSER_ACCOUNT = "browserplayer"
BROWSER_PASSWORD = "ElosernBrowserTest!2026"

_LOCAL_HOSTS = ("127.0.0.1", "localhost")

# The webclient page always renders these shell surfaces after the store is
# active; waiting for them proves the GoldenLayout shell booted.
REQUIRED_SURFACES = (
    ".elosern-header",
    ".elosern-narrative",
    ".elosern-status",
    ".elosern-action-dock",
    ".elosern-drawer",
    "#action-dock",
    "#inputfield",
)


def guard_local_only(page: Page) -> None:
    """Fail every non-local network request.

    Requests to anything other than the loopback origins (including CDNs) are
    aborted; a browser acceptance test must never depend on a remote resource.
    """

    def _handle(route):
        url = route.request.url
        if "://" not in url:
            route.continue_()
            return
        host = url.split("://")[1].split("/")[0]
        if ":" in host:
            host = host.split(":")[0]
        if host in _LOCAL_HOSTS:
            route.continue_()
        else:
            route.abort("blockedbyclient")

    page.route("**/*", _handle)


def install_outbound_recorder(page: Page) -> None:
    """Record every client->server message in ``window.__elosernSent``.

    Wraps ``Evennia.msg`` so tests can prove that no ``ui_action`` (or only one)
    ever crosses the wire, without relying on network sniffing.
    """
    page.evaluate(
        """() => {
      if (window.__elosernRecorder) { return; }
      window.__elosernRecorder = true;
      window.__elosernSent = [];
      var original = Evennia.msg.bind(Evennia);
      Evennia.msg = function (cmdname, args, kwargs, callback) {
        window.__elosernSent.push([cmdname, args || [], kwargs || {}]);
        return original(cmdname, args, kwargs, callback);
      };
    }"""
    )


def outbound_messages(page: Page) -> list[list]:
    """Return the recorded client->server messages."""
    return page.evaluate("window.__elosernSent || []")


def sent_action_count(page: Page, action_id: str | None = None) -> int:
    """Count ``ui_action`` envelopes (optionally for one action ID)."""
    count = 0
    for cmdname, args, _kwargs in outbound_messages(page):
        if cmdname != "ui_action" or not args:
            continue
        if action_id is None or args[0].get("action_id") == action_id:
            count += 1
    return count


def login_and_open(page: Page, webclient_url: str, base_url: str) -> None:
    """Log in through Django auth and open the WebClient, waiting for the shell.

    The Evennia server performs a one-time initial-setup restart on a fresh
    database; the login page can briefly return an empty document while the
    restarted web process comes up. A short bounded retry absorbs that window.
    """
    login_url = f"{base_url}/auth/login/"
    attempts = 4
    for attempt in range(attempts):
        page.goto(login_url)
        try:
            page.wait_for_selector("#id_username", timeout=20000)
            break
        except Exception:
            if attempt == attempts - 1:
                raise
            page.wait_for_timeout(1500)
    page.fill("#id_username", BROWSER_ACCOUNT)
    page.fill("#id_password", BROWSER_PASSWORD)
    page.click('input[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.goto(webclient_url)
    wait_for_shell_active(page)


def wait_for_shell_active(page: Page, timeout: int = 60000) -> None:
    """Wait until the shell surfaces render and the store is active and unlocked."""
    for selector in REQUIRED_SURFACES:
        # The drawer input row exists in the DOM but is hidden by default
        # (behind the entry button), so existence, not visibility, is the
        # shell-ready signal for it.
        state = "attached" if selector == "#inputfield" else "visible"
        page.wait_for_selector(selector, timeout=timeout, state=state)
    page.wait_for_selector(".resource-value", timeout=timeout)
    page.wait_for_function(
        """() => {
          var b = window.__elosernBridge;
          if (!b || !b.store) { return false; }
          var s = b.store.view;
          return s && s.connected && s.phase === 'active' &&
                 !!s.epoch && !s.mutationsLocked && s.mode;
        }""",
        timeout=timeout,
    )


def store_state(page: Page) -> dict:
    """Return the current client store state (the C4 bridge hook)."""
    return page.evaluate(
        "(window.__elosernBridge && window.__elosernBridge.store.view) || null"
    )


def evaluate_tolerating_navigation(page: Page, expression: str, arg=None):
    """``page.evaluate`` that treats an in-flight navigation as "not yet".

    A page navigation destroys the execution context; an evaluate racing it
    raises Playwright's ``Execution context was destroyed`` error on the
    Python side instead of returning a value. Polling loops that must survive
    a reconnect window treat that as "not ready yet" and keep waiting.
    """
    try:
        return page.evaluate(expression, arg)
    except Error as exc:
        if "Execution context was destroyed" not in str(exc):
            raise
        return None


def suppress_one_shot_recovery_reload(page: Page) -> None:
    """Pre-consume the client's one-shot recovery reload marker.

    ``elosern_state.js`` reloads the page once per tab session (the marker
    lives in ``sessionStorage`` under ``elosern.sync_recovery_reload``) when
    the awaiting-snapshot resync budget (8 x 1.5s) is exhausted without a
    snapshot. Under a loaded runner a slow portal re-attach can outlast that
    budget mid-test; the reload would then destroy the in-page outbound
    recorder and the action client's uncertain-result state that reconnect
    tests assert on. Setting the marker here scopes the window under test to
    the client's own reconnect: a genuinely stalled reconnect still fails
    loudly at the poll deadline instead of self-reloading.
    """
    page.evaluate(
        "() => { try { window.sessionStorage.setItem("
        "'elosern.sync_recovery_reload', '1'); } catch (e) {} }"
    )


def store_state_or_none(page: Page) -> dict | None:
    """Store snapshot, or None while the client is re-bootstrapping.

    Polls that span a transport reconnect observe a window in which the
    ``Elosern`` global is briefly absent while the client re-boots; those
    polls must treat that as "not yet" instead of letting the evaluate
    raise. An in-flight page navigation is tolerated the same way (see
    ``evaluate_tolerating_navigation``).
    """
    return evaluate_tolerating_navigation(
        page,
        "() => window.__elosernBridge && window.__elosernBridge.store "
        "? window.__elosernBridge.store.view : null",
    )


def wait_for_presentation_settled(page: Page, timeout: int = 30000) -> None:
    """Wait until the store's accepted presentation revision stops advancing.

    A submitted ``ui_action`` must name the server's newest revision exactly
    (the dispatcher rejects anything else as ``stale``). Right after a command
    such as engagement the publication burst may still be in flight, with the
    store one revision behind the coordinator; a submit in that window is
    rejected before the adapter runs. Two consecutive reads that agree prove
    the burst has landed — the same quiet-gap rule the narrative settle uses.
    Also requires the client to be connected, unlocked, and out of the
    snapshot/detached phases, i.e. in a state where ``Elosern.actions.submit``
    will actually dispatch.
    """
    deadline = time.monotonic() + timeout / 1000
    previous = None
    while time.monotonic() < deadline:
        revision = page.evaluate(
            "() => { const b = window.__elosernBridge; "
            "if (!b || !b.store) { return null; } const s = b.store.view; "
            "if (!s || !s.connected || s.mutationsLocked) { return null; } "
            "if (s.phase === 'awaiting_initial_snapshot' || s.phase === 'detached') { return null; } "
            "return s.revision; }"
        )
        if revision is not None and revision == previous:
            return
        previous = revision
        page.wait_for_timeout(200)
    raise AssertionError("presentation revision never settled")


def wait_for_narrative_settled(page: Page, before: int, timeout: int = 30000) -> None:
    """Wait until the narrative exceeds ``before`` characters and stops growing.

    A plain length-exceeds wait races with the tail of a previous server
    response on a loaded runner: a later assertion can observe a partially
    settled narrative and misattribute the growth. This helper polls until two
    consecutive reads agree (a quiet gap after the last append), then falls
    back to the length-exceeds wait so a genuinely missing response still
    fails loudly with a timeout.
    """
    deadline = time.monotonic() + timeout / 1000
    previous = None
    while time.monotonic() < deadline:
        current = len(page.locator(".elosern-narrative").inner_text())
        if current > before and current == previous:
            return
        previous = current
        page.wait_for_timeout(200)
    page.wait_for_function(
        "(before) => document.querySelector('.elosern-narrative')"
        ".innerText.length > before",
        arg=before,
        timeout=timeout,
    )


def valid_status_panel(name: str, identity: str) -> dict:
    """A schema-valid available status panel for injected snapshots."""
    return {
        "schema_version": 1,
        "available": True,
        "actor": {"name": name, "identity": identity, "location": None},
        "resources": {
            "hp": {"current": 100, "maximum": 100},
            "mp": {"current": 50, "maximum": 50},
            "sp": {"current": 20, "maximum": 20},
        },
        "conditions": [],
        "disguise_active": False,
        "combat": None,
    }


def valid_local_map_panel(**overrides) -> dict:
    """A schema-valid available local_map panel for injected snapshots.

    Mirrors the exact D10a shape the server presenter emits; the grid fixture
    uses two nodes (current plus a visible neighbor) and one edge.
    """
    panel = {
        "schema_version": 1,
        "available": True,
        "layer": "grid",
        "current_node": "grid:capital_altoria:2:0",
        "title": "南門街道圖",
        "nodes": [
            {
                "id": "grid:capital_altoria:2:0",
                "label": "南門",
                "x": 2,
                "y": 0,
                "visibility": "current",
                "current": True,
                "anchor": False,
                "landmark": False,
                "action": None,
            },
            {
                "id": "grid:capital_altoria:2:1",
                "label": "南大道",
                "x": 2,
                "y": 1,
                "visibility": "visible_visited",
                "current": False,
                "anchor": False,
                "landmark": False,
                "action": {
                    "kind": "move",
                    "exit_ref": "42",
                    "destination": "grid:capital_altoria:2:1",
                },
            },
            {
                "id": "grid:capital_altoria:0:3",
                "label": "市場街",
                "x": 0,
                "y": 3,
                "visibility": "remembered",
                "current": False,
                "anchor": False,
                "landmark": False,
                "action": None,
            },
        ],
        "edges": [
            {
                "source": "grid:capital_altoria:2:0",
                "destination": "grid:capital_altoria:2:1",
                "label": "n",
                "known": True,
                "traversable": True,
            }
        ],
        "legend": ["你目前所在的位置", "尚未探索的相鄰位置"],
    }
    panel.update(overrides)
    return panel


def snapshot_envelope(epoch: str, revision: int, panels: dict, **overrides) -> dict:
    """A schema-valid full snapshot envelope (mirrors server schema)."""
    envelope = {
        "protocol_version": 1,
        "presentation_epoch": epoch,
        "revision": revision,
        "mode": "exploration",
        "panels": panels,
        "layout_version": 1,
        "server_time": {
            "year": 2026,
            "season_index": 0,
            "season_label": "春",
            "day_in_season": 1,
            "hour": 12,
            "minute": 0,
            "second": 0,
        },
    }
    envelope.update(overrides)
    return envelope


def fresh_epoch() -> str:
    """A valid 22-character epoch not yet used by a real server snapshot."""
    return "browserTestEpoch_0001a"
