"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): wait/rest clock journeys with safety rejections, stale/tampered rejections, the no-take/drop rule, and non-success narrative delivery.
"""

from __future__ import annotations

import json
from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    fixture_home_node_id,
    install_outbound_recorder,
    sent_action_count,
    outbound_messages,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


def _connected_active(state: dict) -> bool:
    """Gate on the client being connected and in the active presentation phase."""
    return bool(state.get("connected")) and state.get("phase") == "active"


class ExplorationBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with the exploration fixture."""
    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_EXPLORATION"] = "1"
        # Boot mode: SHIPPED catalogs (explicit override of the harness
        # synthetic default, per the creation/action-feedback precedent).
        # These journeys assert shipped fixture identity end to end and were
        # never migrated to kit seams.
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"

        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def _live_exploration_panel(self, page):
        # The panels mapping can be observed mid-snapshot-adoption without the
        # exploration key; callers poll, so a missing panel reads as None.
        return store_state(page)["panels"].get("exploration")

    def _wait_exploration_available(self, page, timeout=30000):
        def _exploration_available(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("exploration") or {}
            return panel.get("available") is True

        wait_for_store_state(page, _exploration_available, timeout=timeout)

    def _wait_panel(self, page, name, predicate, timeout=30000):
        def _panel_ready(state: dict) -> bool:
            panel = (state.get("panels") or {}).get(name)
            return panel is not None and predicate(panel)

        wait_for_store_state(page, _panel_ready, timeout=timeout)

    def _reset_root(self, page):
        focus_action_dock(page)
        page.evaluate("window.__elosernBridge.store.resetFramesToRoot()")
        page.wait_for_timeout(60)

    def _open_root(self, page, index):
        self._reset_root(page)
        # The exploration root is a single seven-column row (mockup grid), so
        # horizontal arrows move across it; submenus are 2-column grids.
        for _ in range(index):
            _press(page, "ArrowRight")
        _press(page, "Enter")

    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_unsafe_skip_rejects_before_any_clock_advance(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # At the South Gate a living goblin makes every skip unsafe; the
        # daypart boundary rejects before any clock advance.
        time_before = store_state(page)["serverTime"]
        # The desktop redesign re-homed Wait to the dock root's fourth tab
        # (webclient-exploration-menu: the capability-driven root
        # [move, look, interact, wait, suggestions]) and re-cut the wait
        # frame into the three-operation row [等待直到黎明, 睡眠至完全恢復,
        # 休息 N 小時] — the direct daypart wait dispatches from the first
        # column, and the safety gate rejects it while the goblin stands at
        # the gate (the daypart value is irrelevant to the rejection).
        self._open_root(page, 3)  # Wait/休息
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("code") == "unsafe_skip",
            timeout=20000,
        )
        self.assertEqual(store_state(page)["lastActionResult"]["code"], "unsafe_skip")
        self.assertEqual(sent_action_count(page, "explore.wait"), 1)
        self.assertEqual(store_state(page)["serverTime"], time_before)

        # The bounded custom-duration form is parsed server-side and rejected
        # by the same safety gate.
        # 休息 N 小時 is the third card of the shipped row (stores/elosern.js
        # resolves exploration.wait with gridCols: 3): two ArrowRight steps
        # reach it.
        self._open_root(page, 3)  # Wait/休息
        _press(page, "ArrowRight")  # 睡眠至完全恢復
        _press(page, "ArrowRight")  # 休息 N 小時
        _press(page, "Enter")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": ".exploration-rest-form input[type='number']",
                "predicate": (
                    "() => { const f = document.querySelector("
                    "'.exploration-rest-form input[type=\\'number\\']');"
                    "return !!f && document.activeElement === f; }"
                ),
                "description": "rest form's duration input focused",
            },
        )
        # The redesigned form's unit is HOURS (RestForm.vue: raw ref "1",
        # submit emits bounded seconds) — the default one-hour value is the
        # custom 3600s the old seconds-form typed; keep the form's default
        # and confirm it.
        page.keyboard.press("Enter")
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("code") == "unsafe_skip",
            timeout=20000,
        )
        self.assertEqual(store_state(page)["lastActionResult"]["code"], "unsafe_skip")
        self.assertEqual(sent_action_count(page, "explore.wait"), 2)
        self.assertEqual(store_state(page)["serverTime"], time_before)

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_safe_wait_until_dawn_advances_the_clock(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Move away from the goblin, then wait until dawn succeeds.
        self._open_root(page, 0)  # Move
        _press(page, "Enter")  # first exit
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True and p["current_node"] != fixture_home_node_id(),
        )
        time_before = store_state(page)["serverTime"]
        # The shipped three-operation frame (webclient-exploration-menu,
        # 298bc61): 等待直到黎明 / 睡眠至完全恢復 dispatch their daypart wait
        # directly — a no-op at the fixture's midnight clock — while 休息 N
        # 小時 (wait-rest, the third card of the gridCols: 3 row) opens the
        # custom-duration form. Confirm the form's default one-hour wait so
        # the SKIP advance moves the fixture clock off midnight.
        self._open_root(page, 3)  # Wait/休息
        _press(page, "ArrowRight")  # 睡眠至完全恢復
        _press(page, "ArrowRight")  # 休息 N 小時
        _press(page, "Enter")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": ".exploration-rest-form input[type='number']",
                "predicate": (
                    "() => { const f = document.querySelector("
                    "'.exploration-rest-form input[type=\\'number\\']');"
                    "return !!f && document.activeElement === f; }"
                ),
                "description": "rest form's duration input focused",
            },
        )
        _press(page, "Enter")  # confirm the default one-hour wait
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("code") == "skipped",
            timeout=20000,
        )
        ok = store_state(page)["lastActionResult"]
        self.assertIsNotNone(ok, "a safe wait must succeed")
        time_after = store_state(page)["serverTime"]
        self.assertNotEqual(
            (time_after["hour"], time_after["minute"]),
            (time_before["hour"], time_before["minute"]),
            "a successful wait must advance the world clock",
        )

    @covers_requirement("webclient-exploration-menu::exploration-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_stale_and_tampered_submissions_do_nothing(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        map_before = store_state(page)["panels"]["local_map"]["current_node"]

        # A raw ui_action with a stale base_revision returns the dispatcher's
        # stale outcome and performs no traversal.
        page.evaluate(
            """() => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              const moveRow = s.panels.exploration.move[0];
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'stale-move-1',
                base_revision: 0,
                action_id: 'explore.move',
                payload: { exit_ref: moveRow.exit_ref, current_node: s.panels.local_map.current_node },
              }], {});
            }"""
        )
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") == "stale-move-1",
            timeout=20000,
        )
        self.assertEqual(store_state(page)["lastActionResult"]["outcome"], "stale")
        self.assertEqual(
            store_state(page)["panels"]["local_map"]["current_node"],
            map_before,
            "a stale move must not relocate the actor",
        )

        # A tampered exit_ref fails commit-time revalidation.
        page.evaluate(
            """() => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'tampered-move-1',
                base_revision: s.revision,
                action_id: 'explore.move',
                payload: { exit_ref: '999999', current_node: s.panels.local_map.current_node },
              }], {});
            }"""
        )
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") == "tampered-move-1",
            timeout=20000,
        )
        last = store_state(page)["lastActionResult"]
        self.assertEqual(last["outcome"], "rejected")
        self.assertEqual(last["code"], "no_exit")
        self.assertEqual(
            store_state(page)["panels"]["local_map"]["current_node"],
            map_before,
        )

    def _err_line_texts(self, page):
        """The rendered narrative err lines, in feed order."""
        return page.evaluate(
            """() => Array.from(
                 document.querySelectorAll(
                   '[data-testid="message-page"] [data-line-kind="err"]'),
                 (n) => n.textContent)"""
        )

    def _tamper_sender(self, page, tamper):
        """Wrap the live transport sender so dispatched envelopes pass through
        ``tamper`` (shallow-cloned; the store's envelope is never mutated in
        place). The caller stores ``window.__elosernOriginalSender`` first and
        restores it with ``_restore_sender``."""
        page.evaluate(
            """(tamperSource) => {
              const store = window.__elosernBridge.store;
              const original = window.__elosernOriginalSender;
              if (!original || typeof original.sendAction !== "function") {
                throw new Error("no stashed original sender");
              }
              const tamper = new Function("return " + tamperSource)();
              store.setSender({
                sendText: (text) => original.sendText(text),
                sendSync: () => original.sendSync(),
                sendAction: (envelope) => original.sendAction(tamper(envelope)),
              });
            }""",
            tamper,
        )

    def _restore_sender(self, page):
        page.evaluate(
            "() => window.__elosernBridge.store.setSender(window.__elosernOriginalSender)"
        )

    def _dispatch_move(self, page):
        """Dispatch one explore.move for the first exit through the store."""
        return page.evaluate(
            """() => {
              const s = window.__elosernBridge.store.view;
              const row = s.panels.exploration.move[0];
              return window.__elosernBridge.store.dispatchAction('explore.move', {
                exit_ref: row.exit_ref,
                current_node: s.panels.local_map.current_node,
              });
            }"""
        )

    def _wait_admitted_move(self, page, node_before):
        """Dispatch real moves until one is admitted (a presentation revision
        can advance between the view read and admission; the dispatcher then
        answers stale — the same bounded retry the move journey uses)."""
        for _attempt in range(3):
            request_id = self._dispatch_move(page)
            self.assertIsNotNone(request_id)
            try:
                wait_for_store_state(
                    page,
                    lambda s: (s.get("panels") or {}).get("local_map", {}).get("current_node")
                    != node_before,
                    timeout=10000,
                )
                return
            except AssertionError:
                last = store_state(page).get("lastActionResult") or {}
                self.assertEqual(
                    last.get("outcome"),
                    "stale",
                    "the move was neither admitted nor rejected as stale",
                )
                wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None)
        self.fail("three consecutive move dispatches were all answered stale")

    def _dock_holds_focus(self, page):
        """True when #action-dock (or a focusable descendant) is the active
        element — element identity, not a text marker (duck finding)."""
        return page.evaluate(
            """() => { const dock = document.getElementById('action-dock');
                       const el = document.activeElement;
                       return !!dock && !!el
                         && (el === dock || dock.contains(el)); }"""
        )

    def _wait_non_success_line(self, page, message, baseline):
        """Wait until the err-line multiset grew by exactly [message] over
        ``baseline`` (baseline-relative counting: pre-existing lines, the
        dispatch's own in-kind echo, and mutation echoes are all excluded --
        only the recognized result may add an err line)."""
        page.wait_for_function(
            """([message, baselineJson]) => {
                 const baseline = JSON.parse(baselineJson);
                 const lines = Array.from(
                   document.querySelectorAll(
                     '[data-testid="message-page"] [data-line-kind="err"]'),
                   (n) => n.textContent);
                 const counts = new Map();
                 for (const l of baseline) counts.set(l, (counts.get(l) || 0) + 1);
                 for (const l of lines) counts.set(l, (counts.get(l) || 0) - 1);
                 // added = actual-minus-baseline multiset diff (negative
                 // remaining count per occurrence of an unseen line).
                 const added = lines.filter((l) => (counts.get(l) || 0) < 0
                   && ((counts.set(l, counts.get(l) + 1), true)));
                 return added.length === 1 && added[0].includes(message);
               }""",
            arg=[message, json.dumps(baseline)],
        )

    @covers_requirement("webclient-action-dispatch::a-non-success-action-result-surfaces-its-message-exactly-once")
    def test_non_success_action_results_speak_once_in_the_narrative(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        # The stale admission needs a positive committed revision so the
        # decremented base_revision stays schema-valid (a negative one would
        # follow the malformed-envelope protocol-error path instead).
        wait_for_store_state(page, lambda s: (s.get("revision") or 0) > 0)
        node_before = store_state(page)["panels"]["local_map"]["current_node"]
        page.evaluate(
            "() => { window.__elosernOriginalSender = window.__elosernBridge.store.getSender(); }"
        )

        # (a) A real stale admission through the store's own dispatch path:
        # the sender wrapper sends the envelope with a superseded
        # base_revision; the dispatcher answers outcome `stale`.
        self._tamper_sender(
            page,
            "(e) => Object.assign({}, e, { base_revision: e.base_revision - 1 })",
        )
        dispatch_base = page.evaluate("() => window.__elosernBridge.store.view.revision")
        err_baseline = self._err_line_texts(page)
        request_id = page.evaluate(
            "() => window.__elosernBridge.store.dispatchAction('explore.wait', { daypart: 'dusk' })"
        )
        self.assertIsNotNone(request_id)
        # The wire envelope really carried the decremented revision.
        tampered = [
            args[0]
            for cmdname, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmdname == "ui_action" and args and args[0].get("request_id") == request_id
        ]
        self.assertEqual(len(tampered), 1)
        self.assertEqual(tampered[0]["base_revision"], dispatch_base - 1)
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") == request_id,
            timeout=20000,
        )
        self._restore_sender(page)
        result = store_state(page)["lastActionResult"]
        self.assertEqual(result["outcome"], "stale", f"expected stale, got {result}")
        message = result["message"]
        # The message renders verbatim and exactly once over the baseline err
        # multiset -- no second line, no accompanying mutation echo.
        self._wait_non_success_line(page, message, err_baseline)
        err_lines = [t for t in self._err_line_texts(page) if message in t]
        self.assertEqual(err_lines[0].strip(), message)
        self.assertEqual(page.locator('[role="dialog"]').count(), 0)
        self.assertEqual(sent_action_count(page, "explore.wait"), 1)
        self.assertEqual(
            store_state(page)["panels"]["local_map"]["current_node"],
            node_before,
            "the stale admission performed no traversal",
        )
        # The stale lock releases once the recovery revision commits.
        wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None)

        # (b) A real domain rejection: a genuine move commits the new room;
        # then a valid re-move whose sender wrapper replaces only
        # payload.current_node with the pre-move node reaches the exploration
        # adapter's stale-location rejection.
        self._wait_admitted_move(page, node_before)
        moved_node = store_state(page)["panels"]["local_map"]["current_node"]
        wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None)

        # Keyboard focus is held by the dock; a rendered result must not move
        # or steal it (no modal steals focus either).
        focus_action_dock(page)
        self.assertTrue(self._dock_holds_focus(page), "the dock did not take focus")
        self._tamper_sender(
            page,
            """(e) => Object.assign({}, e, {
                 payload: Object.assign({}, e.payload, { current_node: %r })
               })"""
            % node_before,
        )
        # Admission itself can race a revision advance (answered stale before
        # the adapter runs); retry the tampered dispatch until the adapter's
        # domain rejection lands, bounded. Stale retries append their own
        # (different) message, so the domain-message baseline is captured
        # right before the final accepted attempt.
        result = None
        for _attempt in range(3):
            err_baseline = self._err_line_texts(page)
            request_id = self._dispatch_move(page)
            self.assertIsNotNone(request_id)
            wait_for_store_state(
                page,
                lambda s: (s.get("lastActionResult") or {}).get("requestId") == request_id,
                timeout=20000,
            )
            result = store_state(page)["lastActionResult"]
            if result["outcome"] != "stale":
                self._wait_non_success_line(page, result.get("message", ""), err_baseline)
                break
            stale_message = result.get("message", "")
            wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None)
            # Settle the stale line's DOM append before re-capturing so the
            # next attempt's baseline multiset already contains it.
            page.wait_for_function(
                """(message) => message !== "" && Array.from(
                     document.querySelectorAll(
                       '[data-testid="message-page"] [data-line-kind="err"]'),
                     (n) => n.textContent).some((t) => t.includes(message))""",
                arg=stale_message,
            )
            err_baseline = self._err_line_texts(page)
        self._restore_sender(page)
        self.assertIsNotNone(result)
        self.assertEqual(
            result["outcome"], "rejected", f"expected domain rejection, got {result}"
        )
        self.assertEqual(result["code"], "stale_location")
        message = "你的位置已經改變，請重新操作。"
        self.assertEqual(result["message"], message)
        err_lines = [t for t in self._err_line_texts(page) if message in t]
        self.assertEqual(len(err_lines), 1)
        self.assertEqual(err_lines[0].strip(), message)
        # The player keeps keyboard focus without any modal.
        self.assertEqual(page.locator('[role="dialog"]').count(), 0)
        self.assertTrue(
            self._dock_holds_focus(page),
            "the rendered result moved keyboard focus out of the dock",
        )
        # The rejected move relocated nobody.
        self.assertEqual(
            store_state(page)["panels"]["local_map"]["current_node"],
            moved_node,
        )

    @covers_requirement("webclient-exploration-menu::exploration-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    def test_no_take_or_drop_control_is_rendered(self):
        page = self.logged_in_page((1280, 720))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        # The exploration dock renders no take/drop or generic object-mutation
        # control anywhere in the surface.
        body_text = page.locator("#action-dock").inner_text()
        self.assertNotIn("拾取", body_text)
        self.assertNotIn("丟棄", body_text)
        self.assertNotIn("explore.take", body_text)
        self.assertNotIn("explore.drop", body_text)
        sent = page.evaluate("window.__elosernSent || []")
        for cmdname, args, _kwargs in sent:
            if cmdname != "ui_action" or not args:
                continue
            self.assertFalse(
                args[0]["action_id"].startswith("explore.take"),
                "explore.take must never be submitted",
            )
            self.assertFalse(
                args[0]["action_id"].startswith("explore.drop"),
                "explore.drop must never be submitted",
            )
