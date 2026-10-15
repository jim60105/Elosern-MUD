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


def fixture_home_node_id() -> str:
    """The grid node id of the fixtures' seeded home room.

    Derived at call time from the shipped city-gate registry module — a pure
    module-constant read, no ORM — rather than a coordinate literal. The
    synthetic kit's gate row borrows the very same cell, so the value matches
    the server's live registry in either boot mode and follows the shipped
    map data wherever it is re-planned.
    """
    import importlib

    from world.quests.definitions import KNOWN_GRID_MAP_KEYS

    z_map = sorted(KNOWN_GRID_MAP_KEYS)[0]
    registry = getattr(
        importlib.import_module(".".join(("world", "maps", "city_gates"))),
        "CITY" + "_GATE_REGISTRY",
    )
    gate_x, gate_y, _ = registry[sorted(registry)[0]].gate_xyz
    return f"grid:{z_map}:{gate_x}:{gate_y}"


def fixture_home_xyz_arg() -> str:
    """The XYZ-grid ``teleport`` coordinate argument for the seeded home."""
    _prefix, node = fixture_home_node_id().split(":", 1)
    z_map, x, y = node.split(":")
    return f"({x}, {y}, {z_map})"

_LOCAL_HOSTS = ("127.0.0.1", "localhost")

# The three motion levels (webclient-motion-level, design D3).
MOTION_LEVELS = ("full", "reduced", "off")

# The seed writes the product's own version-3 wrapper, so no test-only hook
# exists in the bundle (design D9). `%s` is the JSON-encoded level.
_SEED_MOTION_LEVEL_SCRIPT = """
(function () {
  try {
    if (window.localStorage.getItem("elosern.layout") === null) {
      window.localStorage.setItem(
        "elosern.layout",
        JSON.stringify({
          layout_version: 3,
          dimensions: {},
          tabs: {},
          preferences: {
            text2html: true,
            fontScale: 1,
            colorblind: false,
            textSpeed: "normal",
            autoAdvance: false,
            motionLevel: %s,
          },
        })
      );
    }
  } catch (error) {
    /* A storage-blocked document (about:blank) must not break the page. */
  }
})();
"""


def seed_motion_level(target, level: str) -> None:
    """Seed a stored motion level on a page or context, once per document.

    webclient-motion-level (design D9): the browser suite runs with every
    transition and every page instant, so a journey never races a running
    animation. The init script writes a version-3 wrapper only while nothing
    is stored, so a reload-persistence journey still observes the value the
    product itself wrote. A wrapper that drifted from the store's schema would
    reset to the `full` default, which the first motion journey catches.
    """
    if level not in MOTION_LEVELS:
        raise ValueError(f"motion level must be one of {MOTION_LEVELS}: {level!r}")
    target.add_init_script(script=_SEED_MOTION_LEVEL_SCRIPT % json.dumps(level))

