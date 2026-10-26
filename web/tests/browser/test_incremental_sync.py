"""Real changed-path functional acceptance for the synchronization protocol.

Change ``webclient-sync-functional-smoke``. Every journey runs the integrated
production path end to end: a committed gameplay action reaches the session's
real publication owner (``PresentationCoordinator``), the batch crosses the
managed Evennia server, AMP, the portal and the WebSocket, and the production
reducer/view adopts it. Nothing here replaces the wire with a mock, injects a
snapshot to fake a server state, or reads a second store.

The four focused scenarios are:

1. a graphical same-area move, an ordinary nonterminal combat round and a
   terminal combat settlement publish exactly the changed panels on the exact
   committed baseline, the two settlements each publish one fresh complete
   eager checkpoint, and the text paths (a different-map traversal, an
   unchanged read action and a metadata-only skip control) keep the contract;
2. an oversized snapshot and an oversized single-panel delta travel as bounded
   general parts and adopt once, every frame inside its own limit;
3. one genuine publication dropped before the reducer makes the next result
   start the single bounded repair, and a test-scope publication that omits a
   changed panel's owner is repaired by the next real checkpoint;
4. the single repair failing is terminal (no sync loop, graphical lock, text
   still usable), an explicit synchronize re-establishes the base without
   tearing down valid local UI state, and a subscriber-held committed record
   cannot be written through.

These are functional assertions only. No latency, profiling, long-task,
allocation or no-stutter claim is made anywhere in this module; the byte limits
asserted are protocol resource bounds, not measured responsiveness.

Run one journey at a time (the full browser suite is CI-owned)::

    uv run --locked python -m web.tests.browser.unittest_driver \\
        web.tests.browser.test_incremental_sync.IncrementalSyncBrowserTests.<name>
"""

from __future__ import annotations

import hashlib
import json
import re

from tools.spec_traceability import covers_requirement

from . import fixtures
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    activate_first_compass_exit,
    focus_action_dock,
    install_outbound_recorder,
    narrative_log_text,
    open_command_line,
    outbound_messages,
    store_state,
    wait_for_shell_active,
    wait_for_presentation_settled,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from .incremental_sync_fixture import first_gate_xyz, second_map_xyz, xyz_arg

SNAPSHOT = "ui_snapshot"
UPDATE = "ui_update"
PART = "ui_publication_part"
RESULT = "ui_action_result"
PRESENTATION = frozenset({SNAPSHOT, UPDATE, PART})

# The shared publication resource limits the wire asserts (a functional
# protocol bound, never a measured workload).
PART_RAW_BYTES = 24_576
FRAME_CEILING = 65_536

# The fixture's one result line.
_RESULT_RE = re.compile(
    r"INCREMENTAL_SYNC (\w+) (\S+) (\d+) (\w+) ([01]) (\d+) ([0-9a-f]{64}) (\S+)"
)

# Panels a movement can never change: they carry no position, time or combat
# fact, so a same-area delta that named one of them would be retransmitting
# untouched data.
_MOVEMENT_FROZEN_PANELS = ("lore_codex", "sleep_handoff", "title_ballot")

_INSTALL_TRACE = """() => {
  const store = window.__elosernBridge.store;
  if (window.__syncTrace) { return false; }
  window.__syncTrace = { records: [] };
  store.subscribe((record) => { window.__syncTrace.records.push(record); });
  return true;
}"""

# Report, for the two committed records at ``previous`` and ``current``, which
# panel values were carried over by identity (``===``) and which membership the
# newer record added or dropped.
_COMPARE_RECORDS = """([previous, current]) => {
  const records = window.__syncTrace.records;
  const pick = (revision) => {
    for (let index = records.length - 1; index >= 0; index -= 1) {
      if (records[index].revision === revision) { return records[index]; }
    }
    return null;
  };
  const before = pick(previous);
  const after = pick(current);
  if (before === null || after === null) { return null; }
  const preserved = {};
  for (const name of Object.keys(after.panels)) {
    preserved[name] = before.panels[name] === after.panels[name];
  }
  return {
    preserved: preserved,
    added: Object.keys(after.panels).filter((name) => !(name in before.panels)),
    removed: Object.keys(before.panels).filter((name) => !(name in after.panels)),
    beforeEpoch: before.activeEpoch,
    afterEpoch: after.activeEpoch,
  };
}"""

# The transport fault gate: it sits in front of the reducer (the evennia.js
# socket handler calls ``Evennia.emit``, and the app's listeners are reached
# only through it), so a genuine frame can be dropped, held and released, or
# corrupted exactly as the scenario needs. ``restore`` puts the original
# function back, so no later journey sees a seam.
_INSTALL_GATE = """() => {
  if (window.__syncGate) { return false; }
  const root = window.Evennia;
  const original = root.emit;
  const gate = {
    dropNextDelta: false,
    corruptSnapshotAbove: null,
    dropped: [],
    corrupted: [],
    received: [],
  };
  const matches = (name, args) => {
    const envelope = args && args[0];
    return {
      envelope: envelope,
      revision: envelope && typeof envelope === "object" ? envelope.revision : null,
    };
  };
  root.emit = function (name, args, kwargs) {
    if (name === 'ui_snapshot' || name === 'ui_update' || name === 'ui_publication_part') {
      const seen = matches(name, args);
      if (gate.dropNextDelta && name === 'ui_update') {
        // Withhold exactly one genuine publication: the client never sees it,
        // and the next publication's baseline exposes the gap.
        gate.dropNextDelta = false;
        gate.dropped.push(seen.revision);
        return undefined;
      }
      if (
        gate.corruptSnapshotAbove !== null &&
        name === 'ui_snapshot' &&
        typeof seen.revision === 'number' &&
        seen.revision > gate.corruptSnapshotAbove
      ) {
        gate.corruptSnapshotAbove = null;
        const broken = {};
        if (seen.envelope && typeof seen.envelope === 'object') {
          for (const key of Object.keys(seen.envelope)) { broken[key] = seen.envelope[key]; }
        }
        broken.mode = 'corrupt';
        gate.corrupted.push(name);
        return original.call(root, name, [broken], kwargs);
      }
    }
    return original.call(root, name, args, kwargs);
  };
  window.__syncGate = gate;
  window.__syncGateArm = function (options) {
    Object.assign(gate, options || {});
    return true;
  };
  window.__syncGateState = function () {
    return {
      dropped: gate.dropped.slice(),
      corrupted: gate.corrupted.length,
      received: gate.received.slice(),
    };
  };
  window.__syncGateRestore = function () {
    root.emit = original;
    if (gate.patchedReceive) {
      window.__elosernBridge.store.receive = gate.originalReceive;
    }
    delete window.__syncGate;
    delete window.__syncGateArm;
    delete window.__syncGateState;
    delete window.__syncGateRestore;
    return true;
  };
  // Record the reducer's own verdict per presentation frame: a rejected frame
  // is the difference between "the server published X" and "the browser
  // adopted X", which is exactly what a fault scenario must tell apart.
  const store = window.__elosernBridge.store;
  gate.originalReceive = store.receive;
  gate.patchedReceive = true;
  store.receive = function (generation, name, args, kwargs) {
    const result = gate.originalReceive.call(this, generation, name, args, kwargs);
    if (typeof name === 'string' && name.indexOf('ui_') === 0) {
      const envelope = args && args[0];
      gate.received.push([
        name,
        envelope && typeof envelope === 'object' ? envelope.revision : null,
        result && result.accepted,
        result && result.reason,
        result && result.pending === true,
      ]);
    }
    return result;
  };
  return true;
}"""

