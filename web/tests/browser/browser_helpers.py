"""Playwright helpers for the browser acceptance tests.

Provides localhost-only request guarding, deterministic login, outbound-message
recording, shell readiness waits, and small DOM/store helpers. All fixtures are
deterministic and never invoke an LLM, image generator, or other external
service.
"""

from __future__ import annotations

import json
import time

from playwright.sync_api import Error, Page

# Deterministic seeded account (see seed.py).
BROWSER_ACCOUNT = "browserplayer"
BROWSER_PASSWORD = "ElosernBrowserTest!2026"

_LOCAL_HOSTS = ("127.0.0.1", "localhost")

# Guaranteed shell surfaces the Vue SPA always renders: the header, the
# narrative feed, and the command line (H5, webclient-hud-05-overlays-and-
# command-line: the command line is permanently present — the input field
# `#inputfield` renders in the DOM in every mode matrix that shows the
# command-line anchor, so it IS required for the shared shell-active wait).
# The status panel and the action dock are conditional (rendered only when
# their panels are available), so they are also not required here. The
# narrative feed and command line are addressed through the Vue SPA's stable
# `data-testid` hooks (the legacy `.elosern-narrative` class hooks are
# preserved by the Vue app, but the `data-testid` hooks are the stable
# contract); the header still renders under its legacy `.elosern-header`
# class.
REQUIRED_SURFACES = (
    '[data-testid="topbar"]',
    '[data-testid="narrative-feed"]',
    '[data-testid="command-line"]',
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


def login_and_open(
    page: Page,
    webclient_url: str,
    base_url: str,
    account: str = BROWSER_ACCOUNT,
    password: str = BROWSER_PASSWORD,
) -> None:
    """Log in through Django auth and open the WebClient, waiting for the shell.

    The Evennia server performs a one-time initial-setup restart on a fresh
    database; the login page can briefly return an empty document while the
    restarted web process comes up. A short bounded retry absorbs that window.
    ``account``/``password`` default to the shared browser account; pass the
    creation account to reach a creation-pending (non-exploration) character,
    whose ``services`` panel commits its registry-owned unavailable form.
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
    page.fill("#id_username", account)
    page.fill("#id_password", password)
    page.click('input[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.goto(webclient_url)
    wait_for_shell_active(page)


def wait_for_shell_active(page: Page, timeout: int = 60000) -> None:
    """Wait until the guaranteed shell surfaces render and the store is active and unlocked."""

    def _shell_active(state: dict) -> bool:
        return (
            bool(state.get("connected"))
            and state.get("phase") == "active"
            and bool(state.get("epoch"))
            and state.get("mutationsLocked") is not True
            and bool(state.get("mode"))
        )

    surfaces_js = ", ".join(repr(s) for s in REQUIRED_SURFACES)
    wait_for_store_state(
        page,
        _shell_active,
        dom_readiness={
            "selector": REQUIRED_SURFACES[0],
            "predicate": (
                "() => { const sels = [" + surfaces_js + "]; "
                "for (const sel of sels) { if (!document.querySelector(sel)) { return false; } } "
                "return true; }"
            ),
            "description": "guaranteed shell surfaces rendered",
        },
        timeout=timeout,
    )


def store_state(page: Page) -> dict:
    """Return the current client store state (the C4 bridge hook).

    The committed store view is a deeply nested object graph; returning it
    directly can exceed Playwright's result-serialization limit ("object
    reference chain is too long"). Serialize it to a JSON string in-page and
    parse it in Python.
    """
    raw = page.evaluate(
        "(window.__elosernBridge && window.__elosernBridge.store"
        " ? JSON.stringify(window.__elosernBridge.store.view) : null)"
    )
    return json.loads(raw) if raw is not None else {}


def focus_action_dock(page: Page, timeout: int = 60000) -> None:
    """Robustly focus the ``#action-dock`` element, gated on deterministic state.

    The action dock is a conditional surface (rendered only when its backing
    ``context_actions`` panel or ``suggestions`` envelope is available), so a
    raw ``document.getElementById('action-dock').focus()`` raises
    ``TypeError: Cannot read properties of null (reading 'focus')`` in a loaded
    CI runner where the dock has not mounted yet. This helper gates on the
    committed store state (the dock render condition) and the dock's DOM
    readiness in one bounded loop, then focuses it via Playwright's auto-waiting
    locator and verifies ``document.activeElement`` is the dock or a focusable
    descendant, so a swallowed focus fails with a precise diagnostic.
    """

    def _dock_ready(state: dict) -> bool:
        if not state.get("connected"):
            return False
        if state.get("suggestions"):
            return True
        panels = state.get("panels") or {}
        ca = panels.get("context_actions") or {}
        if ca.get("available"):
            kind = ca.get("kind")
            if kind == "exploration":
                return len(ca.get("affordances") or []) > 0
            if kind == "combat":
                menu = state.get("combatMenu") or {}
                return len(menu.get("items") or []) > 0
        if state.get("mode") == "creation":
            creation = panels.get("creation") or {}
            if creation.get("available"):
                return True
        return False

    deadline = time.monotonic() + timeout / 1000
    wait_for_store_state(
        page,
        _dock_ready,
        dom_readiness={
            "selector": "#action-dock",
            "predicate": (
                "() => { const d = document.querySelector('#action-dock'); "
                "if (!d) { return false; } "
                "const r = d.getBoundingClientRect(); "
                "return r.width > 0 && r.height > 0 && d.offsetParent !== null; }"
            ),
            "description": "#action-dock visible + focusable",
        },
        timeout=timeout,
    )
    remaining_ms = int((deadline - time.monotonic()) * 1000)
    if remaining_ms <= 0:
        raise AssertionError("#action-dock focus: no deadline budget remains after the store-state gate")
    page.locator("#action-dock").focus(timeout=remaining_ms)
    landed = page.evaluate(
        """() => {
          const dock = document.querySelector('#action-dock');
          const active = document.activeElement;
          if (!dock || !active) { return false; }
          return dock === active || dock.contains(active);
        }"""
    )
    if not landed:
        active = page.evaluate(
            "() => { const a = document.activeElement; "
            "return a ? (a.id || a.className || a.tagName || 'unknown') : null; }"
        )
        raise AssertionError(
            "focus did not land on #action-dock or a focusable descendant; activeElement=%r"
            % active
        )


def focus_creation_action_dock(page: Page, timeout: int = 30000) -> None:
    """Focus the shared ``#action-dock`` while in creation mode.

    Gates the focus on deterministic state with a single bounded polling loop: the
    committed store view reports creation mode and is connected and not mutation-locked;
    the creation surface (``[data-testid="creation-overlay"]``) is mounted; and exactly
    one ``#action-dock`` element with ``data-mode="creation"`` exists and is visible.
    Reuses ``evaluate_tolerating_navigation`` / ``store_state_or_none`` so a reconnect
    window (the ``Elosern`` global briefly absent, or an in-flight navigation destroying
    the execution context) is treated as "not ready yet".
    """
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        state = store_state_or_none(page)
        surface_mounted = evaluate_tolerating_navigation(
            page,
            "() => !!document.querySelector('[data-testid=\"creation-overlay\"]')",
        )
        dock = evaluate_tolerating_navigation(
            page,
            """() => {
              const d = document.querySelector('#action-dock');
              if (!d) { return { count: 0, mode: null, visible: false }; }
              const count = document.querySelectorAll('#action-dock').length;
              const r = d.getBoundingClientRect();
              const visible = r.width > 0 && r.height > 0 && d.offsetParent !== null;
              return { count: count, mode: d.getAttribute('data-mode'), visible: visible };
            }""",
        )
        if (
            state
            and state.get("mode") == "creation"
            and state.get("connected")
            and state.get("mutationsLocked") is not True
            and surface_mounted is True
            and dock is not None
            and dock["count"] == 1
            and dock["mode"] == "creation"
            and dock["visible"]
        ):
            remaining_ms = int((deadline - time.monotonic()) * 1000)
            if remaining_ms <= 0:
                raise AssertionError("creation dock focus: no deadline budget remains after the store-state gate")
            page.locator("#action-dock").focus(timeout=remaining_ms)
            landed = page.evaluate(
                """() => {
                  const dock = document.querySelector('#action-dock');
                  const active = document.activeElement;
                  if (!dock || !active) { return false; }
                  return dock === active || dock.contains(active);
                }"""
            )
            if not landed:
                active = page.evaluate(
                    "() => { const a = document.activeElement; "
                    "return a ? (a.id || a.className || a.tagName || 'unknown') : null; }"
                )
                raise AssertionError(
                    "creation dock focus did not land on #action-dock or a focusable descendant; activeElement=%r"
                    % active
                )
            return
        page.wait_for_timeout(250)
    raise AssertionError(
        "creation dock readiness gate not satisfied within %dms; store=%r"
        % (timeout, store_state_or_none(page))
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
    raw = evaluate_tolerating_navigation(
        page,
        "() => window.__elosernBridge && window.__elosernBridge.store "
        "? JSON.stringify(window.__elosernBridge.store.view) : null",
    )
    if raw is None:
        return None
    return json.loads(raw)


def wait_for_store_state(
    page: Page,
    predicate,
    dom_readiness: dict | None = None,
    timeout: int = 30000,
    interval_ms: int = 250,
) -> None:
    """Gate a test wait on deterministic store state within a single bounded deadline.

    Polls the committed store view via ``store_state_or_none`` (tolerating a
    one-shot recovery reload / in-flight navigation) and, when a
    ``dom_readiness`` descriptor is provided, also polls the surface DOM in the
    SAME loop under the SAME monotonic deadline.

    ``dom_readiness`` is a structured descriptor ``{"selector", "predicate",
    "description"}``. Its ``predicate`` is a JavaScript arrow function returning
    a truthiness result; the helper evaluates it in the polling loop. A ``None``
    store read (mid-reload) is treated as "not ready yet" and the store
    ``predicate`` is not invoked on ``None``. A DOM ``page.evaluate`` that races
    an in-flight navigation is routed through the same navigation-tolerating
    path as the store read: a recoverable "execution context was destroyed"
    error is recorded as the last evaluation error and the wait continues to the
    deadline; a non-navigation JavaScript/selector error is surfaced in the
    timeout diagnostic. On timeout the helper raises a diagnostic
    ``AssertionError`` carrying the last non-``None`` store state, whether any
    ``None`` reads occurred, the last evaluation error, and — when a
    ``dom_readiness`` descriptor is supplied — the selector's connected/visible/
    enabled state and the current ``activeElement``.
    """
    deadline = time.monotonic() + timeout / 1000
    last_state = None
    none_observed = False
    last_eval_error = None
    dom_selector = (dom_readiness or {}).get("selector")
    dom_predicate_js = (dom_readiness or {}).get("predicate")
    dom_description = (dom_readiness or {}).get("description") or dom_selector or ""

    while time.monotonic() < deadline:
        state = store_state_or_none(page)
        if state is None:
            none_observed = True
        else:
            last_state = state
            store_ok = bool(predicate(state))
            if dom_readiness is not None and dom_predicate_js:
                dom_ok = False
                try:
                    dom_result = page.evaluate(dom_predicate_js)
                    dom_ok = dom_result is not None and bool(dom_result)
                except Error as exc:
                    if "Execution context was destroyed" in str(exc):
                        last_eval_error = "Execution context was destroyed (in-flight navigation)"
                    else:
                        last_eval_error = "DOM predicate evaluate error: " + repr(exc)
            else:
                dom_ok = True
            if store_ok and dom_ok:
                return
            page.wait_for_timeout(interval_ms)

    dom_diag = None
    if dom_readiness is not None and dom_selector:
        dom_diag = evaluate_tolerating_navigation(
            page,
            """(selector) => {
                const el = document.querySelector(selector);
                if (!el) { return { connected: false, visible: false, enabled: null }; }
                const r = el.getBoundingClientRect();
                const visible = r.width > 0 && r.height > 0 && el.offsetParent !== null;
                const enabled = el.hasAttribute('disabled') ? false : (el.disabled === undefined ? null : !el.disabled);
                return { connected: true, visible: visible, enabled: enabled };
              }""",
            dom_selector,
        )
    active_element = evaluate_tolerating_navigation(
        page,
        "() => { const a = document.activeElement; "
        "return a ? (a.id || a.className || a.tagName || 'unknown') : null; }",
    )
    parts = [
        "store-state gate not satisfied within %dms",
        "last_state=%r",
        "none_observed=%s",
        "last_eval_error=%r",
    ]
    args = [timeout, last_state, none_observed, last_eval_error]
    if dom_readiness is not None:
        parts.extend(["dom_readiness=%r", "dom_diag=%r", "activeElement=%r"])
        args.extend([dom_description, dom_diag, active_element])
    raise AssertionError(" ".join(parts) % tuple(args))


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


def valid_art_panel() -> dict:
    """A schema-valid available art panel for injected snapshots.

    Mirrors the exact available art form the server presenter emits
    (``web/webclient/presentation/art.py::art_presenter``): a done scene
    with a same-origin URL, 16:9 aspect ratio, and no placeholder.
    """
    return {
        "schema_version": 1,
        "available": True,
        "kind": "scene",
        "scene": {
            "archetype": None,
            "label": "酒館內部",
            "subject_key": None,
            "status": "done",
            "url": "/art/scene/tavern_interior.png",
            "aspect_ratio": "16:9",
            "alt": "酒館內部",
            "placeholder": None,
        },
        "portrait_catalog": {},
    }


def valid_character_panel(**overrides) -> dict:
    """A schema-valid available character panel (schema version 5) for
    injected snapshots.

    Mirrors the exact available character form the server presenter emits
    (``web/webclient/presentation/character.py``): a `magic_level` breakdown
    trait row (``base``/``current``/``max``/``effective``/``layers``; a
    static row's ``current`` equals its ``effective`` and ``max`` is null),
    adjustment-bearing equipment rows, a guild rank/merit, and an integer-
    copper wallet. The v5 exact-field set includes the nullable ``intimate``
    section (webclient-intimate-status-section); a `None` value is schema-
    valid. ``overrides`` replace top-level fields for variant cases (e.g. an
    active disguise).
    """
    panel = {
        "schema_version": 5,
        "available": True,
        "kind": "character",
        "traits": [
            {
                "key": "magic_level",
                "label": "魔法階級",
                "base": 27,
                "current": 27,
                "max": None,
                "effective": 27,
                "layers": [],
            },
        ],
        "actives": [],
        "passives": [],
        "equipment": [],
        "disguise": {"active": False, "description": "", "displayed": []},
        "guild": {"rank": "銀牌", "merit": 120},
        "wallet": 3240,
        "persona": {"background": None},
        "intimate": None,
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
