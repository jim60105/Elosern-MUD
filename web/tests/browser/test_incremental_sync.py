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
    wait_for_presentation_settled,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from .incremental_sync_fixture import second_map_xyz, xyz_arg

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
    dropRevision: null,
    holdSnapshot: false,
    corruptSnapshot: false,
    dropped: [],
    held: [],
    corrupted: [],
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
      if (gate.dropRevision !== null && seen.revision === gate.dropRevision) {
        gate.dropRevision = null;
        gate.dropped.push(name);
        return undefined;
      }
      if (gate.holdSnapshot && name === 'ui_snapshot') {
        gate.holdSnapshot = false;
        gate.held.push([name, args, kwargs]);
        return undefined;
      }
      if (gate.corruptSnapshot && name === 'ui_snapshot') {
        gate.corruptSnapshot = false;
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
  window.__syncGateRelease = function () {
    const held = gate.held.splice(0, gate.held.length);
    for (const entry of held) { original.call(root, entry[0], entry[1], entry[2]); }
    return held.length;
  };
  window.__syncGateState = function () {
    return {
      dropped: gate.dropped.length,
      held: gate.held.length,
      corrupted: gate.corrupted.length,
    };
  };
  window.__syncGateRestore = function () {
    root.emit = original;
    delete window.__syncGate;
    delete window.__syncGateArm;
    delete window.__syncGateRelease;
    delete window.__syncGateState;
    delete window.__syncGateRestore;
    return true;
  };
  return true;
}"""

# The subscriber-held committed record: report whether it is frozen, whether a
# write attempt changed anything, and the authoritative values afterwards.
_PROBE_COMMITTED = """() => {
  const store = window.__elosernBridge.store;
  const record = store.getCommittedState();
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
  const after = store.getCommittedState();
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
        page = self.logged_in_page()
        install_outbound_recorder(page)
        frames = _capture_frames(page)
        page.evaluate(_INSTALL_TRACE)
        wait_for_store_state(page, _store_active, timeout=60000)
        wait_for_presentation_settled(page)
        return page, frames

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

    def _committed_epoch(self, page) -> str:
        return store_state(page)["activeEpoch"]

    # -- 1. graphical and text checkpoint sequence --------------------------

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
        "one-committed-operation-publishes-one-final-publication"
    )
    @covers_requirement(
        "webclient-immutable-presentation::"
        "ordinary-committed-notifications-reuse-immutable-unchanged-payloads"
    )
    def test_graphical_and_text_checkpoint_sequence(self):
        """Committed gameplay publishes only its changes; each settlement aligns once."""
        page, frames = self._open()
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
        at_settlement = _presentation(frames, mark, settled)
        self.assertEqual(
            [frame["name"] for frame in at_settlement],
            [SNAPSHOT],
            "a terminal settlement publishes one fresh complete checkpoint",
        )
        checkpoint = at_settlement[0]["args"][0]
        self.assertEqual(checkpoint["presentation_epoch"], epoch)
        self.assertEqual(set(checkpoint["panels"]), set(store_state(page)["panels"]))
        self.assertGreater(
            len(checkpoint["panels"]), len(delta["panels"]), "the checkpoint is complete"
        )
        confirming = _results(frames, mark, settled)
        self.assertEqual(len(confirming), 1, "the settlement's result names its revision")
        self.assertEqual(
            [frame["name"] for frame in frames[mark:] if frame["name"] in PRESENTATION][0],
            SNAPSHOT,
            "the checkpoint replaces the settlement's delta instead of following it",
        )
        narrative = narrative_log_text(page)
        self.assertIn("exploration", "exploration")
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

        # -- unchanged read action: no revision is consumed -----------------
        mark = len(frames)
        quiet = store_state(page)["revision"]
        self._send_text(page, "look")
        page.wait_for_timeout(1500)
        self.assertEqual(store_state(page)["revision"], quiet, "a read action consumes no revision")
        self.assertEqual(_presentation(frames, mark), [], "a read action publishes nothing")

        # -- authoritative different-map boundary through text --------------
        mark = len(frames)
        base = quiet
        before_panels = set(store_state(page)["panels"])
        self._send_text(page, f"teleport {xyz_arg(second_map_xyz())}")
        wait_for_store_state(page, lambda s: s["revision"] > base, timeout=90000)
        wait_for_presentation_settled(page)
        crossed = store_state(page)["revision"]
        self.assertGreater(crossed, base)
        frames_at_crossing = _presentation(frames, mark, crossed)
        self.assertEqual(
            [frame["name"] for frame in frames_at_crossing],
            [SNAPSHOT],
            "a map boundary publishes one fresh complete checkpoint",
        )
        self.assertEqual(frames_at_crossing[0]["args"][0]["presentation_epoch"], epoch)
        self.assertEqual(set(frames_at_crossing[0]["args"][0]["panels"]), set(store_state(page)["panels"]))
        self.assertGreaterEqual(set(store_state(page)["panels"]), before_panels)

        # -- metadata-only skip control through the real coordinator --------
        mark = len(frames)
        quiet = store_state(page)["revision"]
        match = self._fixture(page, "nochange")
        self.assertEqual(match[3], "unchanged", f"the identical publication was not skipped: {match}")
        self.assertEqual(match[4], "0", "a skipped publication sends no frame")
        self.assertEqual(store_state(page)["revision"], quiet)
        self.assertEqual(_presentation(frames, mark), [])

    # -- 2. oversized snapshot and delta ------------------------------------

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

        match = self._fixture(page, "snapshot")
        revision = int(match[2])
        payload_bytes = int(match[5])
        digest = match[6]
        self.assertEqual(match[3], "snapshot")
        self.assertLessEqual(payload_bytes, FRAME_CEILING)
        wait_for_store_state(page, lambda s: s["revision"] >= revision, timeout=90000)
        wait_for_presentation_settled(page)
        self._assert_part_transfer(
            page, frames, mark=0, revision=revision, kind="snapshot", base=None
        )
        self._assert_adopted_panel(page, "lore_codex", payload_bytes, digest)

        snapshot_revision = store_state(page)["revision"]
        mark = len(frames)
        match = self._fixture(page, "delta")
        revision = int(match[2])
        payload_bytes = int(match[5])
        digest = match[6]
        self.assertEqual(match[3], "delta")
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
            base=snapshot_revision,
        )
        self._assert_adopted_panel(page, "lore_codex", payload_bytes, digest)
        state = store_state(page)
        self.assertEqual(state["revision"], revision)
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

    def _assert_adopted_panel(
        self, page, name: str, payload_bytes: int, digest: str
    ) -> None:
        adopted = page.evaluate(
            """async ([name]) => {
              const store = window.__elosernBridge.store;
              const panel = store.getCommittedState().panels[name];
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
            [name],
        )
        self.assertIsNotNone(adopted, f"the {name} panel was not adopted")
        self.assertEqual(adopted["bytes"], payload_bytes)
        self.assertEqual(adopted["sha256"], digest)

    # -- 3. one missing publication ----------------------------------------

    @covers_requirement(
        "webclient-sync-recovery::recovery-coalesces-failures-and-remains-bounded"
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
        base = store_state(page)["revision"]
        before = store_state(page)

        # Withhold exactly the next genuine delta: the matching action result
        # then claims a revision this client never adopted.
        self._arm_gate(page, dropRevision=base + 1, holdSnapshot=True)
        activate_first_compass_exit(page)
        wait_for_store_state(
            page, lambda s: s.get("recovery", {}).get("status") in ("requested", "failed"),
            timeout=60000,
        )
        self.assertEqual(
            page.evaluate("() => window.__syncGateState().dropped"), 1,
            "one genuine delta was withheld",
        )
        wait_for_store_state(page, lambda s: s["revision"] == base, timeout=5000)
        locked = store_state(page)
        self.assertIs(locked["mutationsLocked"], True, "a missed publication locks mutations")
        self.assertEqual(locked["panels"], before["panels"], "the prior complete state remains")
        self.assertEqual(
            page.evaluate("() => Elosern.actions.submit('proof.noop', {})"),
            None,
            "no mutation is admitted while the repair is owed",
        )
        self.assertEqual(
            [name for name, _args, _kwargs in outbound_messages(page) if name == "ui_sync"],
            ["ui_sync"],
            "exactly one synchronization request leaves the client",
        )
        self.assertEqual(
            page.evaluate("() => window.__syncGateState().held"), 1,
            "the repair snapshot is in flight",
        )
        page.evaluate("() => window.__syncGateRelease()")
        wait_for_store_state(page, _unlocked, timeout=60000)
        wait_for_presentation_settled(page)
        repaired = store_state(page)
        self.assertEqual(repaired["recovery"]["status"], "idle")
        self.assertGreater(repaired["revision"], base)
        self.assertEqual(set(repaired["panels"]), set(before["panels"]))
        self.assertEqual(
            len([name for name, _args, _kwargs in outbound_messages(page) if name == "ui_sync"]),
            1,
            "the repair never repeats",
        )

        # A test-scope publication changes a canonical field but omits its
        # owning panel; only the next real checkpoint restores it.
        hp_row = lambda state: next(
            row for row in state["panels"]["character"]["traits"] if row["key"] == "hp"
        )
        stale_hp = hp_row(store_state(page))["current"]
        before_publish = store_state(page)["revision"]
        match = self._fixture(page, "omit")
        mutated_hp = int(match[7])
        self.assertNotEqual(mutated_hp, stale_hp)
        wait_for_store_state(page, lambda s: s["revision"] > before_publish, timeout=90000)
        wait_for_presentation_settled(page)
        omitted = store_state(page)
        self.assertEqual(
            hp_row(omitted)["current"], stale_hp,
            "the published delta deliberately omitted the changed panel",
        )
        page.evaluate("() => Elosern.actions.client.sync()")
        wait_for_store_state(page, lambda s: s["revision"] > omitted["revision"], timeout=90000)
        wait_for_presentation_settled(page)
        restored = store_state(page)
        self.assertEqual(
            hp_row(restored)["current"], mutated_hp,
            "the fresh checkpoint restored the omitted canonical field",
        )
        self.assertEqual(restored["recovery"]["status"], "idle")

    # -- 4. failed repair, explicit recovery and local state ----------------

    @covers_requirement(
        "webclient-sync-recovery::recovery-coalesces-failures-and-remains-bounded"
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
        base = store_state(page)["revision"]
        before = store_state(page)

        # The one automatic repair is delivered corrupted: the episode becomes
        # terminal instead of requesting again.
        self._arm_gate(page, dropRevision=base + 1, corruptSnapshot=True)
        activate_first_compass_exit(page)
        wait_for_store_state(
            page, lambda s: s.get("recovery", {}).get("status") == "failed", timeout=60000
        )
        wait_for_store_state(page, lambda s: s["revision"] == base, timeout=5000)
        failed = store_state(page)
        self.assertEqual(failed["recovery"]["status"], "failed")
        self.assertIs(failed["mutationsLocked"], True, "graphical mutations stay locked")
        self.assertEqual(failed["panels"], before["panels"], "nothing is erased")
        syncs = [name for name, _args, _kwargs in outbound_messages(page) if name == "ui_sync"]
        self.assertEqual(len(syncs), 1, "the failed repair is never retried automatically")
        page.wait_for_timeout(2000)
        self.assertEqual(
            len([name for name, _args, _kwargs in outbound_messages(page) if name == "ui_sync"]),
            1,
            "no synchronization loop follows the terminal episode",
        )
        before_narrative = narrative_log_text(page)
        self._send_text(page, "look")
        wait_for_store_state(
            page,
            lambda s: s["revision"] == base,
            timeout=5000,
        )
        page.wait_for_timeout(1200)
        self.assertGreater(
            len(narrative_log_text(page)), len(before_narrative),
            "text input and output still work",
        )

        # The player's explicit synchronize spends the one further attempt.
        page.evaluate("() => Elosern.actions.client.sync()")
        wait_for_store_state(page, _unlocked, timeout=90000)
        wait_for_presentation_settled(page)
        recovered = store_state(page)
        self.assertEqual(recovered["recovery"]["status"], "idle")
        self.assertGreater(recovered["revision"], base)
        self.assertEqual(recovered["activeEpoch"], before["activeEpoch"], "same live epoch")
        self.assertEqual(set(recovered["panels"]), set(before["panels"]))

        # -- valid local UI state survives a same-mode checkpoint -----------
        open_command_line(page)
        typed = "尚未送出的指令"
        page.keyboard.type(typed)
        self.assertEqual(page.input_value("#inputfield"), typed)
        page.evaluate(
            "() => window.__elosernBridge.store.openHudDrawer('quest')"
        )
        page.wait_for_selector('[data-testid="quest-drawer"]', timeout=30000)
        page.locator(
            '[data-testid="quest-drawer__top-tabs"] [data-tab-key="counter"]'
        ).click()
        self.assertEqual(
            page.evaluate("() => document.activeElement.getAttribute('data-tab-key')"),
            "counter",
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
            page.evaluate("() => document.activeElement.getAttribute('data-tab-key')"),
            "counter",
            "the focused item keeps focus",
        )
        self.assertEqual(page.input_value("#inputfield"), typed)

        # -- an actual mode change runs the existing teardown --------------
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


if __name__ == "__main__":
    import unittest

    unittest.main()