# The subscriber-held committed record: report whether it is frozen, whether a
# write attempt changed anything, and the authoritative values afterwards.
_PROBE_COMMITTED = """() => {
  const store = window.__elosernBridge.store;
  const records = window.__syncTrace.records;
  const record = records[records.length - 1];
  const panel = record.panels && record.panels.status ? record.panels.status : null;
  const before = {
    revision: record.revision,
    panelNames: Object.keys(record.panels || {}).sort(),
    panelCopy: panel === null ? null : JSON.parse(JSON.stringify(panel)),
  };
  let revisionWriteThrew = false;
  let panelWriteThrew = false;
  try { record.revision = 999999999; } catch (error) { revisionWriteThrew = true; }
  try { if (panel !== null) { panel.available = false; } } catch (error) { panelWriteThrew = true; }
  const after = store.view;
  return {
    frozen: Object.isFrozen(record),
    panelFrozen: panel === null ? null : Object.isFrozen(panel),
    revisionWriteThrew: revisionWriteThrew,
    panelWriteThrew: panelWriteThrew,
    revisionUnchanged: after.revision === before.revision,
    panelsUnchanged:
      panel === null
        ? null
        : JSON.stringify(after.panels.status) === JSON.stringify(before.panelCopy),
    panelNames: Object.keys(after.panels || {}).sort(),
  };
}"""


def _store_active(state: dict) -> bool:
    return (
        bool(state.get("connected"))
        and state.get("phase") == "active"
        and state.get("mutationsLocked") is not True
    )


def _unlocked(state: dict) -> bool:
    return bool(state.get("connected")) and state.get("mutationsLocked") is not True


def _revision_of(frame: dict) -> int | None:
    args = frame.get("args") or []
    if not args or not isinstance(args[0], dict):
        return None
    revision = args[0].get("revision")
    return revision if isinstance(revision, int) else None


def _capture_frames(page) -> list[dict]:
    """Append every incoming OOB frame's parsed triple to one live list."""
    frames: list[dict] = []

    def on_socket(socket) -> None:
        def on_frame(payload) -> None:
            text = payload if isinstance(payload, str) else payload.decode("utf-8")
            if '"ui_' not in text:
                return
            try:
                name, args, kwargs = json.loads(text)
            except ValueError:
                return
            frames.append({"name": name, "args": args, "kwargs": kwargs, "text": text})

        socket.on("framereceived", on_frame)

    page.on("websocket", on_socket)
    return frames


def _presentation(frames: list[dict], mark: int, revision: int | None = None) -> list[dict]:
    """Presentation frames captured since ``mark``, optionally at one revision."""
    selected = [frame for frame in frames[mark:] if frame["name"] in PRESENTATION]
    if revision is None:
        return selected
    return [frame for frame in selected if _revision_of(frame) == revision]


def _results(frames: list[dict], mark: int, revision: int | None = None) -> list[dict]:
    """Action-result frames captured since ``mark``, optionally at one revision."""
    selected = [frame for frame in frames[mark:] if frame["name"] == RESULT]
    if revision is None:
        return selected
    matched = []
    for frame in selected:
        args = frame.get("args") or []
        envelope = args[0] if args and isinstance(args[0], dict) else {}
        if envelope.get("presentation_revision") == revision:
            matched.append(frame)
    return matched


def _hp_trait(state: dict) -> int:
    """The committed ``character`` panel's current hp value."""
    for row in state["panels"]["character"]["traits"]:
        if row["key"] == "hp":
            return int(row["current"])
    raise AssertionError("the character panel carries no hp trait")


def _hp_at(page, revision: int) -> int | None:
    """The current hp value in the traced committed record at ``revision``."""
    return page.evaluate(
        """([revision]) => {
          const records = window.__syncTrace.records.filter(
            (record) => record.revision === revision);
          if (records.length === 0) { return null; }
          const panel = records[records.length - 1].panels.character || null;
          if (!panel || !Array.isArray(panel.traits)) { return null; }
          const row = panel.traits.find((trait) => trait.key === 'hp');
          return row ? row.current : null;
        }""",
        [revision],
    )


