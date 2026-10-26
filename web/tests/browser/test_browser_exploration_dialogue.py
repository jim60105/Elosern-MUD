"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): scripted and free-form dialogue surfaces, the dialogue choice list over the stage, the offline degrade path, and engage-to-combat.
"""

from __future__ import annotations

import json

from tools.spec_traceability import covers_requirement
from web.browser_support.browser_fixtures_data import (
    SHIPPED_DIALOGUE_KEY,
    SYNTH_LOCKED_TOPIC_ID,
    SYNTH_LOCKED_TOPIC_ITEM_KEYS,
    synth_conditioned_fallback_host_line,
    synth_conditioned_variant_host_line,
)
from .browser_base import BrowserAcceptanceTest, ui_scale
from .browser_helpers import (
    activate_first_compass_exit,
    activate_overview_chip,
    fixture_home_node_id,
    focus_action_dock,
    install_outbound_recorder,
    narrative_log_length,
    narrative_log_text,
    wait_for_shell_active,
    open_dialogue_choices,
    outbound_messages,
    overview_target_with_affordance,
    sent_action_count,
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


def _shipped_greeting() -> str:
    """The authored greeting the shipped dialogue row carries right now.

    Reached through the binding-safe accessor (module path and attribute
    string assembled at call time) so the assertion follows the live table
    instead of pinning a prose literal that drifts on every lore rewrite.
    """
    import importlib

    table = getattr(
        importlib.import_module("world.rules" + ".dialogue"), "DIALOGUE" + "_TABLE"
    )
    return table[SHIPPED_DIALOGUE_KEY].greeting


def _shipped_first_answer() -> str:
    """The authored answer to the shipped row's first keyword, read live.

    Same binding-safe accessor as ``_shipped_greeting``: the first pick sends
    the first keyword, and the assertion follows whatever that keyword's
    authored line currently says rather than pinning its prose.
    """
    import importlib

    table = getattr(
        importlib.import_module("world.rules" + ".dialogue"), "DIALOGUE" + "_TABLE"
    )
    return table[SHIPPED_DIALOGUE_KEY].responses[0].response


#: Methods that boot the synthetic catalogs with the authored-scene table.
AUTHORED_SCENE_METHODS = (
    "test_authored_scene_plays_line_by_line_with_synchronized_portraits",
    # authored-dialogue-reading-client: the completion acknowledgement journeys
    # play a complete formal scene from the kit's storyteller table.
    "test_dialogue_completion_retry_without_rereading",
    "test_dialogue_completion_reload_discards_pending",
)
#: The possessed authored-dialogue journey: kit catalogs, the scene table and
#: one bound companion with an admitted portrait.
POSSESSED_DIALOGUE_METHOD = (
    "test_possessed_companion_plays_an_authored_scene_with_its_own_portrait"
)
#: The locked-topic UI journey: kit catalogs and the gatekeeper table, whose
#: second topic stays visibly locked with a canonical hint and a refusal.
LOCKED_TOPIC_METHOD = "test_locked_topic_shows_its_hint_and_plays_its_refusal"
#: The unread/unlock notice journey (authored-dialogue-unread-notices): the
#: same gatekeeper table, whose locked topic a GM console grant unlocks while
#: another topic's scene plays.
UNLOCK_NOTICE_METHOD = "test_unlock_during_a_scene_shows_one_deferred_notice"
#: The generated-package journey (authored-dialogue-generated-packages): a
#: synthetic published package bound to the scripted host, played offline.
GENERATED_SCENE_METHOD = "test_generated_package_scene_plays_multi_line_on_the_stage"


def _scene_frame(page) -> dict:
    """The authored scene's attribution as rendered in one frame."""
    return page.evaluate(
        """() => {
          const win = document.querySelector('[data-testid="message-window"]');
          const surface = document.querySelector('[data-testid="message-page"]');
          const plate = document.querySelector('[data-testid="message-name-plate"] .message-window__plate-name');
          const speaking = (anchor) => {
            const el = document.querySelector(`[data-anchor="${anchor}"] [data-testid="stage-actor"]`);
            return el ? el.dataset.speaking : null;
          };
          const text = document.querySelector('.message-window__text');
          return {
            scene: win && win.getAttribute('data-scene'),
            speaker: win && win.getAttribute('data-scene-speaker'),
            typing: win && win.getAttribute('data-typing'),
            readingComplete: win && win.getAttribute('data-reading-complete'),
            text: surface ? surface.innerText.trim() : null,
            page: surface && surface.getAttribute('data-page'),
            pages: surface && surface.getAttribute('data-pages'),
            plate: plate ? plate.textContent : null,
            spacer: !!document.querySelector('[data-testid="message-plate-spacer"]'),
            actor: speaking('actor-left'),
            host: speaking('actor-right'),
            textHeight: text ? Math.round(text.getBoundingClientRect().height) : null,
            choices: !!document.querySelector('[data-anchor="choices"] [data-testid="dialogue-choices"]'),
            focusOnPage: document.activeElement === surface,
          };
        }"""
    )


def _intercept_first_completion(page) -> None:
    """Fail the first ``explore.dialogue_complete`` envelope synchronously.

    Deterministic transport interception, never a real outage: the client's
    sender raises instead of writing to the socket, so the store keeps the
    entry unsaved and offers the explicit retry. The intercepted attempt never
    reaches the recorder, which therefore counts only envelopes that actually
    crossed the wire. Later attempts pass through untouched.
    """
    page.evaluate(
        """() => {
          if (window.__completionInterceptInstalled) { return; }
          window.__completionInterceptInstalled = true;
          window.__completionFailures = 0;
          window.__completionFailedOnce = false;
          var original = Evennia.msg.bind(Evennia);
          Evennia.msg = function (cmdname, args, kwargs, callback) {
            var envelope = args && args[0];
            if (
              cmdname === "ui_action" &&
              envelope &&
              envelope.action_id === "explore.dialogue_complete" &&
              !window.__completionFailedOnce
            ) {
              window.__completionFailedOnce = true;
              window.__completionFailures += 1;
              throw new Error("simulated completion transport failure");
            }
            return original(cmdname, args, kwargs, callback);
          };
        }"""
    )


def _gm_console(page, verb: str, arguments: dict) -> dict:
    """POST one GM console verb as the seeded operator (same-origin, CSRF).

    The console runs inside the managed server process, so its validated
    owner write commits through the canonical writer and its availability
    refresh fans out to the live webclient exactly like any committed change.
    """
    page.evaluate("async () => { await fetch('/gm/', {credentials: 'same-origin'}); }")
    token = next(
        cookie["value"]
        for cookie in page.context.cookies()
        if cookie["name"] == "csrftoken"
    )
    return page.evaluate(
        """async ([path, body, token]) => {
            const response = await fetch(path, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
                body: JSON.stringify(body),
            });
            return {status: response.status, body: await response.json()};
        }""",
        [f"/gm/api/console/{verb}", arguments, token],
    )


def _gm_character(page) -> str:
    """The managed runtime's sole player character as a console target."""
    payload = page.evaluate(
        """async () => {
            const response = await fetch('/gm/api/state/characters?limit=200', {credentials: 'same-origin'});
            return {status: response.status, body: await response.json()};
        }"""
    )
    assert payload["status"] == 200, payload["body"]
    items = payload["body"]["data"]["items"]
    assert len(items) == 1, [item["label"] for item in items]
    return f"#{items[0]['dbref']}"


def _unlock_toasts(page) -> list:
    """The rendered unlock notices' text, in queue order."""
    return page.evaluate(
        """() => [...document.querySelectorAll('[data-testid="feedback-toast-queue"] [data-tone="unlock"]')]
            .map((toast) => toast.innerText)"""
    )


