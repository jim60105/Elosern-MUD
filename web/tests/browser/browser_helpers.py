"""Playwright helpers for the browser acceptance tests.

Provides localhost-only request guarding, deterministic login, outbound-message
recording, shell readiness waits, and small DOM/store helpers. All fixtures are
deterministic and never invoke an LLM, image generator, or other external
service.
"""

from __future__ import annotations

from playwright.sync_api import Page

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
        page.wait_for_selector(selector, timeout=timeout)
    page.wait_for_selector(".resource-value", timeout=timeout)
    page.wait_for_function(
        """() => {
          var c = window.Elosern && window.Elosern.StateController;
          if (!c) { return false; }
          var s = c.getState();
          return s && s.connected && s.phase === 'active' &&
                 !!s.activeEpoch && !s.mutationsLocked && s.mode;
        }""",
        timeout=timeout,
    )


def store_state(page: Page) -> dict:
    """Return the current client store state."""
    return page.evaluate("Elosern.StateController.getState()")


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