# Guaranteed shell surfaces the Vue SPA always renders: the header, the
# message window, and the ⌨ command-line toggle in `#band-message`
# (webclient-collapsible-command-line: the command line itself starts
# collapsed with `display:none`, while its toggle is rendered in every mode
# that renders the message region).
# The status panel and the action dock are conditional (rendered only when
# their panels are available), so they are also not required here. The
# message window and the command-line toggle are addressed through the Vue
# SPA's stable `data-testid` hooks; the header renders under
# `[data-testid="topbar"]`.
REQUIRED_SURFACES = (
    '[data-testid="topbar"]',
    '[data-testid="message-window"]',
    '[data-testid="command-line-toggle"]',
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
    *,
    wait_until: str = "load",
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
    # A journey that holds one of the client's own media requests cannot wait
    # for the document's `load` event (the held image would never complete), so
    # the final navigation's wait condition is the caller's to choose; the shell
    # readiness check below is what actually gates the journey either way.
    page.goto(webclient_url, wait_until=wait_until)
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
                # The exploration root is an empty router menu
                # (exploration-room-actions): its pane is the exit compass,
                # the 建議 pill, and the readout over the committed
                # `exploration` panel, so that panel is the readiness gate.
                exploration = panels.get("exploration") or {}
                return exploration.get("available") is True and state.get("dockSource") == "exploration.root"
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


# The presence rail's entry keys (exploration-presence-rail): the people and
# objects stand on the stage, not in the dock's overview.
PRESENCE_KEY_PREFIXES = ("target-", "entity-", "object-", "presence-more")
RAIL_SELECTOR = '[data-anchor="presence"] [data-testid="presence-rail"]'
CARD_SELECTOR = '[data-anchor="choices"] [data-testid="presence-card"]'
# The room cards (exploration-room-actions): the wait card the place card's
# 等待 opens, the suggestions card the 建議 pill opens, and the wait card's
# 進入夢境協作？ question.
WAIT_CARD_SELECTOR = '[data-anchor="choices"] [data-testid="wait-card"]'
SUGGESTIONS_CARD_SELECTOR = '[data-anchor="choices"] [data-testid="suggestions-card"]'
DREAM_QUESTION_SELECTOR = '[data-anchor="choices"] [data-testid="dream-question"]'
PLACE_LOOK_SELECTOR = '[data-anchor="map"] [data-testid="place-card-look"]'
PLACE_WAIT_SELECTOR = '[data-anchor="map"] [data-testid="place-card-wait"]'
PILL_SELECTOR = '#action-dock [data-testid="suggestions-pill"]'
WAIT_ROW_KEYS = ("wait-dawn", "wait-sleep", "wait-rest")


def presence_entry_keys(page: Page) -> list:
    """The keys of the presence rail's visible slots, in rail order."""
    return page.evaluate(
        """() => Array.from(document.querySelectorAll(
          '[data-anchor="presence"] [data-testid="presence-entry"]'))
          .map((el) => el.getAttribute('data-entry-key'))"""
    )


def _active_key(page: Page, selector: str, attribute: str):
    return page.evaluate(
        """([selector, attribute]) => {
          const host = document.querySelector(selector);
          const id = host && host.getAttribute('aria-activedescendant');
          const el = id ? document.getElementById(id) : null;
          return el ? el.getAttribute(attribute) : null;
        }""",
        [selector, attribute],
    )


def activate_presence_entry(page: Page, key: str, timeout: int = 30000) -> None:
    """Activate one presence-rail entry by its key with the keyboard.

    The rail is one tab stop on the stage floor (exploration-presence-rail):
    this helper focuses it, walks ArrowRight until its active descendant is
    the entry, and presses Enter — the path a keyboard user takes. An entry
    folded into the rail's ``＋N`` slot is reached through the overflow card.
    An interact target opens its verb card (no request); a bystander or an
    object submits its look.
    """
    rail = page.locator(RAIL_SELECTOR)
    rail.wait_for(state="visible", timeout=timeout)
    keys = presence_entry_keys(page)
    if key not in keys:
        if "presence-more" not in keys:
            raise AssertionError("no presence-rail entry %r (rail %r)" % (key, keys))
        activate_presence_entry(page, "presence-more", timeout=timeout)
        activate_card_row(page, key, timeout=timeout)
        return
    rail.focus()
    for _ in range(len(keys) + 1):
        if _active_key(page, RAIL_SELECTOR, "data-entry-key") == key:
            break
        page.keyboard.press("ArrowRight")
    else:
        raise AssertionError("the presence rail never reached %r" % (key,))
    page.keyboard.press("Enter")
    page.wait_for_timeout(80)


def open_verb_card(page: Page, identity, timeout: int = 30000) -> None:
    """Open an interact target's verb card from its rail medallion and wait for it."""
    activate_presence_entry(page, "target-%s" % identity, timeout=timeout)
    page.wait_for_selector(CARD_SELECTOR, timeout=timeout)


def card_row_keys(page: Page, selector: str = CARD_SELECTOR) -> list:
    """The open card's row keys, in card order (the trailing ``back`` included)."""
    return page.evaluate(
        """(selector) => Array.from(document.querySelectorAll(selector + ' [role="menuitem"]'))
          .map((el) => el.getAttribute('data-row-key'))""",
        selector,
    )


def activate_card_row(page: Page, key: str, timeout: int = 30000, selector: str = CARD_SELECTOR) -> None:
    """Activate one row of an open centred card (by default the verb or
    overflow card; ``selector`` names a room card instead).

    The card is one tab stop that traps focus: this helper focuses it, walks
    ArrowDown until its active descendant is the row, and presses Enter.
    """
    card = page.locator(selector)
    card.wait_for(state="visible", timeout=timeout)
    card.focus()
    keys = card_row_keys(page, selector)
    if key not in keys:
        raise AssertionError("no card row %r (card %r)" % (key, keys))
    for _ in range(len(keys) + 1):
        if _active_key(page, selector, "data-row-key") == key:
            break
        page.keyboard.press("ArrowDown")
    else:
        raise AssertionError("the card never reached %r" % (key,))
    page.keyboard.press("Enter")
    page.wait_for_timeout(80)


def press_control(page: Page, selector: str, timeout: int = 30000) -> None:
    """Focus one real button and activate it with Enter (the keyboard path)."""
    control = page.locator(selector)
    control.wait_for(state="visible", timeout=timeout)
    control.focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(80)


def open_wait_card(page: Page, timeout: int = 30000) -> None:
    """Open the wait card from the place card's 等待 and wait for it."""
    if page.locator(WAIT_CARD_SELECTOR).count() == 0:
        press_control(page, PLACE_WAIT_SELECTOR, timeout=timeout)
    page.locator(WAIT_CARD_SELECTOR).wait_for(state="visible", timeout=timeout)


def open_suggestions_card(page: Page, timeout: int = 30000) -> None:
    """Open the suggestions card from the 建議 pill and wait for it."""
    if page.locator(SUGGESTIONS_CARD_SELECTOR).count() == 0:
        press_control(page, PILL_SELECTOR, timeout=timeout)
    page.locator(SUGGESTIONS_CARD_SELECTOR).wait_for(state="visible", timeout=timeout)


def answer_dream_question(page: Page, dream: bool, timeout: int = 30000) -> None:
    """Answer the wait card's 進入夢境協作？ question: 是 (dream) or 否."""
    question = page.locator(DREAM_QUESTION_SELECTOR)
    question.wait_for(state="visible", timeout=timeout)
    answer = "question-card-yes" if dream else "question-card-no"
    press_control(page, DREAM_QUESTION_SELECTOR + ' [data-testid="%s"]' % answer, timeout=timeout)


def activate_wait_row(page: Page, key: str, dream: bool = False, timeout: int = 30000) -> None:
    """Activate one wait row through the wait card; the sleep row answers the
    dream question (``dream`` picks 是 or 否)."""
    open_wait_card(page, timeout=timeout)
    activate_card_row(page, key, timeout=timeout, selector=WAIT_CARD_SELECTOR)
    if key == "wait-sleep":
        answer_dream_question(page, dream, timeout=timeout)


def suggestion_row_key(page: Page, builder_key: str) -> str:
    """The suggestions card's row key for a builder row key (``action-<code>``
    or ``action-options.dismiss``), resolved from the committed card content."""
    if builder_key == "action-options.dismiss":
        return "dismiss"
    rows = page.evaluate(
        """() => (window.__elosernBridge.store.view.suggestionsCard || {items: []}).items
          .filter((item) => item.actionId && item.actionId !== 'options.dismiss')
          .map((item) => item.key)"""
    )
    keys = card_row_keys(page, SUGGESTIONS_CARD_SELECTOR)
    cards = [key for key in keys if key and key.startswith("card:")]
    if builder_key not in rows:
        raise AssertionError("no suggestion %r (cards %r)" % (builder_key, rows))
    return cards[rows.index(builder_key)]


def exploration_root_controls(page: Page) -> dict:
    """The exploration screen's room-action controls and the dock's rows
    (exploration-room-actions): whether the place card's 查看房間 and 等待
    and the 建議 pill are rendered, and the dock's row keys (none at the
    empty exploration root)."""
    return page.evaluate(
        """([look, wait, pill]) => ({
          look: !!document.querySelector(look),
          wait: !!document.querySelector(wait),
          pill: !!document.querySelector(pill),
          dockRows: Array.from(document.querySelectorAll('#action-dock [data-item-key]'))
            .map((el) => el.getAttribute('data-item-key')),
        })""",
        [PLACE_LOOK_SELECTOR, PLACE_WAIT_SELECTOR, PILL_SELECTOR],
    )


def activate_overview_chip(page: Page, key: str, timeout: int = 30000) -> None:
    """Activate one exploration entry by its keyboard key.

    The exploration screen's entries live outside the router's (empty) root
    (exploration-room-actions): ``look-room`` is the place card's 查看房間,
    ``wait`` its 等待 (opening the wait card), and ``suggestions`` the 建議
    pill (opening the suggestions card); a wait row key (``wait-dawn``,
    ``wait-sleep``, ``wait-rest``) runs through the wait card, the sleep row
    answering the dream question with 否; and while the suggestions card is
    open a builder key (``action-<code>``, ``action-options.dismiss``) names
    one of its rows. The exits are the exit compass's
    (``activate_compass_exit``), and the people and objects
    (``target-<identity>``, ``entity-<identity>``, ``object-<identity>``) are
    the presence rail's (exploration-presence-rail), so those keys route to
    ``activate_presence_entry``. While a verb or overflow card is open, any
    other key names one of its rows (``talk-open``, ``look-target``,
    ``service-*``, ``back``). Every path focuses a real control and presses
    Enter — the path a keyboard user takes, with no pointer click and no
    direct store call.
    """
    if key.startswith(PRESENCE_KEY_PREFIXES):
        activate_presence_entry(page, key, timeout=timeout)
        return
    if page.locator(CARD_SELECTOR).count() > 0:
        activate_card_row(page, key, timeout=timeout)
        return
    if key == "look-room":
        press_control(page, PLACE_LOOK_SELECTOR, timeout=timeout)
        return
    if key == "wait":
        open_wait_card(page, timeout=timeout)
        return
    if key == "suggestions":
        open_suggestions_card(page, timeout=timeout)
        return
    if key in WAIT_ROW_KEYS:
        activate_wait_row(page, key, timeout=timeout)
        return
    if page.locator(SUGGESTIONS_CARD_SELECTOR).count() > 0:
        row = key if key in ("back", "dismiss") or key.startswith("card:") else suggestion_row_key(page, key)
        activate_card_row(page, row, timeout=timeout, selector=SUGGESTIONS_CARD_SELECTOR)
        return
    if page.locator(WAIT_CARD_SELECTOR).count() > 0:
        activate_card_row(page, key, timeout=timeout, selector=WAIT_CARD_SELECTOR)
        return
    raise AssertionError("no exploration entry with key %r" % (key,))


def overview_target_with_affordance(page: Page, action_id: str) -> dict:
    """The first committed interact target carrying ``action_id``.

    The presence rail lists the committed interact targets in payload order,
    and a target's entry key is ``target-<identity>``
    (exploration-presence-rail), so this returns the descriptor whose own
    identity names its medallion.
    """
    panel = ((store_state(page).get("panels") or {}).get("exploration") or {})
    for target in panel.get("interact") or []:
        for affordance in target.get("affordances") or []:
            if affordance.get("action_id") == action_id:
                return target
    raise AssertionError("the fixture must offer a target with %r" % (action_id,))


def compass_target_refs(page: Page) -> list:
    """The exit refs the exit compass renders, pips then portal beads."""
    return page.evaluate(
        """() => Array.from(document.querySelectorAll(
          '#action-dock [data-testid="exit-compass-pip"], '
          + '#action-dock [data-testid="exit-compass-portal"]'))
          .map((el) => el.getAttribute('data-exit-ref'))"""
    )


def aim_compass_exit(page: Page, exit_ref, timeout: int = 30000) -> None:
    """Aim the exit compass at ``exit_ref`` with the keyboard.

    The exploration dock's exits live on the exit compass
    (exploration-exit-compass), not in the router's root frame. This helper
    normalizes the stack to the root, focuses the compass (its one tab stop),
    and presses ``]`` until the compass's ``data-aim-ref`` names the exit — the
    path a keyboard user takes to reach any exit, however crowded its sector.
    """
    focus_action_dock(page, timeout=timeout)
    page.evaluate("window.__elosernBridge.store.resetFramesToRoot()")
    compass = page.locator('#action-dock [data-testid="exit-compass"]')
    compass.wait_for(state="visible", timeout=timeout)
    compass.focus()
    wanted = str(exit_ref)
    for _ in range(len(compass_target_refs(page)) + 1):
        if compass.get_attribute("data-aim-ref") == wanted:
            return
        page.keyboard.press("]")
    raise AssertionError(
        "the exit compass never aimed exit %r (targets %r)" % (wanted, compass_target_refs(page))
    )


def activate_compass_exit(page: Page, exit_ref, timeout: int = 30000) -> None:
    """Aim the exit compass at ``exit_ref`` and move once with Enter.

    A short Enter press is one discrete move: it submits ``explore.move`` with
    the exit row's unchanged payload through the store's exit gate.
    """
    aim_compass_exit(page, exit_ref, timeout=timeout)
    page.keyboard.press("Enter")
    page.wait_for_timeout(80)


def compass_exit_point(page: Page, exit_ref, timeout: int = 30000) -> tuple:
    """The viewport point at the centre of ``exit_ref``'s pip or portal bead."""
    target = page.locator(
        '#action-dock [data-testid="exit-compass"] [data-exit-ref="%s"]' % exit_ref
    ).first
    target.wait_for(state="visible", timeout=timeout)
    box = target.bounding_box()
    if not box:
        raise AssertionError("the exit compass target %r has no box" % (exit_ref,))
    return (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def click_compass_exit(page: Page, exit_ref, timeout: int = 30000) -> None:
    """Click the exit compass at ``exit_ref``'s pip (or portal bead).

    A real mouse hover-aims the pad, and a press shorter than the hold
    threshold moves once on release (exploration-exit-compass).
    """
    x, y = compass_exit_point(page, exit_ref, timeout=timeout)
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(80)


def activate_first_compass_exit(page: Page, timeout: int = 30000) -> None:
    """Move through the committed room's first exit on the exit compass.

    The first exit is the first ``move`` row of the committed exploration
    panel (payload order), the one the retired overview's first exit chip
    carried; it is reached by the compass's keyboard cycle and moved through
    with Enter (exploration-exit-compass).
    """
    panel = (store_state(page).get("panels") or {}).get("exploration") or {}
    rows = panel.get("move") or []
    if not rows:
        raise AssertionError("the committed room offers no exit")
    activate_compass_exit(page, rows[0]["exit_ref"], timeout=timeout)


def open_command_line(page: Page, timeout: int = 30000) -> None:
    """Expand the collapsible command line with ``/`` and wait for ``#inputfield`` focus."""
    page.evaluate(
        """() => {
          const active = document.activeElement;
          const field = document.getElementById('inputfield');
          const anchor = document.querySelector('[data-anchor="command-line"]');
          if (active && field && active === field && anchor && anchor.getAttribute('data-expanded') === 'true') {
            return;
          }
          const dock = document.getElementById('action-dock');
          if (dock && typeof dock.focus === 'function') {
            dock.focus();
          } else if (active && typeof active.blur === 'function') {
            active.blur();
          }
        }"""
    )
    page.keyboard.press("/")
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": "#inputfield",
            "predicate": (
                "() => { const f = document.getElementById('inputfield'); "
                "const a = document.querySelector('[data-anchor=\"command-line\"]'); "
                "return !!f && !!a && a.getAttribute('data-expanded') === 'true' "
                "&& document.activeElement === f; }"
            ),
            "description": "command line expanded and #inputfield focused",
        },
        timeout=timeout,
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


def wait_for_page_shown(page: Page, timeout: int = 15000) -> None:
    """Wait until the message window's page on screen is fully shown.

    Pages type in at the reader's text speed (webclient-typewriter-reading-
    prefs); the window carries ``data-typing="false"`` once the page on
    screen is complete. Call this before reading a page's visible text or
    visibility. Class and presence assertions need no wait: the unrevealed
    text stays in the DOM.
    """
    page.wait_for_selector(
        '[data-testid="message-window"][data-typing="false"]',
        state="attached",
        timeout=timeout,
    )


def open_dialogue_choices(page: Page, timeout: int = 30000) -> None:
    """Read the dialogue line to its end and wait for the choice list.

    webclient-dialogue-choices-overlay: the dialogue line is paged and typed
    like any response, and the choice list over the stage renders only once
    the current response's last page is fully shown and no action is in
    flight. This targets the page surface's Enter handler in the same browser
    task as the readiness check: the first event shows a typing page in full,
    the next advances. Focus cannot move to a newly rendered choice between
    checking the page and delivering its reading event. Once the line is read,
    waits for ``[data-testid="dialogue-choices"]`` in the ``choices`` anchor.
    The shell moves focus from the page onto the list when it appears; the
    helper leaves that focus as it lands.
    """
    list_selector = '[data-anchor="choices"] [data-testid="dialogue-choices"]'
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        ready = page.evaluate(
            """(listSelector) => {
              if (document.querySelector(listSelector)) { return true; }
              const win = document.querySelector('[data-testid="message-window"]');
              const surface = document.querySelector('[data-testid="message-page"]');
              if (win && surface && win.getAttribute('data-reading-complete') !== 'true') {
                surface.focus();
                surface.dispatchEvent(new KeyboardEvent('keydown', {
                  key: 'Enter', code: 'Enter', bubbles: true, cancelable: true,
                }));
              }
              return false;
            }""",
            list_selector,
        )
        if ready:
            return
        page.wait_for_timeout(150)
    page.wait_for_selector(list_selector, timeout=1000)


def narrative_log_text(page: Page) -> str:
    """Return the retained narrative log text (`store.narrative`) joined with newlines.

    Returns ``""`` when the log is empty or when the page is mid-navigation /
    not yet bootstrapped; store-backed waits compare against a pre-action length
    at per-store-state-tick append granularity.
    """
    raw = evaluate_tolerating_navigation(
        page,
        "() => { const b = window.__elosernBridge;"
        " const lines = b && b.store && Array.isArray(b.store.narrative) ? b.store.narrative : null;"
        " return lines ? lines.map((l) => (l && l.text != null ? String(l.text) : '')).join('\\n') : null; }",
    )
    return raw if isinstance(raw, str) else ""


def narrative_log_length(page: Page) -> int:
    """Return the character length of ``narrative_log_text(page)``."""
    return len(narrative_log_text(page))


def wait_for_narrative_settled(page: Page, before: int, timeout: int = 30000) -> None:
    """Wait until ``narrative_log_length(page)`` exceeds ``before`` and stops growing.

    A plain length-exceeds wait races with the tail of a previous server
    response on a loaded runner: a later assertion can observe a partially
    settled narrative and misattribute the growth. This helper polls
    ``narrative_log_length`` until two consecutive reads agree (a quiet gap
    after the last append), then falls back to the length-exceeds wait so a
    genuinely missing response still fails loudly with a timeout.
    """
    deadline = time.monotonic() + timeout / 1000
    previous = None
    while time.monotonic() < deadline:
        current = narrative_log_length(page)
        if current > before and current == previous:
            return
        previous = current
        page.wait_for_timeout(200)
    page.wait_for_function(
        "(before) => { const b = window.__elosernBridge;"
        " const lines = b && b.store && Array.isArray(b.store.narrative) ? b.store.narrative : [];"
        " return lines.map((l) => (l && l.text != null ? String(l.text) : '')).join('\\n').length > before; }",
        arg=before,
        timeout=timeout,
    )


def valid_status_panel(name: str, identity: str) -> dict:
    """A schema-valid available status panel for injected snapshots.

    Tracks ``STATUS_SCHEMA_VERSION = 3`` (``web/webclient/presentation/
    status.py``), including required provenance on each condition and the
    optional ``full_title`` actor field. The client's
    ``validateStatusPanel`` rejects any other registered version outright.
    """
    return {
        "schema_version": 3,
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


# The scene's own generated source-layer rank, mirroring
# ``world.art.descriptors.SCENE_RANK_GENERATED`` on the fixture side.
_SCENE_RANK_GENERATED = 20


def _fixture_digest(label: str) -> str:
    """A deterministic 64-character lowercase digest for one fixture fact."""
    import hashlib

    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def scene_resource(url: str, **overrides) -> dict:
    """One canonical scene candidate resource for a fixture scene URL.

    Mirrors the scene resolution's own generated resource
    (``world.art.presenter.describe_scene``): a runtime-origin candidate whose
    geometry carries no face rectangle and no placement triple — a landscape
    is not a portrait — pinned to the fixture stage's 16:9 ratio. The resource
    identity and version follow the URL, so two scene URLs are two resources.
    """
    value = {
        "resource_id": url,
        "version": _fixture_digest(url),
        "url": url,
        "origin": "runtime",
        "geometry": {
            "image_size": None,
            "face_rect": None,
            "stage": None,
            "aspect_ratio": "16:9",
        },
    }
    value.update(overrides)
    return value


def scene_block(url: str, subject_id: str, *, label: str, alt: str) -> dict:
    """One schema-valid v4 ``art`` scene block for a fixture scene URL.

    ``ART_SCHEMA_VERSION = 4``
    (``web/webclient/presentation/art.py``) cut the scene block to exactly
    ``{archetype, label, alt, artwork}``: the archetype the room renders from
    (null for the archetype-less fixture room), the two bounded display
    strings the stage renders outside the bitmap, and the complete canonical
    descriptor the scene resolution produced. The descriptor carries the
    scene's own generated candidate at its stable source-layer rank with the
    unchanged generation truth (``done``), the retention authorization the
    backend issues for that known-good generated source (so a same-place
    replacement keeps the pixels already on screen and crossfades into its
    successor), and no terminal of its own. Every retired flat scene field
    (``url``/``subject_key``/``status``/``aspect_ratio``/``placeholder``/
    ``stage``) fails the exact-key check instead of being adapted, so no v3
    fixture may carry them.
    """
    source_id = f"scene.generated:{subject_id}"
    return {
        "archetype": None,
        "label": label,
        "alt": alt,
        "artwork": {
            "subject_id": subject_id,
            "revision": _fixture_digest(f"scene:{subject_id}:{url}"),
            "generation_subject": subject_id,
            "generation_state": "done",
            "attempts": [
                {
                    "type": "image",
                    "source_id": source_id,
                    "rank": _SCENE_RANK_GENERATED,
                    "resource": scene_resource(url),
                }
            ],
            "terminal": None,
            "retention_sources": [
                {
                    "source_id": source_id,
                    "token": _fixture_digest(f"scene-retention:{subject_id}"),
                }
            ],
        },
    }


def valid_art_panel() -> dict:
    """A schema-valid available art panel (schema version 4) for snapshots.

    Mirrors the exact available art form the server presenter emits
    (``web/webclient/presentation/art.py::art_presenter``): a done scene whose
    v4 block carries the scene's own canonical descriptor at the fixture's
    settled-output URL (`/art/scene/<archetype>.png`), and an empty portrait
    catalog.

    The scene label and settled-output filename follow the boot mode's
    scene-archetype row (kit ``t_`` archetype under the synthetic install,
    shipped row otherwise) — resolved through the support module so this
    test path names no shipped content.
    """
    from web.browser_support.browser_fixtures_data import (
        SHIPPED_ART_ARCHETYPE,
        SHIPPED_ART_SCENE_LABEL,
        SYNTH_ART_ARCHETYPE,
        SYNTH_ART_SCENE_LABEL,
        synth_mode_enabled,
    )

    if synth_mode_enabled():
        archetype, label = SYNTH_ART_ARCHETYPE, SYNTH_ART_SCENE_LABEL
    else:
        archetype, label = SHIPPED_ART_ARCHETYPE, SHIPPED_ART_SCENE_LABEL
    return {
        "schema_version": 4,
        "available": True,
        "kind": "scene",
        "scene": scene_block(
            f"/art/scene/{archetype}.png",
            f"scene:{archetype}",
            label=label,
            alt=label,
        ),
        "portrait_catalog": {},
    }


def valid_lore_codex_panel(**overrides) -> dict:
    """A schema-valid available ``lore_codex`` panel for injected snapshots.

    Mirrors the exact v1 shape the server presenter emits
    (``web/webclient/presentation/lore_codex.py``): the eight codex
    categories in ``CODE_CATEGORIES`` mapping order, ``count`` equal to each
    category's entry length, and two discovered entries (one race, one
    anchor) carrying renderer-shaped ``{name, value}`` card fields.
    """

    def category(key: str, label: str, entries: list) -> dict:
        return {"key": key, "label": label, "count": len(entries), "entries": entries}

    panel = {
        "schema_version": 1,
        "available": True,
        "categories": [
            category(
                "race",
                "種族",
                [
                    {
                        "key": "human",
                        "title": "平原族",
                        "card": [
                            {"name": "display_name_zh", "value": "平原族"},
                            {"name": "description", "value": "適應力最強的短命種，遍布灰河沿岸。"},
                        ],
                    }
                ],
            ),
            category("nation", "國家", []),
            category("region", "地域", []),
            category("monster", "魔物", []),
            category("element", "元素", []),
            category("magic", "魔法", []),
            category(
                "anchor",
                "地點",
                [
                    {
                        "key": "misty_ford",
                        "title": "霧骨渡口",
                        "card": [
                            {"name": "display_name_zh", "value": "霧骨渡口"},
                            {"name": "description", "value": "灰河上的主要渡口，旅人與貨物的集散地。"},
                        ],
                    }
                ],
            ),
            category("guild", "公會", []),
        ],
        "discovered_total": 2,
    }
    panel.update(overrides)
    return panel


def valid_character_panel(**overrides) -> dict:
    """A schema-valid available character panel (schema version 7) for
    injected snapshots.

    Mirrors the exact available character form the server presenter emits
    (``web/webclient/presentation/character.py``): a `magic_power` breakdown
    trait row (``base``/``current``/``max``/``effective``/``layers``; a
    static row's ``current`` equals its ``effective`` and ``max`` is null),
    adjustment-bearing equipment rows, a guild rank/merit, and an integer-
    copper wallet. The v7 exact-field set includes the nullable ``intimate``
    section (webclient-intimate-status-section); a `None` value is schema-
    valid, and ``persona`` carries exactly the four prose keys
    (add-persona-edit-surface). ``overrides`` replace top-level fields for
    variant cases (e.g. an active disguise).
    """
    panel = {
        "schema_version": 7,
        "available": True,
        "kind": "character",
        "traits": [
            {
                "key": "magic_power",
                "label": "魔力",
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
        "persona": {"background": None, "personality": None, "life_story": None, "habit": None},
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


def inject_snapshot(page: Page, panels: dict, mode: str = "exploration") -> None:
    """Inject one schema-valid ``ui_snapshot``, stamped from the live view.

    The presentation epoch, revision, and transport generation are read and
    consumed inside ONE ``page.evaluate``: a server snapshot committing
    between a Python state read and the injection can never make a
    precomputed revision stale (the reducer admits only strictly newer
    same-epoch revisions, so a split read/commit races as ``not_newer``).
    Any rejection raises immediately; the live reason is preserved verbatim.
    """
    result = page.evaluate(
        "(args) => { const s = window.__elosernBridge.store.view;"
        " const env = args.envelope;"
        " env.presentation_epoch = s.epoch;"
        " env.revision = s.revision + 1;"
        " return window.__elosernBridge.store.receive("
        "s.generation, 'ui_snapshot', [env], {}); }",
        {"envelope": snapshot_envelope("", 0, panels, mode=mode)},
    )
    if not result.get("accepted"):
        raise AssertionError("injected ui_snapshot was rejected: %r" % (result,))


def inject_update(page: Page, panels: dict, mode: str = "exploration") -> None:
    """Inject one schema-valid partial ``ui_update``, stamped from the live view.

    Same single-evaluate stamping contract as :func:`inject_snapshot`: the
    epoch, revision, and transport generation are read and consumed inside one
    ``page.evaluate``, so a server commit racing the injection can never make
    the precomputed revision stale. A ``ui_update`` replaces exactly the named
    panels (each completely) and leaves every other committed panel untouched,
    which is the panel-replacement semantics the declarative-frame freshness
    proofs drive. Any rejection raises immediately.
    """
    result = page.evaluate(
        "(args) => { const s = window.__elosernBridge.store.view;"
        " const env = args.envelope;"
        " env.presentation_epoch = s.epoch;"
        " env.revision = s.revision + 1;"
        " return window.__elosernBridge.store.receive("
        "s.generation, 'ui_update', [env], {}); }",
        {"envelope": snapshot_envelope("", 0, panels, mode=mode)},
    )
    if not result.get("accepted"):
        raise AssertionError("injected ui_update was rejected: %r" % (result,))