class IncrementalSyncBrowserTests(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Real publication-path journeys against one dedicated managed runtime."""

    @classmethod
    def setUpClass(cls) -> None:
        # Every journey boots its own server: a live combat session and a
        # dropped/queued frame window both leave a session a later login on the
        # same server could not reuse cleanly.
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime(prefix="elosern-incremental-sync-")
        runtime.env["ELOSERN_BROWSER_INCREMENTAL_SYNC"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    # -- plumbing -----------------------------------------------------------

    def _open(self):
        """A logged-in page with the outbound recorder, frame capture and trace."""
        # The socket is created during login, so the frame capture has to be
        # armed on the page before the first navigation; a listener attached
        # afterwards would only see sockets opened by a later reconnect.
        page = self.new_page()
        frames = _capture_frames(page)
        self._login(page)
        install_outbound_recorder(page)
        # The trace is installed as soon as the bridge exists, so the initial
        # snapshot (the journey's baseline) is one of its committed records.
        page.wait_for_function(
            "() => !!(window.__elosernBridge && window.__elosernBridge.store)",
            timeout=60000,
        )
        page.evaluate(_INSTALL_TRACE)
        wait_for_shell_active(page)
        wait_for_store_state(page, _store_active, timeout=60000)
        wait_for_presentation_settled(page)
        self._settle_episode(page)
        # The initial snapshot may already have committed before the bridge
        # existed, so the journey opens with the player's own explicit
        # synchronize: one real complete checkpoint that the trace certainly
        # records, and the baseline every later identity comparison uses.
        baseline = store_state(page)["revision"]
        page.evaluate("() => Elosern.actions.client.sync()")
        wait_for_store_state(page, lambda s: s["revision"] > baseline, timeout=90000)
        wait_for_presentation_settled(page)
        self.assertEqual(
            store_state(page)["recovery"]["status"], "idle",
            "the journey starts from a clean recovery state",
        )
        self.assertIsNot(store_state(page).get("mutationsLocked"), True)
        return page, frames

    def _settle_episode(self, page) -> None:
        """Start from a generation whose recovery state is idle.

        The managed runtime's one-time initial-setup restart can leave a login
        with a terminal recovery episode (a frame of the retired sequence was
        rejected while the portal re-attached). That is setup, not a scenario
        condition: the journey reconnects once, which is the client's own
        documented exit from a terminal episode, and then requires a clean
        state before any fault is injected.
        """
        from .browser_helpers import suppress_one_shot_recovery_reload

        state = store_state(page)
        if state["recovery"]["status"] == "idle" and state.get("mutationsLocked") is not True:
            return
        suppress_one_shot_recovery_reload(page)
        generation = state.get("generation") or 1
        page.evaluate("() => { if (window.__elosernWs) window.__elosernWs.close(4001); }")
        wait_for_store_state(
            page,
            lambda s: (s.get("generation") or 0) > generation
            and s.get("recovery", {}).get("status") == "idle"
            and _store_active(s),
            timeout=90000,
        )
        wait_for_presentation_settled(page)

    def _login(self, page) -> None:
        """Authenticate and open the WebClient without waiting for the shell.

        ``login_and_open`` waits for the active shell before returning, which
        would install the commit trace after the journey's baseline snapshot
        published. This mirrors its navigation and its bounded retry over the
        one-time initial-setup restart, and leaves the shell wait to ``_open``.
        """
        from .browser_helpers import BROWSER_ACCOUNT, BROWSER_PASSWORD

        login_url = f"{self.base_url}/auth/login/"
        for attempt in range(4):
            page.goto(login_url)
            try:
                page.wait_for_selector("#id_username", timeout=20000)
                break
            except Exception:
                if attempt == 3:
                    raise
                page.wait_for_timeout(1500)
        page.fill("#id_username", BROWSER_ACCOUNT)
        page.fill("#id_password", BROWSER_PASSWORD)
        page.click('input[type="submit"]')
        page.wait_for_load_state("networkidle")
        page.goto(self.webclient_url)

    def _install_gate(self, page) -> None:
        page.evaluate(_INSTALL_GATE)
        self.addCleanup(
            lambda: page.evaluate(
                "() => (window.__syncGateRestore ? window.__syncGateRestore() : true)"
            )
        )

    def _arm_gate(self, page, **options) -> None:
        page.evaluate("(options) => window.__syncGateArm(options)", options)

    def _send_text(self, page, text: str) -> None:
        page.evaluate("(text) => window.__elosernBridge.store.sendText(text)", text)

    def _fixture(self, page, case: str) -> re.Match:
        """Run one server fixture case and return its parsed result line."""
        before = narrative_log_text(page)
        seen = len(_RESULT_RE.findall(before))
        self._send_text(
            page,
            "@py __import__('web.tests.browser.incremental_sync_fixture',"
            f" fromlist=['run']).run(me, '{case}')",
        )

        def _reported(_state: dict) -> bool:
            return len(_RESULT_RE.findall(narrative_log_text(page))) > seen

        try:
            wait_for_store_state(page, _reported, timeout=90000)
        except AssertionError as error:
            raise AssertionError(
                f"the {case} fixture reported nothing; narrative tail: "
                f"{narrative_log_text(page)[-2000:]!r}"
            ) from error
        match = _RESULT_RE.findall(narrative_log_text(page))[seen]
        self.assertEqual(match[0], case)
        return match

    # -- combat choreography (the real keyboard dock) ------------------------

    def _press(self, page, key: str) -> None:
        page.keyboard.press(key)
        page.wait_for_timeout(80)

    def _focus_key(self, page):
        return store_state(page).get("focus", {}).get("key")

    def _walk_to(self, page, key: str, limit: int = 40) -> None:
        for _ in range(limit):
            if self._focus_key(page) == key:
                return
            self._press(page, "ArrowDown")
        self.assertEqual(self._focus_key(page), key, f"never reached {key}")

    def _root(self, page) -> None:
        for _ in range(4):
            state = store_state(page)
            if state.get("dockSource") == "combat.root" and state.get("dockDepth") == 1:
                break
            self._press(page, "Escape")
        focus_action_dock(page)

    def _combat_panel(self, page) -> dict:
        return store_state(page)["panels"]["context_actions"]

    def _engage(self, page, timeout: int = 40000) -> None:
        from web.browser_support.browser_fixtures_data import combat_journey_values

        target = combat_journey_values()["engage_target"]
        page.evaluate("([t]) => Evennia.msg('text', [`engage ${t}`], {})", [target])
        wait_for_store_state(
            page,
            lambda s: s.get("mode") == "combat"
            and ((s.get("panels") or {}).get("context_actions") or {}).get("available")
            is True,
            timeout=timeout,
        )

    def _first_foe(self, page) -> int:
        for participant in self._combat_panel(page)["participants"]:
            if participant["team"] == "foes" and participant["state"] == "active":
                return int(participant["identity"])
        raise AssertionError("the combat session offers no active foe")

    def _submit_basic_attack(self, page) -> None:
        foe = self._first_foe(page)
        self._root(page)
        self._walk_to(page, "attack")
        self._press(page, "Enter")
        self._walk_to(page, f"target-{foe}")
        self._press(page, "Enter")

    def _surrender(self, page) -> None:
        """Finish the combat through its normal dock route + confirmation card."""
        self._root(page)
        wait_for_presentation_settled(page)
        before = store_state(page).get("lastActionResult")
        self._walk_to(page, "surrender")
        self._press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId")
            not in (None, (before or {}).get("requestId"))
            and (s.get("dispatch") or {}).get("inFlight") is None,
            timeout=30000,
        )
        card = page.locator('[data-testid="party-exit-question"]')
        card.wait_for(state="visible", timeout=30000)
        card.locator('[data-testid="question-card-yes"]').click()
        page.wait_for_selector(
            '[data-testid="party-exit-question"]', state="detached", timeout=30000
        )

    # -- assertions ---------------------------------------------------------

    def _assert_delta(self, page, frames: list[dict], mark: int, base: int, revision: int) -> dict:
        """Assert one exact-base delta at ``revision`` and return its envelope."""
        at_revision = _presentation(frames, mark, revision)
        names = [frame["name"] for frame in at_revision]
        self.assertEqual(names, [UPDATE], f"expected one delta at {revision}, got {names}")
        envelope = at_revision[0]["args"][0]
        self.assertEqual(envelope["base_revision"], base)
        self.assertEqual(
            [frame for frame in _presentation(frames, mark) if frame["name"] == PART],
            [],
            "an ordinary committed change must not fragment",
        )
        return envelope

    def _trace_mark(self, page) -> int:
        """The trace length now: records after it belong to the injected fault."""
        return page.evaluate("() => window.__syncTrace.records.length")

    def _assert_locked_episode(self, page, base: int, eager: set, trace_mark: int) -> list:
        """Assert the recorded episode kept the prior state and locked mutations.

        The subscriber's records are the contract's own read of every
        transition, so the locked window is asserted from them rather than by
        delaying a live frame. The window is scoped to the records after the
        fault was armed, and the retained panels must be the pre-fault values,
        not merely the same names.
        """
        episodes = page.evaluate(
            """([mark]) => {
              const records = window.__syncTrace.records;
              return records.slice(mark).map((record, index) => {
                const previous = records[mark + index - 1] || null;
                return [
                  record.revision,
                  record.recovery.status,
                  record.mutationsLocked,
                  Object.keys(record.panels || {}).sort(),
                  JSON.stringify(record.panels),
                  previous ? previous.revision : null,
                  previous ? JSON.stringify(previous.panels) : null,
                ];
              });
            }""",
            [trace_mark],
        )
        locked = [
            entry
            for entry in episodes
            if entry[1] in ("needed", "requested", "failed")
        ]
        self.assertTrue(locked, f"no recovery episode was recorded after the fault: {episodes}")
        for revision, status, is_locked, names, panels, previous, previous_panels in locked:
            self.assertGreaterEqual(
                revision, base, f"the {status} episode sits on the last committed revision"
            )
            self.assertEqual(
                revision, previous, f"the {status} episode kept the committed revision"
            )
            self.assertIs(is_locked, True, f"the {status} episode locked mutations")
            self.assertEqual(set(names), eager, f"the {status} episode kept every panel")
            self.assertEqual(
                panels,
                previous_panels,
                f"the {status} episode retained the committed values",
            )
        return episodes

    def _assert_base_mismatch(self, page, trace_mark: int) -> None:
        """Assert the fault window rejected a delta for an unadopted baseline."""
        verdicts = page.evaluate("() => window.__syncGateState().received")
        rejected = [
            entry
            for entry in verdicts
            if entry[0] == UPDATE and entry[2] is False and entry[3] == "base_mismatch"
        ]
        self.assertGreaterEqual(
            len(rejected), 1, f"a delta was rejected for its baseline: {verdicts}"
        )

    def _assert_preserved(self, page, base: int, revision: int, excluded) -> None:
        """Assert every panel the delta did not name kept its committed identity."""
        comparison = page.evaluate(_COMPARE_RECORDS, [base, revision])
        self.assertIsNotNone(comparison, f"no traced commit pair for {base}->{revision}")
        self.assertEqual(comparison["added"], [])
        self.assertEqual(comparison["removed"], [])
        for name, preserved in comparison["preserved"].items():
            if name in excluded:
                self.assertFalse(
                    preserved, f"the changed panel {name!r} kept a stale identity"
                )
            else:
                self.assertTrue(
                    preserved, f"the untouched panel {name!r} was replaced"
                )

    def _assert_checkpoint(self, frames: list[dict], mark: int, *, revision=None) -> tuple:
        """Assert one complete checkpoint and no delta at or below it.

        A settlement publishes exactly one fresh complete snapshot and no
        intermediate delta for the same commit. Later asynchronous
        publications are excluded by their own revision, never by a fixed
        frame count.
        """
        window = _presentation(frames, mark)
        snapshots = [frame for frame in window if frame["name"] == SNAPSHOT]
        self.assertEqual(
            len(snapshots), 1, "a settlement publishes exactly one complete checkpoint"
        )
        checkpoint = snapshots[0]
        committed = _revision_of(checkpoint)
        self.assertIsNotNone(committed)
        if revision is not None:
            self.assertEqual(committed, revision)
        # The settlement's own publication is replaced by this checkpoint:
        # nothing may carry a delta *at* the checkpoint revision. Deltas at
        # earlier revisions are the same flow's ordinary steps (a confirmation
        # request, for one) and are identified by their own revisions.
        competing = [
            frame
            for frame in window
            if frame["name"] == UPDATE and _revision_of(frame) == committed
        ]
        self.assertEqual(
            competing, [], "the checkpoint replaced that revision's delta"
        )
        return checkpoint, committed

    def _committed_epoch(self, page) -> str:
        # The view exposes the live epoch as ``epoch``; the committed record
        # (read by the in-page trace) names the same value ``activeEpoch``.
        return store_state(page)["epoch"]

    # -- 1. graphical and text checkpoint sequence --------------------------

    @covers_requirement(
        "webclient-incremental-sync-verification::"
        "changed-synchronization-paths-have-actual-browser-functional-acceptance"
    )
    @covers_requirement(
        "webclient-incremental-publication::"
        "unknown-scope-recomputes-all-eager-panels-without-full-retransmission"
    )
    @covers_requirement(
        "webclient-settlement-alignment::"
        "every-completed-combat-termination-is-a-fresh-checkpoint"
    )
    @covers_requirement(
        "webclient-publication-settlements::"
        "every-watcher-receives-one-final-checkpoint-publication-per-committed-group"
    )
    @covers_requirement(
        "webclient-immutable-presentation::"
        "ordinary-committed-notifications-reuse-immutable-unchanged-payloads"
    )
    def test_graphical_and_text_checkpoint_sequence(self):
        """Committed gameplay publishes only its changes; each settlement aligns once."""
        page, frames = self._open()
        eager = self._eager_panels(page)
        wait_for_presentation_settled(page)
        base = store_state(page)["revision"]
        epoch = self._committed_epoch(page)

        # -- ordinary nonterminal combat action -----------------------------
        mark = len(frames)
        self._engage(page)
        wait_for_presentation_settled(page)
        engaged = store_state(page)["revision"]
        self.assertGreater(engaged, base)
        delta = self._assert_delta(page, frames, mark, base, engaged)
        self.assertEqual(delta["mode"], "combat")
        self.assertIn("context_actions", delta["panels"])
        self._assert_preserved(page, base, engaged, set(delta["panels"]))
        self.assertEqual(
            [frame for frame in _presentation(frames, mark) if frame["name"] == SNAPSHOT],
            [],
            "entering combat is incremental, never a checkpoint",
        )

        mark = len(frames)
        base = engaged
        self._submit_basic_attack(page)
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("context_actions") or {})
            .get("session", {})
            .get("round")
            == 1
            and (s.get("dispatch") or {}).get("inFlight") is None,
            timeout=60000,
        )
        wait_for_presentation_settled(page)
        resolved = store_state(page)["revision"]
        self.assertGreater(resolved, base)
        delta = self._assert_delta(page, frames, mark, base, resolved)
        self.assertEqual(delta["mode"], "combat")
        self._assert_preserved(page, base, resolved, set(delta["panels"]))
        self.assertEqual(
            len(_results(frames, mark, resolved)),
            1,
            "the resolved round's result names the delta revision",
        )
        # The round is ordinary, so the session survives it: the remaining foe
        # is still engaged and the dock still owns the combat root.
        self.assertEqual(store_state(page)["mode"], "combat")
        self.assertTrue(
            [p for p in self._combat_panel(page)["participants"] if p["team"] == "foes"]
        )

        # -- terminal combat settlement: exactly one complete checkpoint ----
        mark = len(frames)
        base = resolved
        self._surrender(page)
        wait_for_store_state(
            page,
            lambda s: s.get("mode") == "exploration"
            and ((s.get("panels") or {}).get("context_actions") or {}).get(
                "available"
            )
            is True
            and (s.get("dispatch") or {}).get("inFlight") is None,
            timeout=60000,
        )
        wait_for_presentation_settled(page)
        settled = store_state(page)["revision"]
        self.assertGreater(settled, base)
        # The confirming action's own result names the revision its
        # presentation committed, so it identifies the completing publication
        # independently of any later asynchronous push.
        confirming = _results(frames, mark)
        self.assertTrue(confirming, "the settlement published no action result")
        checkpoint_revision = confirming[-1]["args"][0]["presentation_revision"]
        self.assertGreater(checkpoint_revision, base)
        checkpoint_frame, _revision = self._assert_checkpoint(
            frames, mark, revision=checkpoint_revision
        )
        checkpoint = checkpoint_frame["args"][0]
        self.assertEqual(checkpoint["presentation_epoch"], epoch)
        self.assertEqual(
            set(checkpoint["panels"]), eager, "the checkpoint carries every eager panel"
        )
        self.assertGreater(
            len(checkpoint["panels"]), len(delta["panels"]), "the checkpoint is complete"
        )
        self.assertLess(
            frames.index(checkpoint_frame),
            frames.index(confirming[-1]),
            "the checkpoint is sent before the result that names it",
        )
        self.assertGreaterEqual(settled, checkpoint_revision)
        narrative = narrative_log_text(page)
        self.assertTrue(narrative.strip(), "the command produced narrative output")

        # -- same-area graphical move: delta only, exact base ---------------
        mark = len(frames)
        base = settled
        activate_first_compass_exit(page)
        wait_for_store_state(page, lambda s: s["revision"] > base, timeout=60000)
        wait_for_presentation_settled(page)
        moved = store_state(page)["revision"]
        delta = self._assert_delta(page, frames, mark, base, moved)
        self.assertEqual(delta["mode"], "exploration")
        for name in _MOVEMENT_FROZEN_PANELS:
            self.assertNotIn(
                name, delta["panels"], f"a same-area move must not retransmit {name!r}"
            )
        self.assertIn("local_map", delta["panels"])
        self._assert_preserved(page, base, moved, set(delta["panels"]))

        # -- read action: incremental only, never a checkpoint --------------
        # A read command may refresh a derived panel; what it must never do is
        # cost a complete checkpoint or fragment. The unchanged-publication
        # skip is proven through the coordinator itself below.
        narrative = narrative_log_text(page)
        mark = len(frames)
        self._send_text(page, "look")
        wait_for_store_state(
            page,
            lambda s: len(narrative_log_text(page)) > len(narrative),
            timeout=30000,
        )
        wait_for_presentation_settled(page)
        quiet = store_state(page)["revision"]
        read_frames = _presentation(frames, mark)
        self.assertEqual(
            {frame["name"] for frame in read_frames},
            {UPDATE},
            f"a read action publishes only deltas, observed {read_frames}",
        )
        chain = moved
        for frame in read_frames:
            envelope = frame["args"][0]
            self.assertEqual(
                envelope["base_revision"], chain, "each read delta keeps the exact base"
            )
            chain = envelope["revision"]
        self.assertEqual(chain, quiet, "the last read delta is the committed revision")

        # -- authoritative different-map boundary through text --------------
        mark = len(frames)
        base = quiet
        before_panels = set(store_state(page)["panels"])
        self._send_text(page, f"teleport {xyz_arg(second_map_xyz())}")
        wait_for_store_state(page, lambda s: s["revision"] > base, timeout=90000)
        wait_for_presentation_settled(page)
        crossed = store_state(page)["revision"]
        self.assertGreater(crossed, base)
        crossing_frame, crossing_revision = self._assert_checkpoint(frames, mark)
        self.assertGreater(crossing_revision, base)
        self.assertLessEqual(crossing_revision, crossed)
        self.assertEqual(crossing_frame["args"][0]["presentation_epoch"], epoch)
        self.assertEqual(
            set(crossing_frame["args"][0]["panels"]),
            eager,
            "the boundary checkpoint carries every eager panel",
        )
        self.assertEqual(set(store_state(page)["panels"]), eager)

        # -- metadata-only skip control through the real coordinator --------
        match = self._fixture(page, "nochange")
        self.assertEqual(match[3], "unchanged", f"the identical publication was not skipped: {match}")
        self.assertEqual(match[4], "0", "a skipped publication sends no frame")
        # The coordinator's own published revision is unchanged by the
        # identical candidate: the skip consumed no revision and sent nothing.
        before, after = (int(part) for part in match[7].split(":"))
        self.assertEqual(
            before, after, "an identical candidate consumes no revision"
        )
        self.assertEqual(int(match[2]), before)

    # -- 2. oversized snapshot and delta ------------------------------------

    @covers_requirement(
        "webclient-incremental-sync-verification::"
        "changed-synchronization-paths-have-actual-browser-functional-acceptance"
    )
    @covers_requirement(
        "webclient-publication-assembly::"
        "general-assembly-adopts-one-complete-validated-publication"
    )
    @covers_requirement(
        "webclient-publication-assembly::assembly-lifetime-and-teardown-are-explicit"
    )
    def test_oversized_snapshot_and_delta_adopt_once(self):
        """Both oversized kinds cross the real socket as bounded parts, once."""
        page, frames = self._open()
        # The gate is installed without arming a fault: it records the
        # reducer's own verdict per part frame, which is what proves the
        # pending parts staged nothing.
        self._install_gate(page)
        eager = self._eager_panels(page)

        match = self._fixture(page, "snapshot")
        revision = int(match[2])
        payload_bytes = int(match[5])
        digest = match[6]
        self.assertEqual(match[3], "snapshot")
        self.assertLessEqual(payload_bytes, FRAME_CEILING)
        wait_for_store_state(page, lambda s: s["revision"] >= revision, timeout=90000)
        wait_for_presentation_settled(page)
        self._assert_part_transfer(
            page,
            frames,
            mark=0,
            revision=revision,
            kind="snapshot",
            base=None,
            eager=eager,
        )
        self._assert_adopted_panel(page, revision, "lore_codex", payload_bytes, digest)

        snapshot_revision = revision
        mark = len(frames)
        match = self._fixture(page, "delta")
        revision = int(match[2])
        payload_bytes = int(match[5])
        digest = match[6]
        delta_base = int(match[7])
        self.assertEqual(match[3], "delta")
        self.assertGreaterEqual(
            delta_base, snapshot_revision, "the delta builds on the committed snapshot"
        )
        self.assertLessEqual(
            payload_bytes, FRAME_CEILING, "the panel itself stays inside its own cap"
        )
        wait_for_store_state(page, lambda s: s["revision"] >= revision, timeout=90000)
        wait_for_presentation_settled(page)
        self._assert_part_transfer(
            page,
            frames,
            mark=mark,
            revision=revision,
            kind="delta",
            base=delta_base,
            eager=eager,
        )
        self._assert_adopted_panel(page, revision, "lore_codex", payload_bytes, digest)
        state = store_state(page)
        self.assertGreaterEqual(state["revision"], revision)
        self.assertEqual(state["recovery"]["status"], "idle")
        self.assertIsNot(state.get("mutationsLocked"), True)

    def _assert_part_transfer(
        self,
        page,
        frames: list[dict],
        *,
        mark: int,
        revision: int,
        kind: str,
        base: int | None,
        eager: set,
    ) -> None:
        """Assert one logical publication crossed as one bounded part transfer."""
        at_revision = _presentation(frames, mark, revision)
        kinds = [frame["name"] for frame in at_revision]
        self.assertNotIn(
            SNAPSHOT if kind == "snapshot" else UPDATE,
            kinds,
            "an over-ceiling publication never travels intact",
        )
        self.assertEqual(set(kinds), {PART}, f"expected only parts, got {kinds}")
        parts = [frame["args"][0] for frame in at_revision]
        total = parts[0]["total_bytes"]
        count = parts[0]["part_count"]
        self.assertGreater(
            total, FRAME_CEILING, "the logical document exceeds the intact allowance"
        )
        self.assertEqual(count, -(-total // PART_RAW_BYTES))
        self.assertEqual([part["part_index"] for part in parts], list(range(count)))
        self.assertEqual(len({part["transfer_id"] for part in parts}), 1)
        self.assertEqual({part["publication_kind"] for part in parts}, {kind})
        self.assertEqual({part["revision"] for part in parts}, {revision})
        self.assertEqual({part["total_bytes"] for part in parts}, {total})
        if kind == "delta":
            self.assertEqual({part["base_revision"] for part in parts}, {base})
        # Every part before the last is staged only: the reducer rejects it as
        # pending, adopts nothing and notifies nobody until the final part
        # produces the one complete commit.
        verdicts = [
            entry
            for entry in page.evaluate("() => window.__syncGateState().received")
            if entry[0] == PART and entry[1] == revision
        ]
        self.assertEqual(
            len(verdicts), len(parts), "every part frame reached the reducer"
        )
        for _name, _seen, accepted, _reason, pending in verdicts[:-1]:
            self.assertIs(accepted, False, "a pending part is never adopted")
            self.assertIs(pending, True, "a non-final part is staged, not committed")
        self.assertIs(verdicts[-1][2], True, "the final part commits")
        self.assertIsNot(verdicts[-1][4], True, "the final part is not pending")
        for frame, part in zip(at_revision, parts):
            self.assertLessEqual(
                len(frame["text"].encode("utf-8")),
                FRAME_CEILING,
                "every part frame stays inside the generic frame ceiling",
            )
            self.assertLessEqual(len(part["chunks"]), 16)
        self.assertEqual(
            self._commits(page, revision), 1,
            "the transfer adopts exactly once",
        )
        committed_names = page.evaluate(
            """([revision]) => {
              const records = window.__syncTrace.records.filter(
                (record) => record.revision === revision);
              if (records.length === 0) { return null; }
              return Object.keys(records[records.length - 1].panels || {}).sort();
            }""",
            [revision],
        )
        self.assertEqual(
            set(committed_names), eager, "the adopted state carries every eager panel"
        )

    def _assert_adopted_panel(
        self, page, revision: int, name: str, payload_bytes: int, digest: str
    ) -> None:
        """Assert the commit at ``revision`` adopted exactly the fixture payload.

        The committed record at that revision is read (not the latest view):
        a later legitimate publication may re-render the panel, so the
        adoption is identified by its own revision.
        """
        adopted = page.evaluate(
            """async ([revision, name]) => {
              const records = window.__syncTrace.records.filter(
                (record) => record.revision === revision);
              if (records.length === 0) { return null; }
              const panel = records[records.length - 1].panels[name];
              if (!panel) { return null; }
              const canonical = (value) => {
                if (value === null || typeof value !== 'object') { return JSON.stringify(value); }
                if (Array.isArray(value)) { return '[' + value.map(canonical).join(',') + ']'; }
                return '{' + Object.keys(value).sort()
                  .map((key) => JSON.stringify(key) + ':' + canonical(value[key]))
                  .join(',') + '}';
              };
              const bytes = new TextEncoder().encode(canonical(panel));
              const hash = await crypto.subtle.digest('SHA-256', bytes);
              return {
                bytes: bytes.length,
                sha256: Array.from(new Uint8Array(hash))
                  .map((b) => b.toString(16).padStart(2, '0')).join(''),
              };
            }""",
            [revision, name],
        )
        self.assertIsNotNone(adopted, f"no commit at {revision} carried the {name} panel")
        self.assertEqual(adopted["bytes"], payload_bytes)
        self.assertEqual(adopted["sha256"], digest)

    # -- 3. one missing publication ----------------------------------------

    @covers_requirement(
        "webclient-sync-recovery::recovery-coalesces-failures-and-remains-bounded"
    )
    @covers_requirement(
        "webclient-incremental-sync-verification::"
        "changed-synchronization-paths-have-actual-browser-functional-acceptance"
    )
    @covers_requirement(
        "webclient-sync-recovery::"
        "action-results-cannot-claim-synchronization-before-adoption"
    )
    @covers_requirement(
        "webclient-settlement-alignment::"
        "completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_missing_publication_recovers_complete_baseline(self):
        """One withheld publication costs exactly one bounded repair."""
        page, frames = self._open()
        self._install_gate(page)
        eager = self._eager_panels(page)
        wait_for_presentation_settled(page)
        base = store_state(page)["revision"]
        before = store_state(page)
        sent_mark = len(outbound_messages(page))
        trace_mark = self._trace_mark(page)

        # Withhold exactly one genuine publication before the reducer sees it.
        # The next real publication then arrives with a baseline this client
        # never committed, which is the missed-publication condition; the
        # locked window is read from the subscriber's own records, so no frame
        # is delayed and the live sequence keeps its ordering.
        self._arm_gate(page, dropNextDelta=True)
        match = self._fixture(page, "delta")
        withheld = int(match[2])
        page.wait_for_function(
            "() => window.__syncGateState().dropped.length === 1", timeout=60000
        )
        withheld_revisions = page.evaluate(
            "() => window.__syncGateState().dropped"
        )
        self.assertEqual(
            len(withheld_revisions), 1, "exactly one genuine publication was withheld"
        )
        self.assertGreaterEqual(
            withheld_revisions[0],
            withheld,
            "the withheld publication belongs to the fault window",
        )
        self.assertGreater(withheld, base)
        # The episode is transient by design (the repair lands immediately), so
        # the locked window and the single request are read from the
        # subscriber's recorded transitions and the outbound recorder.
        wait_for_store_state(
            page,
            lambda s: s["revision"] > base
            and s.get("recovery", {}).get("status") == "idle"
            and _unlocked(s),
            timeout=60000,
        )
        self._assert_locked_episode(page, base, eager, trace_mark)
        self._assert_base_mismatch(page, trace_mark)
        self.assertEqual(
            self._syncs_since(page, sent_mark),
            1,
            "exactly one synchronization request leaves the client",
        )
        wait_for_presentation_settled(page)
        repaired = store_state(page)
        self.assertEqual(repaired["recovery"]["status"], "idle")
        self.assertGreater(repaired["revision"], base)
        self.assertEqual(set(repaired["panels"]), set(before["panels"]))
        self.assertEqual(
            self._syncs_since(page, sent_mark),
            1,
            "the repair never repeats",
        )
        self.assertEqual(
            self._actions_since(page, sent_mark),
            0,
            "no mutation is replayed for the episode",
        )
        self.assertEqual(set(repaired["panels"]), eager, "the repair is complete")

        # A test-scope publication changes a canonical field but omits its
        # owning panel. The omission is proven at the receipt's own revision,
        # and the attributing repair is the *next complete checkpoint*: its
        # own committed record must carry the mutated value, so the repair can
        # never be credited to the omitting delta.
        stale_hp = _hp_trait(store_state(page))
        mark = len(frames)
        match = self._fixture(page, "omit")
        mutated_hp = int(match[7])
        omit_revision = int(match[2])
        self.assertNotEqual(mutated_hp, stale_hp)
        wait_for_store_state(
            page, lambda s: s["revision"] >= omit_revision, timeout=90000
        )
        wait_for_presentation_settled(page)
        published = _presentation(frames, mark, omit_revision)
        self.assertTrue(published, "the omission publication produced no frame")
        self.assertNotIn(
            "character",
            published[0]["args"][0]["panels"],
            "the publication deliberately omitted the changed panel",
        )
        self.assertEqual(
            _hp_at(page, omit_revision),
            stale_hp,
            "the committed panel stayed stale at the omitting revision: "
            f"gate={page.evaluate('() => window.__syncGateState()')}",
        )
        # The player's explicit synchronize is the next real semantic
        # checkpoint. It is verified independently: its own committed record
        # must carry the canonical value and the registry's whole eager set.
        page.evaluate("() => Elosern.actions.client.sync()")
        wait_for_store_state(page, lambda s: s["revision"] > omit_revision, timeout=90000)
        wait_for_presentation_settled(page)
        checkpoints = [
            frame
            for frame in _presentation(frames, mark)
            if frame["name"] == SNAPSHOT and (_revision_of(frame) or 0) > omit_revision
        ]
        self.assertTrue(checkpoints, "no complete checkpoint followed the omission")
        restoring = checkpoints[0]
        restoring_revision = _revision_of(restoring)
        # The first publication that re-renders the owning panel after the
        # omission must carry the canonical value: the stale baseline is never
        # reused, whichever real publication restores it.
        rerenders = [
            frame
            for frame in _presentation(frames, mark)
            if (_revision_of(frame) or 0) > omit_revision
            and "character" in (((frame["args"] or [{}])[0] or {}).get("panels") or {})
        ]
        self.assertTrue(rerenders, "the omitted panel was never re-rendered")
        self.assertEqual(
            _hp_at(page, _revision_of(rerenders[0])),
            mutated_hp,
            "the next fresh render of the panel carries the canonical value",
        )
        self.assertEqual(
            set(restoring["args"][0]["panels"]),
            eager,
            "the restoring checkpoint is complete",
        )
        wait_for_store_state(
            page, lambda s: s["revision"] >= restoring_revision, timeout=30000
        )
        self.assertEqual(
            _hp_at(page, restoring_revision),
            mutated_hp,
            "the checkpoint's own committed record restored the omitted field",
        )
        self.assertEqual(store_state(page)["recovery"]["status"], "idle")

    # -- 4. failed repair, explicit recovery and local state ----------------

    @covers_requirement(
        "webclient-sync-recovery::recovery-coalesces-failures-and-remains-bounded"
    )
    @covers_requirement(
        "webclient-incremental-sync-verification::"
        "changed-synchronization-paths-have-actual-browser-functional-acceptance"
    )
    @covers_requirement(
        "webclient-immutable-presentation::"
        "complete-alignment-preserves-valid-local-interaction-state"
    )
    @covers_requirement(
        "webclient-immutable-presentation::explicit-detached-snapshots-retain-isolation"
    )
    def test_failed_recovery_and_alignment_preserve_local_state(self):
        """A failed repair stays bounded and usable; valid local state survives."""
        page, frames = self._open()
        self._install_gate(page)
        eager = self._eager_panels(page)
        wait_for_presentation_settled(page)
        base = store_state(page)["revision"]
        before = store_state(page)
        sent_mark = len(outbound_messages(page))
        trace_mark = self._trace_mark(page)

        # Withhold one genuine publication, then corrupt the single automatic
        # repair: the episode becomes terminal instead of requesting again.
        self._arm_gate(page, dropNextDelta=True, corruptSnapshotAbove=base)
        self._fixture(page, "delta")
        page.wait_for_function(
            "() => window.__syncGateState().dropped.length === 1", timeout=60000
        )
        wait_for_store_state(
            page, lambda s: s.get("recovery", {}).get("status") == "failed", timeout=60000
        )
        failed = store_state(page)
        self.assertEqual(failed["recovery"]["status"], "failed")
        self.assertIs(failed["mutationsLocked"], True, "graphical mutations stay locked")
        self.assertEqual(set(failed["panels"]), eager, "nothing is erased")
        episodes = self._assert_locked_episode(page, base, eager, trace_mark)
        self._assert_base_mismatch(page, trace_mark)
        self.assertEqual(
            [entry[1] for entry in episodes].count("failed"),
            1,
            "exactly one transition into the terminal episode",
        )
        locked_revision = failed["revision"]
        self.assertEqual(
            self._syncs_since(page, sent_mark),
            1,
            "the failed repair is never retried automatically",
        )
        page.wait_for_timeout(2000)
        self.assertEqual(
            self._syncs_since(page, sent_mark),
            1,
            "no synchronization loop follows the terminal episode",
        )
        self.assertEqual(
            self._actions_since(page, sent_mark),
            0,
            "no mutation is replayed for the failed episode",
        )
        before_output = self._out_lines(page)
        self._send_text(page, "look")
        page.wait_for_function(
            "(before) => window.__elosernBridge.store.narrative.filter("
            "(line) => line && line.kind === 'out').length > before",
            arg=before_output,
            timeout=30000,
        )
        self.assertGreater(
            self._out_lines(page),
            before_output,
            "the server still answers text while the episode is terminal",
        )
        self.assertEqual(
            store_state(page)["revision"], locked_revision, "text consumes no revision"
        )

        # The player's explicit synchronize spends the one further attempt.
        page.evaluate("() => Elosern.actions.client.sync()")
        wait_for_store_state(page, _unlocked, timeout=90000)
        wait_for_presentation_settled(page)
        recovered = store_state(page)
        self.assertEqual(recovered["recovery"]["status"], "idle")
        self.assertGreater(recovered["revision"], base)
        self.assertEqual(recovered["epoch"], before["epoch"], "same live epoch")
        self.assertEqual(set(recovered["panels"]), eager)

        # -- valid local UI state survives a same-mode checkpoint -----------
        open_command_line(page)
        typed = "尚未送出的指令"
        page.keyboard.type(typed)
        self.assertEqual(page.input_value("#inputfield"), typed)
        page.evaluate(
            "() => window.__elosernBridge.store.openHudDrawer('quest')"
        )
        page.wait_for_selector('[data-testid="quest-drawer"]', timeout=30000)
        focused_tab = page.evaluate(
            """() => {
              const tabs = Array.from(document.querySelectorAll(
                '[data-testid="quest-drawer__top-tabs"] [role="tab"]'));
              const enabled = tabs.find(
                (tab) => tab.getAttribute('aria-disabled') !== 'true');
              if (!enabled) { return null; }
              enabled.focus();
              enabled.click();
              return document.activeElement.getAttribute('data-testid');
            }"""
        )
        self.assertIsNotNone(focused_tab, "the drawer offers no enabled tab")
        self.assertEqual(
            page.evaluate("() => document.activeElement.getAttribute('data-testid')"),
            focused_tab,
            "the drawer item holds focus",
        )
        drawer_handle = page.evaluate_handle(
            "() => document.querySelector('[data-testid=\"hud-drawer\"]')"
        )
        checkpoint_revision = store_state(page)["revision"]
        mark = len(frames)
        page.evaluate("() => Elosern.actions.client.sync()")
        wait_for_store_state(
            page, lambda s: s["revision"] > checkpoint_revision, timeout=90000
        )
        wait_for_presentation_settled(page)
        self.assertEqual(
            [frame["name"] for frame in _presentation(frames, mark)].count(SNAPSHOT), 1
        )
        self.assertTrue(
            page.evaluate(
                "() => document.querySelector('[data-testid=\"hud-drawer\"]') !== null"
            ),
            "the open drawer survives the same-mode checkpoint",
        )
        self.assertTrue(
            page.evaluate(
                "(handle) => handle === document.querySelector('[data-testid=\"hud-drawer\"]')",
                drawer_handle,
            ),
            "the drawer is not remounted",
        )
        self.assertEqual(
            page.evaluate("() => document.activeElement.getAttribute('data-testid')"),
            focused_tab,
            "the focused item keeps focus",
        )
        self.assertEqual(page.input_value("#inputfield"), typed)

        # -- an actual mode change runs the existing teardown --------------
        # The fault window's compass step left the room, so return to the gate
        # (where the seeded monsters are) before engaging.
        self._send_text(page, f"teleport {xyz_arg(first_gate_xyz())}")
        wait_for_store_state(
            page,
            lambda s: s.get("mode") == "exploration"
            and (s.get("dispatch") or {}).get("inFlight") is None,
            timeout=60000,
        )
        wait_for_presentation_settled(page)
        self._engage(page)
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"hud-drawer\"]') === null",
            timeout=30000,
        )
        self.assertIsNone(store_state(page).get("hudDrawer"))

        # -- a subscriber-held committed record cannot be written through ---
        probe = page.evaluate(_PROBE_COMMITTED)
        self.assertTrue(probe["frozen"], "the committed record is frozen")
        self.assertTrue(probe["panelFrozen"], "the committed panel is frozen")
        self.assertTrue(probe["revisionUnchanged"])
        self.assertTrue(probe["panelsUnchanged"], "a write attempt changes nothing")
        self.assertEqual(probe["panelNames"], sorted(store_state(page)["panels"]))

    # -- shared trace helpers ----------------------------------------------

    def _commits(self, page, revision: int) -> int:
        """How many traced commits the store recorded at ``revision``."""
        return page.evaluate(
            "(revision) => window.__syncTrace.records.filter("
            "(record) => record.revision === revision).length",
            revision,
        )

    @staticmethod
    def _syncs_since(page, mark: int) -> int:
        """How many ``ui_sync`` requests left the client after ``mark``."""
        return len(
            [
                name
                for name, _args, _kwargs in outbound_messages(page)[mark:]
                if name == "ui_sync"
            ]
        )

    @staticmethod
    def _actions_since(page, mark: int) -> int:
        """How many mutation requests left the client after ``mark``."""
        return len(
            [
                name
                for name, _args, _kwargs in outbound_messages(page)[mark:]
                if name == "ui_action"
            ]
        )

    def _eager_panels(self, page) -> set:
        """The coordinator's own eager panel set, reported by the fixture."""
        match = self._fixture(page, "eager")
        names = match[7]
        self.assertNotEqual(names, "-", "the fixture reported no eager panel set")
        return set(names.split(","))

    @staticmethod
    def _out_lines(page) -> int:
        """How many server-output narrative lines the log holds.

        Only ``out`` lines count: the client appends the player's own ``in``
        echo synchronously, so a length check could pass without the server
        ever answering.
        """
        return page.evaluate(
            """() => {
              const lines = window.__elosernBridge.store.narrative;
              if (!Array.isArray(lines)) { return 0; }
              return lines.filter((line) => line && line.kind === 'out').length;
            }"""
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