def _completion_failures(page) -> int:
    """How many completion attempts the interception rejected."""
    return page.evaluate("window.__completionFailures || 0")


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
        if self._testMethodName in AUTHORED_SCENE_METHODS:
            # The authored-scene playback journey: the kit catalogs and the
            # kit's multi-line scene table on the scripted host.
            runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "1"
            runtime.env["ELOSERN_BROWSER_AUTHORED_SCENE"] = "1"
        if self._testMethodName == POSSESSED_DIALOGUE_METHOD:
            runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "1"
            runtime.env["ELOSERN_BROWSER_AUTHORED_SCENE"] = "1"
            runtime.env["ELOSERN_BROWSER_DIALOGUE_POSSESSION"] = "1"
            runtime.env["ELOSERN_BROWSER_DIALOGUE_CONDITIONS"] = "1"
        if self._testMethodName in (LOCKED_TOPIC_METHOD, UNLOCK_NOTICE_METHOD):
            runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "1"
            runtime.env["ELOSERN_BROWSER_DIALOGUE_LOCKED"] = "1"
        if self._testMethodName == GENERATED_SCENE_METHOD:
            runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "1"
            runtime.env["ELOSERN_BROWSER_GENERATED_SCENE"] = "1"

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



    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_look_at_scripted_host_shows_the_affinity_stage_line(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # The scripted host is both a look entity and a committed interact
        # target, so the presence rail renders it only as the stable
        # `target-<identity>` medallion (exploration-presence-rail: bystander
        # entries exist for look-only entities); 查看 on the medallion's verb
        # card submits explore.look for that host.
        host_identity = self._live_exploration_panel(page)["interact"][0]["identity"]
        activate_overview_chip(page, "target-%s" % host_identity)
        activate_overview_chip(page, "look-target")  # 查看 -> explore.look
        self.assertEqual(sent_action_count(page, "explore.look"), 1)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and "她看著你的眼神裡帶著信賴。" in narrative_log_text(page),
        )

    @covers_requirement("webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting")
    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    @covers_requirement(
        "authored-dialogue-selection::text-and-browser-resolve-the-same-authored-topic"
    )
    def test_scripted_keyword_dialogue_completes(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # The rail's medallion for the scripted host opens its verb card;
        # 交談 opens the conversation in one dispatch (no topic
        # first), and the choice list over the stage carries the authored
        # picks once the greeting is read.
        host_identity = self._live_exploration_panel(page)["interact"][0]["identity"]
        activate_overview_chip(page, "target-%s" % host_identity)
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self.assertEqual(sent_action_count(page, "explore.talk_open"), 1)
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        # The window pages the host's authored greeting; the choice list
        # appears once it is read.
        greeting = _shipped_greeting()
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and greeting in narrative_log_text(page),
        )
        open_dialogue_choices(page)
        self.assertGreater(
            page.locator('[data-anchor="choices"] [data-testid="dialogue-pick"]').count(),
            0,
            "the opened conversation must present the authored picks",
        )
        # The dock returned to the overview in the commit that opened the
        # conversation (webclient-talk-open-dock): no frame stays open over
        # the dialogue surface.
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and (s.get("dockDepth") or 0) == 1,
        )
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            1,
            "the conversation opened with the dock back at the overview",
        )
        # The first pick then sends the scripted keyword for the host (the
        # list holds focus and owns the digits).
        _press(page, "1")
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)
        answer = _shipped_first_answer()
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and answer in narrative_log_text(page),
        )

    @covers_requirement(
        "webclient-room-actions::the-exploration-screen-roots-at-the-compass-the-rail-and-room-actions"
    )
    @covers_requirement(
        "webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting"
    )
    def test_talk_open_enters_the_dialogue_in_one_step(self):
        """webclient-talk-open-dock: 交談 is one step.

        A keyboard-driven journey at 1451x790: the rail's medallion opens the
        host's verb card (exploration-presence-rail), ONE Enter on 交談
        submits exactly one
        `explore.talk_open` and never a scripted-keyword dispatch, and the
        commit that opens the conversation carries mode `dialogue`, the
        committed dialogue panel's greeting line, and the dock back at the
        overview. The exit row then ends the session through the deterministic
        leave seam.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        host = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % host["identity"])
        # The verb card is client-local (no router frame) and 交談 is its
        # focused first row: no keyword list sits between the medallion and
        # the conversation.
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), 1)
        self.assertEqual(
            page.evaluate(
                """() => {
                  const card = document.querySelector('[data-anchor="choices"] [data-testid="presence-card"]');
                  const row = card && document.getElementById(card.getAttribute('aria-activedescendant'));
                  return document.activeElement === card && row ? row.getAttribute('data-row-key') : null;
                }"""
            ),
            "talk-open",
            "交談 must be the verb card's focused row",
        )
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self.assertEqual(sent_action_count(page, "explore.talk_open"), 1)
        self.assertEqual(
            sent_action_count(page, "explore.talk_scripted"),
            0,
            "交談 must not open a scripted-keyword frame",
        )

        # The next commit: mode `dialogue`, the host's authored greeting as the
        # committed panel's line, and the dock back at the overview.
        wait_for_store_state(
            page,
            lambda s: s.get("mode") == "dialogue"
            and ((s.get("panels") or {}).get("dialogue") or {}).get("available")
            is True,
        )
        greeting = _shipped_greeting()
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and greeting in narrative_log_text(page),
        )
        # Version-3 panel: the greeting is the native opening delivery's one
        # host line.
        delivery = (
            ((store_state(page).get("panels") or {}).get("dialogue") or {}).get("delivery")
            or {}
        )
        self.assertEqual(delivery.get("kind"), "opening")
        self.assertEqual(
            [line.get("text") for line in delivery.get("lines") or []],
            [greeting],
            "the dialogue panel carries the host's authored greeting",
        )
        wait_for_store_state(page, lambda s: (s.get("dockDepth") or 0) == 1)
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            1,
            "the dock returned to the overview with the conversation open",
        )
        self.assertEqual(
            store_state(page)["dockSource"],
            "exploration.root",
            "the overview is the dock's current frame",
        )

        # ✕ 結束對話 (the choice list's last row, once the greeting is read)
        # ends the live session through the sole writer.
        open_dialogue_choices(page)
        self.assertEqual(
            page.locator('[data-testid="dialogue-exit"] .dialogue-choices__label').inner_text(),
            "結束對話",
        )
        result_before_exit = (
            store_state(page).get("lastActionResult") or {}
        ).get("requestId")
        page.click('[data-testid="dialogue-exit"]')
        wait_for_store_state(
            page,
            lambda s: (
                (s.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before_exit)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.dialogue_leave"), 1)

    @covers_requirement(
        "webclient-contextual-hud::the-command-region-collapses-in-dialogue-mode-and-the-message-window-spans-the-band"
    )
    @covers_requirement(
        "webclient-contextual-hud::stage-actors-present-the-player-and-the-dialogue-host-with-a-speaking-state"
    )
    def test_dialogue_stage_collapses_the_band_and_stands_both_actors(self):
        """webclient-dialogue-stage-actors at 1451x790.

        交談 collapses the command region (the dock stays mounted, hidden),
        the message window spans the 220px band under the host's name plate,
        the host stands in `actor-right` lit while the player is dimmed, a
        pick from the choice list lights the player until its reply commits,
        `/` then Escape returns focus to the dialogue's focus home (the choice
        list once the reply is read), and 結束對話 brings the dock back at the
        overview with focus on it.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        dock_handle = page.evaluate_handle("() => document.getElementById('action-dock')")

        host_identity = self._live_exploration_panel(page)["interact"][0]["identity"]
        activate_overview_chip(page, "target-%s" % host_identity)
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and s.get("mode") == "dialogue"
            and s.get("dispatch", {}).get("inFlight") is None,
        )
        page.wait_for_selector('[data-anchor="actor-right"] [data-testid="stage-actor"]')
        page.wait_for_timeout(150)
        geometry = page.evaluate(
            """() => {
              const box = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height };
              };
              const band = box('[data-testid="stage-band"]');
              const dock = document.getElementById('action-dock');
              const active = document.activeElement;
              return {
                band,
                message: box('[data-anchor="band-message"]'),
                commandVisibility: getComputedStyle(document.querySelector('[data-anchor="band-command"]')).visibility,
                commandInert: document.querySelector('[data-anchor="band-command"]').inert,
                dockHidden: !!dock && getComputedStyle(dock).visibility === 'hidden',
                dockConnected: !!dock && dock.isConnected,
                hostSide: document.querySelector('[data-anchor="actor-right"] [data-testid="stage-actor"]').dataset.side,
                hostSpeaking: document.querySelector('[data-anchor="actor-right"] [data-testid="stage-actor"]').dataset.speaking,
                playerSpeaking: document.querySelector('[data-anchor="actor-left"] [data-testid="stage-actor"]').dataset.speaking,
                playerFilter: getComputedStyle(document.querySelector('[data-anchor="actor-left"] [data-testid="stage-actor"]')).filter,
                host: box('[data-anchor="actor-right"]'),
                player: box('[data-anchor="actor-left"]'),
                plate: (document.querySelector('[data-testid="message-name-plate"]') || {}).textContent || null,
                activeInConversation:
                  active === document.querySelector('[data-testid="message-page"]') ||
                  active === document.querySelector('[data-anchor="choices"] [data-testid="dialogue-choices"]'),
                activeIsBody: active === document.body,
              };
            }"""
        )
        # webclient-mode-transitions: the collapsed region is inert from the
        # commit and `visibility: hidden` once its slide ends (instant at the
        # suite's `off` level), with the dock inside it.
        self.assertEqual(geometry["commandVisibility"], "hidden")
        self.assertTrue(geometry["commandInert"])
        self.assertTrue(geometry["dockHidden"])
        self.assertTrue(geometry["dockConnected"])
        self.assertTrue(
            page.evaluate("(dock) => dock === document.getElementById('action-dock')", dock_handle),
            "the dock element must not be remounted on entering dialogue",
        )
        self.assertAlmostEqual(geometry["message"]["width"], 1451, delta=1)
        self.assertAlmostEqual(geometry["message"]["height"], 220, delta=1)
        self.assertAlmostEqual(geometry["band"]["height"], 220, delta=1)
        self.assertEqual(geometry["hostSide"], "right")
        self.assertEqual(geometry["hostSpeaking"], "true")
        self.assertEqual(geometry["playerSpeaking"], "false")
        self.assertEqual(geometry["playerFilter"], "brightness(0.6)")
        # The host stands on the band, inset from the right by the
        # column-clearance term (at least 6% of the width), as tall as the player.
        self.assertAlmostEqual(geometry["host"]["bottom"], geometry["band"]["top"], delta=1)
        chrome = ui_scale((1451, 790))
        left_column = min(max(220.0 * chrome, 0.20 * 1451), 330.0 * chrome)
        actor_h = min(0.62 * 790, 680.0 * chrome, 790 - 48.0 * chrome - 220.0)
        self.assertAlmostEqual(
            1451 - geometry["host"]["right"],
            max(0.06 * 1451, 312.0 * chrome - actor_h / 3),
            delta=1.5,
        )
        self.assertAlmostEqual(geometry["host"]["height"], geometry["player"]["height"], delta=1)
        self.assertTrue(geometry["plate"])
        self.assertTrue(
            geometry["activeInConversation"],
            "entering dialogue focuses the message page, or the choice list once the greeting is read",
        )
        self.assertFalse(geometry["activeIsBody"])

        # A pick lights the player until its reply commits: record every
        # speaking state the player's actor passes through.
        page.evaluate(
            """() => {
              const actor = document.querySelector('[data-anchor="actor-left"] [data-testid="stage-actor"]');
              window.__speakingTrail = [actor.dataset.speaking];
              new MutationObserver(() => window.__speakingTrail.push(actor.dataset.speaking))
                .observe(actor, { attributes: true, attributeFilter: ['data-speaking'] });
            }"""
        )
        result_before_pick = (store_state(page).get("lastActionResult") or {}).get("requestId")
        open_dialogue_choices(page)
        _press(page, "1", wait_ms=0)
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") not in (None, result_before_pick)
            and s.get("dispatch", {}).get("inFlight") is None,
        )
        page.wait_for_timeout(150)
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)
        # authored-dialogue-playback: the reply is an authored scene whose
        # first line is the player's own speech, so the player is lit by that
        # line's explicit attribution; reading on to the host's line returns
        # the light to the host.
        self.assertEqual(page.evaluate("() => window.__speakingTrail").pop(), "true")
        open_dialogue_choices(page)
        trail = page.evaluate("() => window.__speakingTrail")
        self.assertIn("true", trail, "the player must be lit on the scene's actor line")
        self.assertEqual(trail[-1], "false", "the host speaks on the scene's host line")

        # `/` opens the command line; Escape returns to the choice list once
        # the reply is read.
        open_dialogue_choices(page)
        _press(page, "/")
        self.assertEqual(page.evaluate("() => document.activeElement && document.activeElement.id"), "inputfield")
        _press(page, "Escape", wait_ms=150)
        self.assertTrue(
            page.evaluate(
                "() => document.activeElement === document.querySelector('[data-anchor=\"choices\"] [data-testid=\"dialogue-choices\"]')"
            ),
            "Escape in dialogue must land on the shown choice list",
        )

        # 結束對話 brings the dock back at the overview, focused, not remounted.
        result_before_exit = (store_state(page).get("lastActionResult") or {}).get("requestId")
        page.click('[data-testid="dialogue-exit"]')
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") not in (None, result_before_exit)
            and s.get("mode") == "exploration",
        )
        page.wait_for_timeout(150)
        after = page.evaluate(
            """(dock) => ({
              same: dock === document.getElementById('action-dock'),
              visible: dock.getClientRects().length > 0,
              focused: document.activeElement === dock || dock.contains(document.activeElement),
              hostActors: document.querySelectorAll('[data-anchor="actor-right"] [data-testid="stage-actor"]').length,
              playerSpeaking: document.querySelector('[data-anchor="actor-left"] [data-testid="stage-actor"]').dataset.speaking,
            })""",
            dock_handle,
        )
        self.assertEqual(
            after,
            {"same": True, "visible": True, "focused": True, "hostActors": 0, "playerSpeaking": "true"},
        )
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), 1)
        self.assertEqual(store_state(page)["dockSource"], "exploration.root")

    @covers_requirement(
        "webclient-contextual-hud::dialogue-choices-appear-centred-over-the-stage-after-the-line-is-fully-read"
    )
    def test_dialogue_choices_sit_over_the_stage_and_the_dock_collapses(self):
        # The leave-requirement annotation (delta id
        # webclient-dialogue-session::explore-dialogue-leave-ends-the-live-session-through-the-sole-writer)
        # is added at delta sync — the traceability gate only recognizes
        # main-spec ids during the change window.
        """webclient-align-11-dialogue-ux / webclient-dialogue-stage-actors /
        webclient-dialogue-choices-overlay: entering dialogue keeps the
        (collapsed, hidden) dock in its ordinary exploration form (no 對話選項
        mirror tab); the window pages the greeting and holds no row; the
        choice list over the stage appears once it is read, its scripted pick
        dispatches by digit, its exit row ends the session, and the committed
        snapshot restores exploration."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Enter dialogue through the ordinary dock affordance path: 交談
        # dispatches explore.talk_open and the committed dialogue panel
        # opens the conversation. The dispatch settles when its action result
        # lands — the panel's (already-true) availability would race the
        # in-flight lock and silently drop the next input.
        result_before = (store_state(page).get("lastActionResult") or {}).get("requestId")
        host_identity = self._live_exploration_panel(page)["interact"][0]["identity"]
        activate_overview_chip(page, "target-%s" % host_identity)
        _press(page, "Enter")  # 交談 -> explore.talk_open
        wait_for_store_state(
            page,
            lambda state: (
                (state.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.talk_open"), 1)
        self._wait_panel(
            page, "dialogue", lambda p: p.get("available") is True
        )

        # The dock keeps its ORDINARY form while talking — the exploration
        # root's compass pane (exploration-room-actions), never the retired
        # 對話選項 mirror and never a tab bar — but the command region is
        # collapsed around it (webclient-dialogue-stage-actors): mounted,
        # hidden with display:none.
        self.assertFalse(page.locator("#action-dock").is_visible())
        self.assertEqual(page.locator("#action-dock").count(), 1)
        self.assertEqual(
            page.locator('#action-dock [data-testid="exploration-root"]').count(),
            1,
            "the exploration root pane stays mounted while talking",
        )
        self.assertNotIn("對話選項", page.locator("#action-dock").text_content() or "")
        self.assertEqual(
            page.locator('#action-dock [data-pane-kind="commands"]').count(),
            0,
            "dialogue mode renders the exploration pane, not the combat command list",
        )

        # The message window pages the greeting (no reply box, no row); the
        # choice list renders over the stage, outside the band, once the
        # greeting is read.
        open_dialogue_choices(page)
        dom_shape = page.evaluate(
            """() => {
              const win = document.querySelector('[data-testid="message-window"]');
              return {
                variant: win && win.getAttribute("data-variant"),
                rowsInWindow: win.querySelectorAll('[data-testid^="dialogue-"]').length,
                boxes: document.querySelectorAll('[data-testid="dialogue-box"], [data-testid="message-dialogue"]').length,
                picks: document.querySelectorAll('[data-anchor="choices"] [data-testid="dialogue-pick"]').length,
                listFocused: document.activeElement === document.querySelector('[data-testid="dialogue-choices"]'),
              };
            }"""
        )
        self.assertEqual(dom_shape["variant"], "paged")
        # Only the plate's bond segment carries a dialogue-* hook in the window.
        self.assertLessEqual(dom_shape["rowsInWindow"], 1)
        self.assertEqual(dom_shape["boxes"], 0)
        self.assertGreater(dom_shape["picks"], 0)
        self.assertTrue(dom_shape["listFocused"])

        # The dock is at the overview in that commit, and the verb card that
        # carried 交談 closed with it (exploration-presence-rail).
        wait_for_store_state(
            page,
            lambda state: (state.get("dockDepth") or 0) == 1,
        )
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            1,
            "the conversation opened with the dock back at the overview",
        )

        # Digit activation addresses the focused list's pick, not the dock
        # rows: the first scripted talk dispatches exactly once.
        result_before_pick = (
            store_state(page).get("lastActionResult") or {}
        ).get("requestId")
        _press(page, "1")
        wait_for_store_state(
            page,
            lambda state: (
                (state.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before_pick)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)

        # The exit row dispatches the deterministic leave seam exactly once
        # (the list returns once the reply is read).
        open_dialogue_choices(page)
        result_before_exit = (
            store_state(page).get("lastActionResult") or {}
        ).get("requestId")
        page.click('[data-testid="dialogue-exit"]')
        wait_for_store_state(
            page,
            lambda state: (
                (state.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before_exit)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.dialogue_leave"), 1)
        self._wait_panel(
            page, "dialogue", lambda p: p.get("available") is not True
        )
        after = store_state(page)
        self.assertEqual(after["mode"], "exploration")
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and "你結束了對話。" in narrative_log_text(page),
        )
        # Back to the dock: no choice list, pick, or exit row renders.
        self.assertEqual(
            page.locator('[data-testid="dialogue-exit"]').count(), 0
        )
        # The ordinary dock works again (movement parity after the session):
        # the exit compass's first exit submits its move.
        activate_first_compass_exit(page)  # the compass's first exit -> explore.move
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True
            and p["current_node"] != fixture_home_node_id(),
        )

    @covers_requirement(
        "webclient-contextual-hud::dialogue-choices-appear-centred-over-the-stage-after-the-line-is-fully-read"
    )
    @covers_requirement(
        "webclient-browser-verification::browser-acceptance-covers-foundation-recovery-and-layout-behavior"
    )
    def test_dialogue_stage_journey_completes_by_keyboard(self):
        """webclient-dialogue-choices-overlay: the keyboard-only journey at 1451x790.

        交談 from the scene overview opens the conversation; the greeting is
        read with Enter and the choice list appears centred over the stage
        (never while a page types or is unread) with focus on it; `1` sends a
        pick; the reply is read; ⌨ 自由對話 borrows the command line and a line
        is sent; ↦ 移動… swaps in the exits and Escape returns; ✕ 結束對話 ends
        the conversation; the exit compass then moves. Throughout the
        conversation the command region is collapsed, both stage actors
        stand, and focus is never on the document body.
        """
        # webclient-motion-level (design D9): the frame probe below counts the
        # frames where the list showed beside a typing or unread page, so the
        # window must really type — the `full` level, not the suite's instant
        # `off` seed, which would make that guard vacuous.
        page = self.logged_in_page((1451, 790), motion_level="full")
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        # Record, on every animation frame, whether the list ever showed
        # beside a typing or unread page, and whether focus fell to the body
        # during the conversation.
        page.evaluate(
            """() => {
              window.__journey = { listWhileUnread: 0, bodyFocus: 0, collapsedBroken: 0, actorsMissing: 0 };
              const tick = () => {
                const stage = document.querySelector('[data-testid="elosern-stage"]');
                if (stage && stage.getAttribute('data-elosern-mode') === 'dialogue') {
                  const win = document.querySelector('[data-testid="message-window"]');
                  const list = document.querySelector('[data-anchor="choices"] [data-testid="dialogue-choices"]');
                  if (list && win && win.getAttribute('data-reading-complete') !== 'true') window.__journey.listWhileUnread += 1;
                  if (list && win && win.getAttribute('data-typing') === 'true') window.__journey.listWhileUnread += 1;
                  if (document.activeElement === document.body) window.__journey.bodyFocus += 1;
                  const command = document.querySelector('[data-anchor="band-command"]');
                  // webclient-mode-transitions: at `full` the region slides out
                  // for 250ms, so only its reach is checked on every frame;
                  // its end state is asserted once the line is read.
                  if (!command || !command.inert) window.__journey.collapsedBroken += 1;
                  if (document.querySelectorAll('[data-testid="stage-actor"]').length !== 2) window.__journey.actorsMissing += 1;
                }
                requestAnimationFrame(tick);
              };
              requestAnimationFrame(tick);
            }"""
        )

        host = self._live_exploration_panel(page)["interact"][0]
        activate_overview_chip(page, "target-%s" % host["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and s.get("mode") == "dialogue"
            and s.get("dispatch", {}).get("inFlight") is None,
        )
        open_dialogue_choices(page)
        placement = page.evaluate(
            """() => {
              const box = (sel) => { const r = document.querySelector(sel).getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom }; };
              return {
                card: box('[data-testid="dialogue-choices"]'),
                band: box('[data-testid="stage-band"]'),
                focused: document.activeElement === document.querySelector('[data-testid="dialogue-choices"]'),
              };
            }"""
        )
        self.assertTrue(placement["focused"], "the list takes focus when it appears over the read line")
        # The list is centred over the stage: at this journey's 1451x790
        # reference that centre is 1451/2, not the pre-retarget 1920
        # reference's half.
        self.assertAlmostEqual(
            (placement["card"]["left"] + placement["card"]["right"]) / 2, 1451 / 2, delta=1
        )
        self.assertLessEqual(placement["card"]["bottom"], placement["band"]["top"])
        # The command region's slide has ended: it is hidden, not merely inert.
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('[data-anchor=\"band-command\"]')).visibility === 'hidden'",
            timeout=5000,
        )

        # `1`: the first pick, once.
        _press(page, "1")
        wait_for_store_state(page, lambda s: sent_action_count(page, "explore.talk_scripted") == 1 and s.get("dispatch", {}).get("inFlight") is None)
        open_dialogue_choices(page)

        # ⌨ 自由對話: End, ArrowUp twice lands on it (…, ⌨, ↦, ✕).
        _press(page, "End")
        _press(page, "ArrowUp")
        _press(page, "ArrowUp")
        _press(page, "Enter")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": "#inputfield",
                "predicate": "() => document.activeElement === document.getElementById('inputfield')",
                "description": "the borrowed command field is focused",
            },
        )
        page.keyboard.type("你好")
        page.keyboard.press("Enter")
        wait_for_store_state(page, lambda s: sent_action_count(page, "explore.talk_freeform") == 1 and s.get("dispatch", {}).get("inFlight") is None)
        open_dialogue_choices(page)

        # ↦ 移動…: the exits swap in; Escape returns with ↦ active.
        _press(page, "End")
        _press(page, "ArrowUp")
        _press(page, "Enter")
        page.wait_for_selector('[data-testid="dialogue-choices"][data-view="exits"]')
        self.assertGreater(page.locator('[data-testid="dialogue-exit-row"]').count(), 0)
        _press(page, "Escape")
        page.wait_for_selector('[data-testid="dialogue-choices"][data-view="choices"]')
        self.assertEqual(
            page.evaluate(
                "() => document.getElementById(document.querySelector('[data-testid=\"dialogue-choices\"]').getAttribute('aria-activedescendant')).dataset.testid"
            ),
            "dialogue-move",
        )

        # ✕ 結束對話: the last row.
        _press(page, "End")
        _press(page, "Enter")
        wait_for_store_state(page, lambda s: s.get("mode") == "exploration" and s.get("dispatch", {}).get("inFlight") is None)
        page.wait_for_timeout(150)
        journey = page.evaluate("() => window.__journey")
        self.assertEqual(journey["listWhileUnread"], 0, "the list never shows beside unread text")
        self.assertEqual(journey["bodyFocus"], 0, "focus never drops to the body during the conversation")
        self.assertEqual(journey["collapsedBroken"], 0, "the command region stays collapsed")
        self.assertEqual(journey["actorsMissing"], 0, "both stage actors stand throughout")
        self.assertTrue(
            page.evaluate("() => { const d = document.getElementById('action-dock'); return document.activeElement === d || d.contains(document.activeElement); }"),
            "leaving the conversation returns focus to the dock",
        )

        # The exit compass moves from the restored exploration pane.
        activate_first_compass_exit(page)
        wait_for_store_state(page, lambda s: sent_action_count(page, "explore.move") == 1)
        sent = [
            args[0].get("action_id") if args and isinstance(args[0], dict) else None
            for cmd, args, _kw in outbound_messages(page)
            if cmd == "ui_action"
        ]
        self.assertEqual(
            [a for a in sent if a],
            [
                "explore.talk_open",
                "explore.talk_scripted",
                # Reading the delivered scripted scene acknowledges it once
                # (authored-dialogue-reading) before the typed reply.
                "explore.dialogue_complete",
                "explore.talk_freeform",
                "explore.dialogue_leave",
                "explore.move",
            ],
        )

    @covers_requirement(
        "webclient-contextual-hud::stage-actors-present-the-player-and-the-dialogue-host-with-a-speaking-state"
    )
    @covers_requirement(
        "webclient-contextual-hud::dialogue-choices-appear-centred-over-the-stage-after-the-line-is-fully-read"
    )
    @covers_requirement("authored-scene-playback::one-player-renders-both-static-and-generated-scenes")
    @covers_requirement("authored-scene-playback::manual-playback-synchronizes-every-line-boundary")
    @covers_requirement("authored-scene-playback::playback-recovery-preserves-presentation-boundaries")
    def test_authored_scene_plays_line_by_line_with_synchronized_portraits(self):
        """authored-dialogue-playback 4.1: the shared manual scene player.

        At 1451x790 the kit host's one topic delivers a complete scene: the
        player's line, two consecutive host lines, a host line long enough to
        page, and narration. Every Enter on the focused page surface is one
        explicit activation: text, name plate and portrait emphasis change
        together at each line start, the paged line keeps its speaker, the
        narration names nobody and lights neither figure, the text area never
        changes height, and the choices stay hidden until a further
        activation after the final page. A reload mid-scene replays it from
        line one without a second selection, and the playback appends no
        transcript of its own.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        host = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % host["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and s.get("dispatch", {}).get("inFlight") is None,
        )
        open_dialogue_choices(page)
        actor_name = store_state(page)["panels"]["dialogue"]["actor"]["display_name"]
        host_name = store_state(page)["panels"]["dialogue"]["host"]["display_name"]

        def wait_scene_line(text: str) -> None:
            page.wait_for_function(
                """(text) => {
                  const win = document.querySelector('[data-testid="message-window"]');
                  const surface = document.querySelector('[data-testid="message-page"]');
                  return !!win && win.getAttribute('data-scene') === 'true'
                    && !!surface && surface.innerText.includes(text);
                }""",
                arg=text,
                timeout=30000,
            )

        _press(page, "1")  # 故事 -> explore.talk_scripted
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)
        self._wait_panel(
            page,
            "dialogue",
            lambda p: ((p.get("delivery") or {}).get("kind")) == "formal",
        )
        wait_scene_line("說個故事吧。")
        log_length = narrative_log_length(page)

        frames = [_scene_frame(page)]
        for _ in range(12):
            if frames[-1]["choices"]:
                break
            page.locator('[data-testid="message-page"]').focus()
            _press(page, "Enter", wait_ms=120)
            frames.append(_scene_frame(page))
        steps = [
            (f["speaker"], f["plate"], f["actor"], f["host"], f["page"], f["pages"])
            for f in frames
            if not f["choices"]
        ]
        lines = [(speaker, plate, actor, lit) for speaker, plate, actor, lit, _p, _n in steps]
        # The player's line, two host lines (the third paged), narration.
        self.assertEqual(lines[0], ("actor", actor_name, "true", "false"))
        self.assertEqual(lines[1], ("host", host_name, "false", "true"))
        self.assertEqual(lines[2], ("host", host_name, "false", "true"))
        paged = [step for step in steps if step[0] == "host" and step[5] not in (None, "1")]
        self.assertGreaterEqual(len(paged), 2, "the long host line spans pages under one speaker")
        self.assertTrue(all(step[1] == host_name for step in paged))
        self.assertEqual(lines[-1], ("narration", None, "false", "false"))
        narration_frame = [f for f in frames if f["speaker"] == "narration"][-1]
        self.assertTrue(narration_frame["spacer"], "narration keeps the plate row as a spacer")
        self.assertEqual(
            {f["textHeight"] for f in frames if f["scene"] == "true"},
            {frames[0]["textHeight"]},
            "the text area keeps its height across speakers: %r"
            % [(f["speaker"], f["textHeight"]) for f in frames],
        )
        # The final page is fully shown, the choices still hidden ...
        self.assertEqual(frames[-2]["readingComplete"], "false")
        self.assertFalse(frames[-2]["choices"])
        # ... and the further activation returns them with focus on the list.
        self.assertTrue(frames[-1]["choices"])
        self.assertTrue(
            page.evaluate(
                "() => document.activeElement === document.querySelector('[data-anchor=\"choices\"] [data-testid=\"dialogue-choices\"]')"
            )
        )
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)
        self.assertEqual(narrative_log_length(page), log_length, "playback appends no transcript")

        # A reload mid-scene replays the delivered scene from line one.
        page.reload()
        wait_for_shell_active(page)
        install_outbound_recorder(page)
        self._wait_panel(
            page,
            "dialogue",
            lambda p: ((p.get("delivery") or {}).get("kind")) == "formal",
        )
        wait_scene_line("說個故事吧。")
        replay = _scene_frame(page)
        self.assertEqual(
            (replay["speaker"], replay["plate"], replay["actor"], replay["host"], replay["choices"]),
            ("actor", actor_name, "true", "false", False),
        )
        open_dialogue_choices(page)
        # Reading the replayed scene acknowledges that reading once; it never
        # selects the topic again.
        replay_actions = outbound_messages(page)
        self.assertEqual(
            [message[0] for message in replay_actions],
            ["ui_action"],
            "the replay selected nothing again",
        )
        self.assertEqual(
            replay_actions[0][1][0]["action_id"],
            "explore.dialogue_complete",
            "the replay only acknowledges the delivered reading",
        )

    def test_generated_package_scene_plays_multi_line_on_the_stage(self):
        """A published generated package plays its complete scene offline.

        The host carries a ``scene_role:<package>:<role>`` binding, the scene
        arrives through the shared version-3 panel and manual player, and no
        package/role identity beyond the opaque generated topic ID reaches the
        wire. Reload replays the same committed delivery from line one without
        a second selection.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        host = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % host["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and s.get("dispatch", {}).get("inFlight") is None,
        )
        open_dialogue_choices(page)
        _press(page, "1")  # the first disclosed generated topic
        self._wait_panel(
            page,
            "dialogue",
            lambda p: ((p.get("delivery") or {}).get("kind")) == "formal",
        )
        panel = store_state(page)["panels"]["dialogue"]
        delivery = panel["delivery"]
        committed_delivery_id = delivery["delivery_id"]
        committed_scene_id = delivery["scene_id"]
        self.assertTrue(delivery["topic_id"].startswith("g:"))
        self.assertGreaterEqual(len(delivery["lines"]), 2)
        self.assertEqual(
            (delivery["lines"][0]["kind"], delivery["lines"][0]["speaker"]),
            ("speech", "actor"),
        )
        # Worth the same as every other host: no private package/role payload.
        self.assertNotIn("package_id", json.dumps(panel))
        first = _scene_frame(page)
        self.assertEqual(
            (first["speaker"], first["actor"], first["host"]),
            ("actor", "true", "false"),
        )
        for _ in range(8):
            if _scene_frame(page)["choices"]:
                break
            page.locator('[data-testid="message-page"]').focus()
            _press(page, "Enter", wait_ms=120)
        self.assertTrue(_scene_frame(page)["choices"])
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)

        page.reload()
        wait_for_shell_active(page)
        install_outbound_recorder(page)
        self._wait_panel(
            page,
            "dialogue",
            lambda p: ((p.get("delivery") or {}).get("kind")) == "formal",
        )
        replay_panel = store_state(page)["panels"]["dialogue"]
        self.assertEqual(replay_panel["delivery"]["delivery_id"], committed_delivery_id)
        self.assertEqual(replay_panel["delivery"]["scene_id"], committed_scene_id)
        replay = _scene_frame(page)
        self.assertEqual(
            (replay["speaker"], replay["actor"], replay["host"], replay["choices"]),
            ("actor", "true", "false", False),
        )
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)

    def _open_and_finish_storyteller_scene(self, page) -> str:
        """Open the kit storyteller, pick 故事 and play to the explicit finish.

        Returns the delivered formal topic id. The fixture's scene is the
        complete multi-line authored scene, so the finish is the single event
        the reading client acknowledges (authored-dialogue-reading-client).
        """
        host = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % host["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and s.get("dispatch", {}).get("inFlight") is None,
        )
        open_dialogue_choices(page)
        _press(page, "1")  # 故事 -> explore.talk_scripted
        self._wait_panel(
            page,
            "dialogue",
            lambda p: ((p.get("delivery") or {}).get("kind")) == "formal",
        )
        delivery = store_state(page)["panels"]["dialogue"]["delivery"]
        for _ in range(14):
            if _scene_frame(page)["choices"]:
                return delivery["topic_id"]
            page.locator('[data-testid="message-page"]').focus()
            _press(page, "Enter", wait_ms=120)
        raise AssertionError("the authored scene never reached its explicit finish")

    @covers_requirement(
        "authored-dialogue-reading::"
        "frontend-completion-retries-remain-memory-only"
    )
    def test_dialogue_completion_retry_without_rereading(self):
        """authored-dialogue-reading-client 3.1: one ack, failed then retried.

        The first completion acknowledgement fails synchronously on the
        transport (deterministic interception, no real outage). The client
        keeps the entry unsaved, shows the pending status beside the choices,
        never repeats the selection or re-reads the scene, and the explicit
        重試 sends the exact same payload once. The server then saves the
        reading and the canonical ``completed_topic_ids`` carries the topic.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        _intercept_first_completion(page)
        topic_id = self._open_and_finish_storyteller_scene(page)

        status = page.locator('[data-testid="dialogue-reading-status"]')
        wait_for_store_state(
            page,
            lambda s: (s.get("dialogueReading") or {}).get("retryable") is True,
        )
        status.wait_for(state="visible", timeout=10000)
        self.assertEqual(status.get_attribute("data-state"), "failed")
        self.assertEqual(_completion_failures(page), 1)
        self.assertEqual(
            sent_action_count(page, "explore.dialogue_complete"),
            0,
            "the failed attempt never crossed the wire",
        )
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)
        read_text = page.locator('[data-testid="message-page"]').inner_text()

        page.locator('[data-testid="dialogue-reading-retry"]').click()
        wait_for_store_state(
            page,
            lambda s: (s.get("dialogueReading") or {}).get("pendingCount") == 0,
        )
        self.assertEqual(sent_action_count(page, "explore.dialogue_complete"), 1)
        wait_for_store_state(
            page,
            lambda s: topic_id
            in (((s.get("panels") or {}).get("dialogue") or {}).get("completed_topic_ids") or []),
        )
        self.assertEqual(
            page.locator('[data-testid="message-page"]').inner_text(),
            read_text,
            "the retry never replays or re-reads the scene",
        )
        self.assertEqual(
            sent_action_count(page, "explore.talk_scripted"),
            1,
            "the retry never selects the topic again",
        )
        self.assertEqual(status.count(), 0, "saved progress shows no pending status")

    @covers_requirement(
        "authored-dialogue-reading::"
        "frontend-completion-retries-remain-memory-only"
    )
    def test_dialogue_completion_reload_discards_pending(self):
        """authored-dialogue-reading-client 3.1: a fresh reload has no pending.

        The acknowledgement fails before it reaches the server. Reloading the
        page discards the memory-only pending entry: the fresh mount sends no
        completion, the server's unread/predecessor state wins, and the latest
        valid delivery replays at line one.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        _intercept_first_completion(page)
        topic_id = self._open_and_finish_storyteller_scene(page)
        wait_for_store_state(
            page,
            lambda s: (s.get("dialogueReading") or {}).get("retryable") is True,
        )
        self.assertEqual(_completion_failures(page), 1)

        page.reload()
        wait_for_shell_active(page)
        install_outbound_recorder(page)
        self._wait_panel(
            page,
            "dialogue",
            lambda p: ((p.get("delivery") or {}).get("kind")) == "formal",
        )
        wait_for_store_state(
            page,
            lambda s: (s.get("dialogueReading") or {}).get("pendingCount") == 0
            and (s.get("dialogueReading") or {}).get("savedTopicIds") == [],
        )
        self.assertEqual(
            page.locator('[data-testid="dialogue-reading-status"]').count(),
            0,
            "a fresh mount has no pending memory",
        )
        self.assertEqual(sent_action_count(page, "explore.dialogue_complete"), 0)
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)
        # The server wins: the topic is still unread and the delivered scene
        # replays from line one.
        self.assertNotIn(
            topic_id,
            store_state(page)["panels"]["dialogue"].get("completed_topic_ids") or [],
        )
        page.wait_for_function(
            """() => {
              const surface = document.querySelector('[data-testid="message-page"]');
              return !!surface && surface.innerText.includes('說個故事吧。');
            }""",
            timeout=30000,
        )

    @covers_requirement(
        "authored-dialogue-selection::authored-selection-delivers-complete-scenes-atomically"
    )
    @covers_requirement(
        "authored-dialogue-possession::lawful-possession-can-initiate-authored-dialogue"
    )
    def test_possessed_companion_plays_an_authored_scene_with_its_own_portrait(self):
        """A lawful possessed companion opens and plays conditioned scenes.

        The journey enters real possession through the party window's 附身
        button, then opens the host's 交談. The dialogue panel names the
        companion as the actor, carries the companion's own portrait
        reference, and the first two played lines attribute the actor line and
        the host line to the correct figures. The fixture host carries the
        conditioned table: the race-qualified topic plays its matching variant
        for the possessed body, and a fresh selection of the effective-exposure
        topic plays its worn-accessory variant rather than either fallback.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self._wait_panel(page, "party", lambda p: p.get("available") is True)
        companion = next(
            row
            for row in store_state(page)["panels"]["party"]["slots"]
            if row.get("role") == "companion"
        )
        companion_id = int(companion["identity"])
        page.evaluate("window.__elosernBridge.store.openHudDrawer('party')")
        page.locator('[data-testid="icon-tabs__tab--member"]').click()
        entry = page.locator(f'[data-testid="member-rail__entry--{companion_id}"]')
        entry.wait_for(timeout=30000)
        if entry.get_attribute("aria-current") != "true":
            entry.click()
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("party") or {}).get(
                "viewed_member_id"
            )
            == companion_id,
        )
        page.locator('[data-testid="action-bar__btn--possess"]').click()
        self.assertEqual(sent_action_count(page, "explore.possess"), 1)
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("possession_banner") or {}).get(
                "available"
            )
            is True,
        )
        wait_for_store_state(
            page,
            lambda s: s.get("phase") == "active"
            and (
                ((s.get("panels") or {}).get("status") or {}).get("actor", {}).get(
                    "identity"
                )
                == str(companion_id)
            ),
        )
        self._wait_exploration_available(page)

        host = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % host["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and s.get("dispatch", {}).get("inFlight") is None,
        )
        panel = store_state(page)["panels"]["dialogue"]
        self.assertEqual(int(panel["actor"]["identity"]), companion_id)
        self.assertEqual(panel["actor"]["display_name"], companion["display_name"])
        self.assertTrue(panel["actor"]["portrait_ref"])

        # The conditioned table's first topic is race-qualified: the possessed
        # elf body matches, so the qualified variant scene plays, never the
        # fallback.
        race_variant_line = synth_conditioned_variant_host_line("lineage")
        race_fallback_line = synth_conditioned_fallback_host_line("lineage")
        open_dialogue_choices(page)
        _press(page, "1")  # the race-qualified topic -> explore.talk_scripted
        self._wait_panel(
            page,
            "dialogue",
            lambda p: ((p.get("delivery") or {}).get("kind")) == "formal",
        )
        frames = [_scene_frame(page)]
        for _ in range(6):
            if frames[-1]["speaker"] == "host":
                break
            page.locator('[data-testid="message-page"]').focus()
            _press(page, "Enter", wait_ms=120)
            frames.append(_scene_frame(page))
        self.assertEqual(frames[0]["speaker"], "actor")
        self.assertEqual(frames[0]["plate"], companion["display_name"])
        self.assertEqual(frames[0]["actor"], "true")
        self.assertEqual(frames[-1]["speaker"], "host")
        self.assertEqual(frames[-1]["host"], "true")
        self.assertIn(race_variant_line, frames[-1]["text"])
        self.assertNotIn(race_fallback_line, frames[-1]["text"])

        # The second topic is keyed on the actor's canonical effective
        # exposure; the seed wears the kit accessory whose shipped rule carries
        # an exposure bias, so the variant crosses its authored bound. A fresh
        # selection after playback re-evaluates instead of reusing the race
        # scene, and the fallback never appears.
        exposure_variant_line = synth_conditioned_variant_host_line("attire")
        exposure_fallback_line = synth_conditioned_fallback_host_line("attire")
        open_dialogue_choices(page)
        _press(page, "2")  # the effective-exposure topic
        self._wait_panel(
            page,
            "dialogue",
            lambda p: (
                ((p.get("delivery") or {}).get("kind")) == "formal"
                and (p.get("delivery") or {}).get("scene_id")
                == "t_synth_conditioned.attire_variant_scene"
            ),
        )
        frames = [_scene_frame(page)]
        for _ in range(6):
            if frames[-1]["speaker"] == "host":
                break
            page.locator('[data-testid="message-page"]').focus()
            _press(page, "Enter", wait_ms=120)
            frames.append(_scene_frame(page))
        self.assertEqual(frames[-1]["speaker"], "host")
        self.assertIn(exposure_variant_line, frames[-1]["text"])
        self.assertNotIn(exposure_fallback_line, frames[-1]["text"])

    @covers_requirement(
        "authored-dialogue-availability::locked-topics-remain-readable-refusals-with-accessible-hints"
    )
    @covers_requirement(
        "webclient-contextual-hud::dialogue-choices-appear-centred-over-the-stage-after-the-line-is-fully-read"
    )
    def test_locked_topic_shows_its_hint_and_plays_its_refusal(self):
        """authored-dialogue-locked-ui 3.1: a selectable locked refusal.

        At 1451x790 the kit gatekeeper's second topic is visibly locked: its
        row carries the padlock and a text lock name, never aria-disabled.
        Pointer hover shows the server's canonical requirement hint in a
        tooltip beside the card (the pointer may move onto it), and keyboard
        focus on the row shows it too, wired through aria-describedby. Enter
        submits exactly one explore.talk_scripted for the locked topic; the
        server's refusal plays line by line through the shared player, the
        protected formal body never reaches the page, and the explicit finish
        returns the choices with nothing further submitted.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        host = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % host["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and s.get("dispatch", {}).get("inFlight") is None,
        )
        choices = store_state(page)["panels"]["dialogue"]["choices"]
        locked_choice = next(c for c in choices if c["topic_id"] == SYNTH_LOCKED_TOPIC_ID)
        self.assertEqual(locked_choice["availability"], "locked")
        hint = locked_choice["requirement_hint"]
        self.assertTrue(hint)
        open_dialogue_choices(page)

        card = page.locator('[data-anchor="choices"] [data-testid="dialogue-choices"]')
        picks = card.locator('[data-testid="dialogue-pick"]')
        self.assertEqual(picks.count(), 2)
        locked = picks.nth(1)
        self.assertEqual(locked.get_attribute("data-locked"), "true")
        self.assertIsNone(locked.get_attribute("aria-disabled"))
        self.assertIn("（尚未解鎖）", locked.text_content())
        self.assertNotIn(hint, locked.text_content())
        self.assertTrue(locked.locator('[data-testid="choice-card-lock"]').is_visible())
        tip = card.locator('[data-testid="choice-card-tip"]')
        self.assertEqual(tip.count(), 0)

        # Pointer hover: the hint shows beside the card, inside the viewport,
        # and stays while the pointer moves onto the tooltip.
        locked.hover()
        tip.wait_for(state="visible", timeout=5000)
        self.assertEqual(tip.get_attribute("data-tip-source"), "pointer")
        self.assertEqual(tip.inner_text().strip(), hint)
        # The tooltip and the rows settle (entrance and placement) before the
        # geometry is read: two consecutive frames agree.
        page.wait_for_function(
            """() => new Promise((resolve) => {
              const read = () => {
                const tip = document.querySelector('[data-testid="choice-card-tip"]');
                const row = document.querySelector('[data-testid="dialogue-pick"][data-locked="true"]');
                return tip && row && tip.dataset.placed === 'true'
                  ? `${tip.getBoundingClientRect().top}|${row.getBoundingClientRect().top}`
                  : null;
              };
              const first = read();
              requestAnimationFrame(() => requestAnimationFrame(() => resolve(first !== null && read() === first)));
            })""",
            timeout=5000,
        )
        card_box = card.bounding_box()
        tip_box = tip.bounding_box()
        row_box = locked.bounding_box()
        self.assertGreaterEqual(tip_box["x"], card_box["x"] + card_box["width"])
        self.assertLessEqual(tip_box["x"] + tip_box["width"], 1451)
        self.assertLessEqual(abs(tip_box["y"] - row_box["y"]), 2)
        page.mouse.move(tip_box["x"] + 4, tip_box["y"] + tip_box["height"] / 2, steps=6)
        page.wait_for_timeout(120)
        self.assertTrue(tip.is_visible(), "the tooltip is hoverable")
        page.mouse.move(4, 400)
        tip.wait_for(state="detached", timeout=5000)

        # Keyboard focus: the active locked row shows and describes the hint.
        card.focus()
        _press(page, "ArrowDown")
        self.assertEqual(
            page.evaluate(
                "(id) => document.activeElement.getAttribute('aria-activedescendant') === id",
                locked.get_attribute("id"),
            ),
            True,
        )
        tip.wait_for(state="visible", timeout=5000)
        self.assertEqual(tip.get_attribute("data-tip-source"), "focus")
        described = page.evaluate(
            """(id) => (document.getElementById(id).getAttribute('aria-describedby') || '')
                .split(' ').filter(Boolean)
                .map((ref) => document.getElementById(ref).textContent).join(' ')""",
            locked.get_attribute("id"),
        )
        self.assertEqual(described, hint)
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)
        sent_before = sent_action_count(page)

        # Enter selects the locked topic: its refusal plays, never the body.
        _press(page, "Enter")
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)
        sent = [
            args[0]
            for cmdname, args, _kwargs in outbound_messages(page)
            if cmdname == "ui_action" and args
        ]
        self.assertEqual(sent[-1]["payload"]["topic_id"], SYNTH_LOCKED_TOPIC_ID)
        self._wait_panel(
            page,
            "dialogue",
            lambda p: ((p.get("delivery") or {}).get("kind")) == "refusal",
        )
        frames = [_scene_frame(page)]
        kinds = set()
        for _ in range(10):
            if frames[-1]["choices"]:
                break
            kinds.add((store_state(page)["panels"]["dialogue"].get("delivery") or {}).get("kind"))
            page.locator('[data-testid="message-page"]').focus()
            _press(page, "Enter", wait_ms=120)
            frames.append(_scene_frame(page))
        self.assertEqual(kinds, {"refusal"})
        speakers = [f["speaker"] for f in frames if not f["choices"]]
        self.assertEqual(
            [s for i, s in enumerate(speakers) if i == 0 or s != speakers[i - 1]],
            ["actor", "host", "narration"],
        )
        self.assertTrue(frames[-1]["choices"])
        self.assertNotIn("只有帶著證物的人能過", page.content())
        self.assertTrue(
            page.evaluate(
                "() => document.activeElement === document.querySelector('[data-anchor=\"choices\"] [data-testid=\"dialogue-choices\"]')"
            )
        )
        # Back at the choices: one selection in all, the topic still locked.
        self.assertEqual(sent_action_count(page), sent_before + 1)
        self.assertEqual(picks.nth(1).get_attribute("data-locked"), "true")

    @covers_requirement(
        "webclient-contextual-hud::dialogue-choices-appear-centred-over-the-stage-after-the-line-is-fully-read"
    )
    @covers_requirement(
        "webclient-exit-compass::the-dialogue-screen-s-exits-list-stays-independent-of-the-exploration-root"
    )
    def test_dialogue_exit_row_moves_with_the_committed_exit_payload(self):
        """exploration-exit-compass D9: the dialogue screen's `↦ 移動…` list
        reads the committed exit rows independently of the exploration router
        root (which carries no exit item), so it lists every exit, and an
        enabled exit row submits exactly the exit row's `explore.move`
        payload."""
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        panel = self._live_exploration_panel(page)
        host = panel["interact"][0]
        activate_overview_chip(page, "target-%s" % host["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and s.get("mode") == "dialogue"
            and s.get("dispatch", {}).get("inFlight") is None,
        )
        open_dialogue_choices(page)
        self.assertFalse(
            any(item["key"].startswith("exit-") for item in store_state(page)["rootMenu"]["items"]),
            "the exploration root carries no exit item",
        )
        # ↦ 移動… sits just above ✕ 結束對話.
        _press(page, "End")
        _press(page, "ArrowUp")
        _press(page, "Enter")
        page.wait_for_selector('[data-testid="dialogue-choices"][data-view="exits"]')
        state = store_state(page)
        rows = state["explorationExits"]
        moves = (state["panels"]["exploration"] or {}).get("move") or []
        self.assertEqual(page.locator('[data-testid="dialogue-exit-row"]').count(), len(moves))
        index = next(i for i, row in enumerate(rows) if row.get("enabled"))
        for _ in range(index):
            _press(page, "ArrowDown")
        _press(page, "Enter")
        wait_for_store_state(page, lambda s: sent_action_count(page, "explore.move") == 1)
        envelope = [
            args[0]
            for cmd, args, _kw in outbound_messages(page)
            if cmd == "ui_action" and args and args[0].get("action_id") == "explore.move"
        ][0]
        self.assertEqual(envelope["payload"], rows[index]["payload"])
        self.assertEqual(
            envelope["payload"],
            {"exit_ref": moves[index]["exit_ref"], "current_node": state["panels"]["local_map"]["current_node"]},
        )

    @covers_requirement(
        "webclient-contextual-hud::pointer-open-dialogue-choices-expose-a-local-initial-highlight"
    )
    def test_pointer_opened_choices_highlight_the_first_choice_without_answering(self):
        """webclient-message-typesetting: a conversation opened and read by
        pointer shows its choice list with the first choice highlighted
        through the list's active descendant, and nothing is answered. While
        focus sits elsewhere (the expanded command line) the highlight stays
        visible and still answers nothing; only a deliberate click does."""
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        host = overview_target_with_affordance(page, "explore.talk_open")
        page.click('[data-anchor="presence"] [data-entry-key="target-%s"]' % host["identity"])
        card_row = '[data-anchor="choices"] [data-testid="presence-card"] [data-row-key="talk-open"]'
        page.wait_for_selector(card_row, timeout=15000)
        page.click(card_row)
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        self.assertEqual(sent_action_count(page, "explore.talk_open"), 1)

        # Read the greeting by pointer: each click on the page shows a typing
        # page in full or advances.
        list_selector = '[data-anchor="choices"] [data-testid="dialogue-choices"]'
        for _ in range(60):
            if page.locator(list_selector).count():
                break
            page.click('[data-testid="message-page"]')
            page.wait_for_timeout(150)
        page.wait_for_selector(list_selector, timeout=5000)

        probe = """() => {
          const list = document.querySelector('%s');
          const active = document.getElementById(list.getAttribute('aria-activedescendant'));
          const rows = Array.from(list.querySelectorAll('[role="menuitem"]'));
          const bg = (el) => getComputedStyle(el).backgroundImage + '|' + getComputedStyle(el).borderTopColor;
          return {
            activeIsFirstPick: active === list.querySelector('[data-testid="dialogue-pick"]'),
            activeFlag: active && active.getAttribute('data-active'),
            distinct: rows.length > 1 && bg(active) !== bg(rows[1]),
            listFocused: document.activeElement === list,
          };
        }""" % list_selector
        opened = page.evaluate(probe)
        # Reading by clicks leaves focus on the message page, so the shell's
        # unchanged focus rule hands it to the list; the highlight itself
        # moves no focus (the unfocused case follows below).
        self.assertTrue(opened["listFocused"])
        self.assertTrue(opened["activeIsFirstPick"])
        self.assertEqual(opened["activeFlag"], "true")
        self.assertTrue(opened["distinct"], "the initial highlight must be visible")
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)

        # Focus elsewhere: the list keeps its quiet highlight and answers
        # nothing.
        page.click('[data-testid="command-line-toggle"]')
        page.wait_for_function("() => document.activeElement && document.activeElement.id === 'inputfield'")
        away = page.evaluate(probe)
        self.assertFalse(away["listFocused"])
        self.assertTrue(away["activeIsFirstPick"])
        self.assertTrue(away["distinct"], "the unfocused list must still show where the keys start")
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)

        # A deliberate click answers exactly once.
        page.click('%s [data-testid="dialogue-pick"]' % list_selector)
        wait_for_store_state(page, lambda s: sent_action_count(page, "explore.talk_scripted") == 1, timeout=15000)

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_dialogue_degrades_offline_through_the_command_line(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # The rail's medallion for the bard opens its verb card; 交談
        # opens the conversation, whose choice list carries the free row.
        bard = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % bard["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        result_before_free = (
            store_state(page).get("lastActionResult") or {}
        ).get("requestId")
        # The choice list's free row borrows the command line.
        open_dialogue_choices(page)
        page.click('[data-testid="dialogue-freeform"]')
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": "#inputfield",
                "predicate": (
                    "() => { const f = document.getElementById('inputfield'); "
                    "const a = document.activeElement; "
                    "return !!f && a === f; }"
                ),
                "description": "command-line input field is focused",
            },
        )
        page.keyboard.type("你好，詩人")
        page.keyboard.press("Enter")
        wait_for_store_state(
            page,
            lambda state: (
                (state.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before_free)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 1)

    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow"
    )
    def test_cancelled_freeform_dialogue_cannot_capture_a_later_command(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Open free-form dialogue but cancel with Escape without sending.
        # The rail's medallion for the bard opens its verb card; 交談
        # opens the conversation, whose choice list carries the free row.
        bard = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % bard["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        open_dialogue_choices(page)
        page.click('[data-testid="dialogue-freeform"]')
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": "#inputfield",
                "predicate": (
                    "() => { const f = document.getElementById('inputfield'); "
                    "const a = document.activeElement; "
                    "return !!f && a === f; }"
                ),
                "description": "command-line input field is focused",
            },
        )
        page.keyboard.type("話到嘴邊又吞了回去")
        page.keyboard.press("Escape")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": '[data-testid="dialogue-pick"], [data-testid="dialogue-freeform"]',
                "predicate": (
                    "() => { const a = document.querySelector('[data-anchor=\"command-line\"]'); "
                    "const d = document.querySelector('[data-testid=\"command-line\"]'); "
                    "const collapsed = !!a && a.getAttribute('data-expanded') === 'false' && !!d; "
                    "const list = document.querySelector('[data-anchor=\"choices\"] [data-testid=\"dialogue-choices\"]'); "
                    "return collapsed && !!list && document.activeElement === list; }"
                ),
                # webclient-dialogue-choices-overlay: in dialogue the focus
                # home is the shown choice list, never the hidden dock.
                "description": "command line collapsed and the choice list focused",
            },
        )

        # Expand the command line with `/` and send an ordinary command: it
        # must travel as text, never as explore.talk_freeform speech to the
        # previously selected NPC.
        page.keyboard.press("/")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": "#inputfield",
                "predicate": (
                    "() => { const f = document.getElementById('inputfield'); "
                    "const a = document.activeElement; "
                    "return !!f && a === f; }"
                ),
                "description": "command-line input field is focused",
            },
        )
        before_len = narrative_log_length(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and narrative_log_length(page) > before_len,
        )
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 0)
        # The command was sent through the text path.
        text_sends = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "text"
        ]
        self.assertTrue(
            any("look" in str(item) for item in text_sends),
            "the ordinary command must travel through the text transport",
        )

    @covers_requirement("webclient-exploration-menu::explore-engage-delegates-to-the-existing-engage-contract")
    @covers_requirement("webclient-frame-resolution::teardown-resets-the-stack-to-the-mode-root-from-one-decision-point")
    @covers_requirement(
        "webclient-art-panel::combat-portrait-references-and-catalog-are-committed-coherently"
    )
    def test_engage_transitions_to_combat(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        goblin = overview_target_with_affordance(page, "explore.engage")
        activate_overview_chip(page, "target-%s" % goblin["identity"])
        _press(page, "Enter")  # 戰鬥 (engage)
        wait_for_store_state(
            page,
            lambda s: s.get("mode") == "combat",
            timeout=30000,
        )
        self.assertEqual(store_state(page)["mode"], "combat")
        self.assertEqual(sent_action_count(page, "explore.engage"), 1)
        self.assertEqual(
            page.locator("#action-dock").get_attribute("data-mode"),
            "combat",
        )
        # Teardown (webclient-declarative-frame-stack): the mode switch
        # replaced the whole exploration stack (root -> interact -> target)
        # with exactly one combat root frame.
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            1,
            "the combat adoption did not collapse the frame stack to one root",
        )

        # Assert the first engaged combat catalog contains monster_anon mask,
        # no standing SVG figure, and no tier-keyed imagery.
        art_panel = store_state(page).get("panels", {}).get("art", {})
        catalog = art_panel.get("portrait_catalog", {})
        goblin_pk = str(goblin["identity"])
        self.assertIn(goblin_pk, catalog)
        goblin_entry = catalog[goblin_pk]
        artwork = goblin_entry["artwork"]
        # The admitted entry's descriptor exposes no real candidate here and
        # carries the committed ``monster_anon`` alpha terminal.
        self.assertEqual(
            [a["type"] for a in artwork["attempts"] if a["type"] == "image"], []
        )
        self.assertEqual(artwork["terminal"]["kind"], "alpha_mask")
        self.assertIn("monster_anon", artwork["terminal"]["resource"]["url"])

        # Ensure standing humanoid SVG is absent from the stage
        svg_count = page.locator('[data-anchor="actor-right"] [data-testid="reference-artwork"] svg').count()
        self.assertEqual(svg_count, 0, "legacy standing humanoid SVG must not be rendered")

    @covers_requirement(
        "webclient-presence-rail::the-presence-rail-and-verb-card-are-verified-in-the-live-client-at-two-viewports"
    )
    def test_presence_rail_and_verb_card_hold_at_both_reference_viewports(self):
        """exploration-presence-rail: geometry and the standee handover at
        1451x790 and 1920x1080.

        The rail sits above the band without overlapping the local-map
        island column, the verb card is centred and fully visible, and 交談
        hands the very same standee element on to the dialogue surface.
        """
        for viewport in ((1451, 790), (1920, 1080)):
            page = self.logged_in_page(viewport)
            self._wait_exploration_available(page)
            host = overview_target_with_affordance(page, "explore.talk_open")
            page.wait_for_selector(
                '[data-anchor="presence"] [data-entry-key="target-%s"]' % host["identity"],
                state="attached",
            )
            page.wait_for_timeout(300)
            geometry = page.evaluate(
                """() => {
                  const box = (el) => {
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return { left: r.left, right: r.right, top: r.top, bottom: r.bottom };
                  };
                  return {
                    rail: box(document.querySelector('[data-anchor="presence"] [data-testid="presence-rail"]')),
                    band: box(document.querySelector('[data-testid="stage-band"]')),
                    island: box(document.querySelector('[data-testid="local-map"]')),
                    width: window.innerWidth,
                  };
                }"""
            )
            self.assertLessEqual(geometry["rail"]["bottom"], geometry["band"]["top"] + 1, str(viewport))
            self.assertGreater(geometry["rail"]["left"], geometry["width"] / 2, str(viewport))
            if geometry["island"]:
                overlaps = not (
                    geometry["rail"]["right"] <= geometry["island"]["left"]
                    or geometry["island"]["right"] <= geometry["rail"]["left"]
                    or geometry["rail"]["bottom"] <= geometry["island"]["top"]
                    or geometry["island"]["bottom"] <= geometry["rail"]["top"]
                )
                self.assertFalse(overlaps, "the rail overlaps the island column at %s" % (viewport,))

            activate_overview_chip(page, "target-%s" % host["identity"])
            page.wait_for_selector('[data-anchor="choices"] [data-testid="presence-card"]')
            page.wait_for_timeout(200)
            card = page.evaluate(
                """() => {
                  const r = document.querySelector('[data-anchor="choices"] [data-testid="presence-card"]')
                    .getBoundingClientRect();
                  return { left: r.left, right: r.right, top: r.top, bottom: r.bottom,
                           width: window.innerWidth, height: window.innerHeight };
                }"""
            )
            self.assertGreaterEqual(card["left"], 0, str(viewport))
            self.assertLessEqual(card["right"], card["width"], str(viewport))
            self.assertGreaterEqual(card["top"], 0, str(viewport))
            self.assertLessEqual(card["bottom"], card["height"], str(viewport))
            self.assertAlmostEqual((card["left"] + card["right"]) / 2, card["width"] / 2, delta=2)

            standee = '[data-anchor="actor-right"] [data-testid="stage-actor"]'
            page.wait_for_selector(standee)
            page.evaluate("(sel) => { document.querySelector(sel).__presenceMark = true; }", standee)
            _press(page, "Enter")  # 交談 -> explore.talk_open
            self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
            wait_for_store_state(page, lambda s: s.get("mode") == "dialogue")
            page.wait_for_selector(standee)
            self.assertTrue(
                page.evaluate("(sel) => document.querySelector(sel).__presenceMark === true", standee),
                "the standee was remounted between the card and the dialogue at %s" % (viewport,),
            )
            # Leave the conversation so the next viewport starts in exploration.
            open_dialogue_choices(page)
            page.click('[data-testid="dialogue-exit"]')
            wait_for_store_state(page, lambda s: s.get("mode") == "exploration")
            page.close()

    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-session-is-deterministic-core-only-character-state"
    )
    def test_unlock_during_a_scene_shows_one_deferred_notice(self):
        """authored-dialogue-unread-notices 4.1: a deferred, single unlock notice.

        The gatekeeper opens with its open topic unread and its second topic
        locked (lock, no pip). While the open topic's scene plays, two GM
        console grants commit the required items through the canonical
        inventory writer; the second grant unlocks the topic and its committed
        refresh claims ONE batch. Nothing shows until the scene's explicit
        finish returns the choices; then one status toast names the topic
        without taking focus, and its row carries the unread pip. A relock and
        reopen shows no second notice, and a reload keeps the pip with no
        replayed notice.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        character = _gm_character(page)
        host = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % host["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and s.get("dispatch", {}).get("inFlight") is None,
        )
        open_dialogue_choices(page)
        card = page.locator('[data-anchor="choices"] [data-testid="dialogue-choices"]')
        picks = card.locator('[data-testid="dialogue-pick"]')
        self.assertEqual(picks.nth(0).get_attribute("data-unread"), "true")
        self.assertIn("（未讀）", picks.nth(0).text_content())
        self.assertEqual(picks.nth(1).get_attribute("data-locked"), "true")
        self.assertIsNone(picks.nth(1).get_attribute("data-unread"))
        self.assertEqual(_unlock_toasts(page), [], "a first visit is not an unlock")

        # Select the open topic: its scene starts playing.
        card.focus()
        _press(page, "Enter")
        self._wait_panel(
            page,
            "dialogue",
            lambda p: ((p.get("delivery") or {}).get("kind")) == "formal",
        )
        self.assertFalse(_scene_frame(page)["choices"])

        # The qualification commits mid-scene through the canonical writer.
        for item_key in SYNTH_LOCKED_TOPIC_ITEM_KEYS:
            response = _gm_console(
                page, "give_item", {"target": character, "key": item_key, "quantity": 1}
            )
            self.assertEqual(response["status"], 200, response["body"])
        wait_for_store_state(
            page,
            lambda s: (s.get("dialogueReading") or {}).get("unlockPending") == 1,
        )
        self.assertEqual(_unlock_toasts(page), [], "deferred while the scene plays")
        self.assertFalse(_scene_frame(page)["choices"])

        # Read to the end and give the explicit finish.
        for _ in range(12):
            if _scene_frame(page)["choices"]:
                break
            page.locator('[data-testid="message-page"]').focus()
            _press(page, "Enter", wait_ms=150)
        self.assertTrue(_scene_frame(page)["choices"])
        page.wait_for_selector(
            '[data-testid="feedback-toast-queue"] [data-tone="unlock"]', timeout=10000
        )
        toasts = _unlock_toasts(page)
        self.assertEqual(len(toasts), 1)
        self.assertIn("霧門後", toasts[0])
        self.assertTrue(
            page.evaluate(
                "() => document.activeElement === document.querySelector('[data-anchor=\"choices\"] [data-testid=\"dialogue-choices\"]')"
            ),
            "the notice never takes focus",
        )
        self.assertEqual(
            page.locator('[data-testid="feedback-toast-queue"] [data-tone="unlock"]').get_attribute("role"),
            "status",
        )
        passage = card.locator(f'[data-testid="dialogue-pick"][data-row-key="dlg-topic-{SYNTH_LOCKED_TOPIC_ID}"]')
        self.assertEqual(passage.get_attribute("data-unread"), "true")
        self.assertIsNone(passage.get_attribute("data-locked"))

        # Relock then reopen: the topic stays unread and announces nothing.
        key = SYNTH_LOCKED_TOPIC_ITEM_KEYS[0]
        response = _gm_console(page, "take_item", {"target": character, "key": key, "quantity": 1})
        self.assertEqual(response["status"], 200, response["body"])
        self._wait_panel(
            page,
            "dialogue",
            lambda p: any(
                c["topic_id"] == SYNTH_LOCKED_TOPIC_ID and c["availability"] == "locked"
                for c in p.get("choices") or []
            ),
        )
        response = _gm_console(page, "give_item", {"target": character, "key": key, "quantity": 1})
        self.assertEqual(response["status"], 200, response["body"])
        self._wait_panel(
            page,
            "dialogue",
            lambda p: any(
                c["topic_id"] == SYNTH_LOCKED_TOPIC_ID and c["availability"] == "open" and c["unread"]
                for c in p.get("choices") or []
            ),
        )
        page.wait_for_timeout(600)
        self.assertEqual((store_state(page).get("dialogueReading") or {}).get("unlockPending"), 0)
        self.assertEqual(len(_unlock_toasts(page)), 1, "no second notice on reopen")

        # Reload: the durable pip stays, no notice is replayed.
        page.reload()
        wait_for_shell_active(page)
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        self.assertIsNone(store_state(page)["panels"]["dialogue"]["unlock_batch"])
        open_dialogue_choices(page)
        passage = page.locator(
            f'[data-anchor="choices"] [data-testid="dialogue-pick"][data-row-key="dlg-topic-{SYNTH_LOCKED_TOPIC_ID}"]'
        )
        self.assertEqual(passage.get_attribute("data-unread"), "true")
        page.wait_for_timeout(600)
        self.assertEqual(_unlock_toasts(page), [])
