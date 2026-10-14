"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): focus and stack-loss resilience across committed re-resolution, the suggestions frame, and reconnect without replay.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    CARD_SELECTOR,
    SUGGESTIONS_CARD_SELECTOR,
    WAIT_CARD_SELECTOR,
    activate_card_row,
    activate_first_compass_exit,
    activate_presence_entry,
    card_row_keys,
    compass_target_refs,
    activate_overview_chip,
    fixture_home_node_id,
    inject_update,
    install_outbound_recorder,
    open_dialogue_choices,
    open_verb_card,
    outbound_messages,
    presence_entry_keys,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


# The methods that need the synthetic companion lineup (a committed four-slot
# party of present LLMNPCs). The companion-focus journey additionally opts into
# the portrait branch's admitted media, so the reused figure is asserted against
# loaded art rather than a placeholder.
COMPANION_LINEUP_METHODS = (
    "test_companion_lineup_dialogue_geometry_and_real_possession",
    "test_exploration_companion_focus_reuses_the_lineup_figure",
)
COMPANION_FOCUS_METHOD = "test_exploration_companion_focus_reuses_the_lineup_figure"


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
        if self._testMethodName in COMPANION_LINEUP_METHODS:
            runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "1"
            runtime.env["ELOSERN_BROWSER_COMPANION_LINEUP"] = "1"
        if self._testMethodName == COMPANION_FOCUS_METHOD:
            runtime.env["ELOSERN_BROWSER_EXPLORATION_PORTRAITS"] = "1"

        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def test_companion_lineup_dialogue_geometry_and_real_possession(self):
        page = self.logged_in_page()
        page.set_viewport_size({"width": 1451, "height": 790})
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self._wait_panel(page, "party", lambda p: p.get("available") and len(p["slots"]) == 4)
        state = store_state(page)
        rows = state["panels"]["party"]["slots"]
        player_id = int(state["panels"]["status"]["actor"]["identity"])
        owner_roster_row = next(row for row in state["panels"]["roster"]["characters"] if row["current"])
        target_id = rows[1]["identity"]
        expected = [player_id, *[row["identity"] for row in rows]]
        page.wait_for_selector('[data-testid="companion-figure"]')

        def identities():
            return page.locator('[data-testid="companion-figure"]').evaluate_all(
                "(els) => els.map(el => Number(el.dataset.identity))"
            )

        self.assertEqual(identities(), expected)
        host_id = self._live_exploration_panel(page)["interact"][0]["identity"]
        activate_overview_chip(page, f"target-{host_id}")
        _press(page, "Enter")
        self._wait_panel(page, "dialogue", lambda p: p.get("available"))
        open_dialogue_choices(page)
        page.evaluate("document.fonts.ready")
        boxes = page.evaluate("""() => {
          const rect = el => { const r = el.getBoundingClientRect(); return {left:r.left,right:r.right,top:r.top,bottom:r.bottom}; };
          const figures = [...document.querySelectorAll('[data-testid="companion-figure"]')].map(rect);
          const choices = rect(document.querySelector('[data-testid="dialogue-choices"]'));
          const foes = [...document.querySelectorAll('[data-testid="foe-slot"]')].map(rect);
          return {figures, choices, foes, width:innerWidth};
        }""")
        def intersects(a, b):
            return a["left"] < b["right"] and b["left"] < a["right"] and a["top"] < b["bottom"] and b["top"] < a["bottom"]
        for box in boxes["figures"]:
            self.assertGreaterEqual(box["left"], -1, boxes)
            self.assertLessEqual(box["right"], boxes["width"] / 2 + 1, boxes)
            self.assertFalse(intersects(box, boxes["choices"]), boxes)
            for foe in boxes["foes"]:
                self.assertFalse(intersects(box, foe), boxes)
        page.locator('[data-testid="dialogue-exit"]').click()
        wait_for_store_state(page, lambda s: s.get("mode") == "exploration")
        page.evaluate("window.__elosernBridge.store.openHudDrawer('status')")
        page.locator('[data-testid="character-status-drawer__open-party"]').click()
        page.locator(f'[data-testid="party-drawer__row-{target_id}"] [data-testid="party-drawer__possess-btn"]').click()
        self.assertEqual(sent_action_count(page, "explore.possess"), 1)
        self._wait_panel(page, "possession_banner", lambda p: p.get("available"))
        swapped = [target_id, rows[0]["identity"], player_id, rows[2]["identity"], rows[3]["identity"]]
        page.wait_for_function("(ids) => [...document.querySelectorAll('[data-testid=\"companion-figure\"]')].map(el=>Number(el.dataset.identity)).join(',') === ids.join(',')", arg=swapped)
        self.assertEqual(identities(), swapped)
        self.assertEqual(len(store_state(page)["panels"]["party"]["slots"]), 4)
        possessed_roster = store_state(page)["panels"]["roster"]
        self.assertTrue(possessed_roster["available"])
        self.assertEqual(next(row for row in possessed_roster["characters"] if row["current"]), owner_roster_row)
        page.evaluate("window.__elosernBridge.store.openHudDrawer('party')")
        page.locator('[data-testid="party-drawer__release-btn"]').click()
        self.assertEqual(sent_action_count(page, "explore.possess_release"), 1)
        wait_for_store_state(page, lambda s: s["panels"]["status"]["actor"]["identity"] == str(player_id))
        self.assertEqual(identities(), expected)

    @covers_requirement(
        "webclient-presence-rail::the-person-focus-verb-card-is-client-local-and-replaces-the-verb-popover"
    )
    @covers_requirement(
        "webclient-contextual-hud::companion-standing-portraits-line-up-behind-the-controlled-character-in-the-actor-left-anchor"
    )
    def test_exploration_companion_focus_reuses_the_lineup_figure(self):
        """reuse-lineup-person-focus 4.1 on the live client at 1451x790.

        The committed four-slot party and its admitted portrait (the portrait
        branch), read from the ACTUAL exploration/art/party packets: opening a
        rendered companion's verb card from its real medallion — and from the
        overflow card — sends nothing and pushes no frame, keeps exactly one
        representation of that identity (no actor-right stage actor), lights the
        existing actor-left figure above every baseline with its loaded media and
        its byte-identical box, restores the current baseline on 返回, transfers
        representation both ways when the committed lineup changes (finishing a
        leave the transfer overtakes), and hands the companion over to dialogue
        once, still represented once.
        """
        # FULL motion on purpose: the rest of the suite runs at `off` so no
        # journey races an animation, but this one has to prove the DOM counts
        # while the real CSS phases run — the representation transfer must skip
        # its own leave phase, and a leave the transfer overtakes must be
        # finished rather than painted beside the left figure.
        page = self.logged_in_page((1451, 790), motion_level="full")
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self._wait_panel(page, "party", lambda p: p.get("available") and len(p["slots"]) == 4)
        state = store_state(page)
        rows = state["panels"]["party"]["slots"]
        catalog = state["panels"]["art"]["portrait_catalog"]
        present = {row["identity"] for row in self._live_exploration_panel(page)["interact"]}
        present_rows = [row for row in rows if row["identity"] in present]
        self.assertTrue(present_rows, "a committed party companion must be present as an interact target")
        # Prefer the companion the fixture admitted a portrait for, so the
        # reused figure is asserted against loaded media.
        member = next((row for row in present_rows if row.get("portrait_ref")), present_rows[0])
        member_id = member["identity"]
        figure_selector = '[data-testid="companion-figure"][data-identity="%s"]' % member_id
        right_selector = '[data-testid="anchor-actor-right"] [data-testid="stage-actor"]'
        page.wait_for_selector(figure_selector, timeout=15000)

        def stage() -> dict:
            """The committed stage: each actor-left figure's identity, props, z,
            rounded box and portrait image, and the actor-right stage actors."""
            return page.evaluate(
                """(rightSelector) => {
                  const box = (el) => {
                    const r = el.getBoundingClientRect();
                    return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)];
                  };
                  return {
                    figures: Array.from(document.querySelectorAll('[data-testid="companion-figure"]')).map((el) => {
                      const actor = el.querySelector('[data-testid="stage-actor"]');
                      const portrait = el.querySelector('img:not(.reference-artwork__mask-probe)');
                      return {
                        identity: el.dataset.identity,
                        controlled: el.dataset.controlled === 'true',
                        z: Number(el.style.zIndex),
                        speaking: actor.getAttribute('data-speaking'),
                        beat: actor.getAttribute('data-beat'),
                        box: box(el),
                        image: portrait ? {
                          src: portrait.getAttribute('src'),
                          complete: portrait.complete,
                          naturalWidth: portrait.naturalWidth,
                        } : null,
                      };
                    }),
                    right: Array.from(document.querySelectorAll(rightSelector))
                      .map((el) => el.getAttribute('data-identity')),
                  };
                }""",
                right_selector,
            )

        def one(state_now: dict, identity) -> dict:
            matches = [item for item in state_now["figures"] if item["identity"] == str(identity)]
            self.assertEqual(len(matches), 1, state_now["figures"])
            return matches[0]

        def party_panel(subset) -> dict:
            committed = store_state(page)["panels"]["party"]
            return {
                "schema_version": committed["schema_version"],
                "available": True,
                "general_quota": committed["general_quota"],
                "slots": list(subset),
            }

        def slots_of(state_now: dict) -> int:
            return len(((state_now.get("panels") or {}).get("party") or {}).get("slots") or [])

        def wait_for_right(identities, timeout: int = 15000) -> None:
            """Wait until actor-right's stage actors are exactly `identities`.

            A store wait alone would not prove the DOM: at full motion a leave
            is still painted after the commit that removes it, so every leg
            settles the anchor before it asserts a count.
            """
            page.wait_for_function(
                "(args) => { const [selector, expected] = args;"
                " const actual = Array.from(document.querySelectorAll(selector))"
                "   .map((el) => el.getAttribute('data-identity')).sort();"
                " return JSON.stringify(actual) === JSON.stringify(expected.slice().sort()); }",
                arg=[right_selector, [str(identity) for identity in identities]],
                timeout=timeout,
            )

        def wait_for_figure_gone(identity, timeout: int = 15000) -> None:
            page.wait_for_function(
                "(args) => !document.querySelector(args[0].replace('%s', args[1]))",
                arg=['[data-testid="companion-figure"][data-identity="%s"]', str(identity)],
                timeout=timeout,
            )

        before = stage()
        wait_for_right([], timeout=5000)
        self.assertEqual(before["right"], [], "the exploration root stands no actor-right stage actor")

        # --- the actual medallion: client-local, singular, lit, unmoved ------ #
        open_verb_card(page, member_id)
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), 1)
        self.assertEqual(sent_action_count(page), 0, "opening the card dispatches nothing")
        wait_for_right([])
        opened = stage()
        self.assertEqual(opened["right"], [], "a rendered companion gets no actor-right copy")
        selected = one(opened, member_id)
        self.assertFalse(selected["controlled"])
        self.assertEqual(selected["speaking"], "true")
        self.assertEqual(selected["z"], 6, "the selected companion takes the focus z")
        for other in opened["figures"]:
            if other["identity"] == str(member_id):
                continue
            self.assertLess(other["z"], selected["z"], other)
            if not other["controlled"]:
                self.assertEqual(other["speaking"], "false", "the other companions keep the listener dim")
        controlled = [item for item in opened["figures"] if item["controlled"]]
        self.assertEqual(len(controlled), 1, "exactly one controlled front figure")
        self.assertIsNone(controlled[0]["beat"], "the controlled figure keeps its own props")
        for earlier in before["figures"]:
            self.assertEqual(
                one(opened, earlier["identity"])["box"],
                earlier["box"],
                "focus changes no figure's box",
            )
        # The admitted portrait branch: the reused figure really loaded media.
        self.assertIsNotNone(member.get("portrait_ref"), "the portrait branch admits a reference")
        entry = catalog[member["portrait_ref"]]
        self.assertTrue(entry["url"].startswith("/art/"), entry)
        self.assertEqual(selected["image"]["src"], entry["url"], "the figure renders its admitted crop")
        self.assertTrue(selected["image"]["complete"])
        self.assertGreater(selected["image"]["naturalWidth"], 0)

        activate_card_row(page, "back")
        wait_for_store_state(page, lambda s: s.get("presenceCard") is None)
        wait_for_right([])
        closed = stage()
        self.assertEqual(closed["right"], [], "closing restores the baseline with no right-side figure")
        self.assertEqual(one(closed, member_id)["z"], one(before, member_id)["z"])
        self.assertEqual(one(closed, member_id)["speaking"], "false")
        self.assertEqual(one(closed, member_id)["box"], one(before, member_id)["box"])
        self.assertEqual(sent_action_count(page), 0)

        # --- the overflow card: the same membership rule for a folded entry -- #
        self.assertIn("presence-more", presence_entry_keys(page), "the fixture crowd must fold entries")
        activate_presence_entry(page, "presence-more")
        page.wait_for_selector(CARD_SELECTOR, timeout=15000)
        folded = next(
            (key for key in card_row_keys(page) if key.startswith("target-")),
            None,
        )
        self.assertIsNotNone(folded, "the overflow card must list an interact target")
        folded_id = int(folded.split("-", 1)[1])
        activate_card_row(page, folded)
        wait_for_store_state(page, lambda s: (s.get("presenceCard") or {}).get("identity") == folded_id)
        wait_for_right([] if folded_id in {row["identity"] for row in rows} else [folded_id])
        overflow = stage()
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), 1)
        self.assertEqual(sent_action_count(page), 0)
        if folded_id in {row["identity"] for row in rows}:
            self.assertEqual(overflow["right"], [], "a folded lineup entry reuses its figure too")
            self.assertEqual(one(overflow, folded_id)["speaking"], "true")
        else:
            self.assertEqual(overflow["right"], [str(folded_id)], "a non-lineup entry keeps actor-right")
            for item in overflow["figures"]:
                if not item["controlled"]:
                    self.assertEqual(item["speaking"], "false", "no unrelated companion gains emphasis")
        activate_card_row(page, "back")
        wait_for_store_state(page, lambda s: s.get("presenceCard") is None)
        wait_for_right([])

        # --- membership decides representation, both ways ------------------- #
        other_rows = [row for row in rows if row["identity"] != member_id]
        open_verb_card(page, member_id)
        inject_update(page, {"party": party_panel(other_rows)})
        wait_for_store_state(page, lambda s: slots_of(s) == len(other_rows))
        wait_for_figure_gone(member_id)
        wait_for_right([member_id])
        transferred_out = stage()
        self.assertEqual(
            [item for item in transferred_out["figures"] if item["identity"] == str(member_id)],
            [],
            "an unrendered identity leaves no left figure",
        )
        self.assertEqual(
            transferred_out["right"], [str(member_id)],
            "the surviving target takes the ordinary actor-right standee",
        )
        inject_update(page, {"party": party_panel(rows)})
        wait_for_store_state(page, lambda s: slots_of(s) == len(rows))
        page.wait_for_selector(figure_selector, timeout=15000)
        wait_for_right([])
        transferred_in = stage()
        self.assertEqual(transferred_in["right"], [], "the transfer back leaves no right-side copy")
        self.assertEqual(one(transferred_in, member_id)["z"], 6)
        self.assertEqual(one(transferred_in, member_id)["speaking"], "true")

        # --- a leave the transfer overtakes paints no second figure --------- #
        inject_update(page, {"party": party_panel(other_rows)})
        wait_for_store_state(page, lambda s: slots_of(s) == len(other_rows))
        wait_for_figure_gone(member_id)
        wait_for_right([member_id])
        self.assertEqual(stage()["right"], [str(member_id)])
        # Close the card, then commit the membership change that overtakes its
        # leave, and read the anchor — all inside ONE task: the standee's CSS
        # leave (350ms at full motion) is provably still running when the left
        # figure is drawn, so the empty anchor afterwards can only come from
        # finishing that copy rather than from the transition ending.
        overtaken = page.evaluate(
            """async (args) => {
              const [rightSelector, panel, identity] = args;
              document
                .querySelector('[data-anchor="choices"] [data-testid="presence-card"] [data-row-key="back"]')
                .click();
              const nextFrame = () =>
                new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
              await nextFrame();
              const leaving = Array.from(document.querySelectorAll(rightSelector))
                .map((el) => el.getAttribute('data-identity'));
              const s = window.__elosernBridge.store.view;
              const envelope = {
                protocol_version: 1,
                presentation_epoch: s.epoch,
                revision: s.revision + 1,
                mode: s.mode,
                layout_version: s.layoutVersion ?? 1,
                panels: { party: panel },
                server_time: s.serverTime,
              };
              const result = window.__elosernBridge.store.receive(s.generation, 'ui_update', [envelope], {});
              await nextFrame();
              return {
                leaving,
                accepted: !!result.accepted,
                left: !!document.querySelector(
                  '[data-testid="companion-figure"][data-identity="' + identity + '"]'
                ),
                after: Array.from(document.querySelectorAll(rightSelector))
                  .map((el) => el.getAttribute('data-identity')),
              };
            }""",
            [right_selector, party_panel(rows), str(member_id)],
        )
        self.assertEqual(overtaken["leaving"], [str(member_id)], "the standee is still leaving")
        self.assertTrue(overtaken["accepted"], "the membership update must be admitted")
        self.assertTrue(overtaken["left"], "the left figure is drawn in the same task")
        self.assertEqual(
            overtaken["after"],
            [],
            "the overtaken leave is finished in the same task",
        )
        wait_for_store_state(page, lambda s: slots_of(s) == len(rows))
        open_verb_card(page, member_id)
        wait_for_right([])
        reopened = stage()
        self.assertEqual(reopened["right"], [], "reopening stays singular")
        self.assertEqual(one(reopened, member_id)["z"], 6)

        # --- the talk handover --------------------------------------------- #
        activate_card_row(page, "talk-open")
        self.assertEqual(sent_action_count(page, "explore.talk_open"), 1)
        inject_update(
            page,
            {
                "dialogue": {
                    "schema_version": 2,
                    "available": True,
                    "kind": "dialogue",
                    "host": {
                        "identity": member_id,
                        "display_name": member["display_name"],
                        "portrait_ref": member.get("portrait_ref"),
                    },
                    "bond_stage": None,
                    "line": "……",
                    "choices": [],
                },
            },
            mode="dialogue",
        )
        wait_for_store_state(page, lambda s: s.get("mode") == "dialogue")
        wait_for_right([])
        handed = stage()
        self.assertEqual(handed["right"], [], "the lineup host keeps actor-right empty in dialogue")
        self.assertEqual(one(handed, member_id)["z"], 6, "the existing host speaker signal owns z")
        self.assertEqual(one(handed, member_id)["speaking"], "true")
        self.assertEqual(page.locator(CARD_SELECTOR).count(), 0, "the mode change closes the card")
        self.assertEqual(sent_action_count(page), 1)
        page.close()

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

    @covers_requirement(
        "webclient-room-actions::the-exploration-screen-roots-at-the-compass-the-rail-and-room-actions"
    )
    def test_escape_from_character_panel_returns_keyboard_to_the_exploration_root(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self.assertIn("character", store_state(page)["panels"])

        # The desktop redesign re-homed the character surface into the top
        # navigation (webclient-desktop-shell, acd3790: the dock root is the
        # capability-driven [move, look, interact, wait, suggestions];
        # 角色狀態 opens from the DesktopNavigation entry — the nav click
        # routes the same store confirm the dock row carried).
        page.locator('.desktop-navigation button', has_text="角色狀態").click()
        self.assertEqual(
            page.evaluate("(() => { const s = window.__elosernBridge.store.view; return s && s.activeSubDock; })()"),
            "character",
            "the character panel must own the action dock",
        )
        _press(page, "Escape")
        page.wait_for_timeout(120)
        self.assertEqual(
            page.evaluate("(() => { const s = window.__elosernBridge.store.view; return s && s.activeSubDock; })()"),
            None,
            "Escape must leave the character panel",
        )

        activate_first_compass_exit(page)  # the compass's first exit
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True and p["current_node"] != fixture_home_node_id(),
        )
        self.assertEqual(
            sent_action_count(page, "explore.move"),
            1,
            "after Character -> Escape the exploration root must accept keyboard input",
        )

    # --- declarative-frame-stack browser verification (task 5.1) -----------
    #
    # These methods verify the shipped stack (router + store + dock DOM)
    # against COMMITTED state the live fixture cannot arrange: a fabricated
    # `ui_update` through the bridge's `store.receive` is the same reducer
    # entry the real transport feeds (the options-surface file pioneered the
    # seam), so the stack settles exactly as it does after a server push —
    # identity loss, panel withdrawal, and suggestions status flips included.

    def _inject_panels(self, page, panels: dict) -> dict:
        """Commit one schema-valid ``ui_update`` for ``panels`` at the
        current revision + 1. The envelope is assembled IN-PAGE from the
        fresh view so no real push can slip a revision between read and
        receive; the injected revision then back-stops the next real push
        (``not_newer``) until the server's revision passes it."""
        return page.evaluate(
            """(panels) => {
              const s = window.__elosernBridge.store.view;
              const envelope = {
                protocol_version: 1,
                presentation_epoch: s.epoch,
                revision: s.revision + 1,
                mode: s.mode,
                layout_version: s.layoutVersion ?? 1,
                panels,
                server_time: s.serverTime,
              };
              return window.__elosernBridge.store.receive(
                s.generation, 'ui_update', [envelope], {});
            }""",
            panels,
        )

    @staticmethod
    def _fabricated_exploration_panel(*, move=(), interact=(), objects=()) -> dict:
        """A schema-valid available exploration panel carrying exactly the
        named rows — the fabricated room a real commit would produce."""
        return {
            "schema_version": 4,
            "available": True,
            "kind": "exploration",
            "move": list(move),
            "look": {
                "room": {"identity": 94001, "display_name": "巡邏室", "room": True},
                "entities": [],
                "objects": list(objects),
            },
            "interact": list(interact),
            "character": {"available": True},
            "quests": {"available": False},
            "inventory": {"available": False},
        }

    @staticmethod
    def _move_row(exit_ref: str, label: str) -> dict:
        return {
            "exit_ref": exit_ref,
            "label": label,
            "destination": "grid:altoria:3:3",
            "enabled": True,
            "disabled_reason": None,
        }

    @staticmethod
    def _object(identity: int, name: str) -> dict:
        return {"identity": identity, "display_name": name}

    @staticmethod
    def _target(identity: int, name: str) -> dict:
        return {
            "identity": identity,
            "display_name": name,
            "portrait_ref": None,
            "affordances": [
                {
                    "kind": "action",
                    "action_id": "explore.engage",
                    "label": "戰鬥",
                    "enabled": True,
                    "disabled_reason": None,
                }
            ],
        }

    def _depth(self, page) -> int:
        return page.evaluate("() => window.__elosernBridge.router.depth()")

    def _pane_keys(self, page) -> list[str]:
        """Every rendered row identity inside the dock (the pane's rows
        carry the `data-item-key` seam; the legacy suggestion cards render
        without one)."""
        return page.evaluate(
            "() => Array.from("
            "document.querySelectorAll('#action-dock [data-item-key]'))"
            ".map((el) => el.getAttribute('data-item-key'))"
        )

    @staticmethod
    def _ready_context(*cards) -> dict:
        """A ready suggestions envelope carrying ``cards`` (each
        ``(action_code, label, params)``), on an affordance-free panel."""
        return {
            "context_actions": {
                "schema_version": 5,
                "available": True,
                "kind": "exploration",
                "affordances": [],
                "suggestions": {
                    "status": "ready",
                    "cards": [
                        {"kind": "known_action", "action_code": code, "label": label, "params": params}
                        for code, label, params in cards
                    ],
                },
            },
        }

    def _card_active_label(self, page) -> str | None:
        """The label of the suggestions card's active row."""
        return page.evaluate(
            """(selector) => {
              const card = document.querySelector(selector);
              const id = card && card.getAttribute('aria-activedescendant');
              const row = id ? document.getElementById(id) : null;
              const label = row && row.querySelector('.choice-card__label');
              return label ? label.textContent : null;
            }""",
            SUGGESTIONS_CARD_SELECTOR,
        )

    @covers_requirement("webclient-frame-resolution::focus-tracks-the-item-key-across-re-resolution")
    def test_focus_follows_the_item_key_across_committed_re_resolution(self):
        """The suggestions card (exploration-room-actions) keeps its active
        row on the same card across committed updates: a commit that
        REORDERS the cards keeps the active row on that card at its new
        index, and a commit that drops it lands on a surviving row — never on
        a frozen copy's old row. Activation then submits the NEW committed
        payload. The card is client-local, so the router stays at its root."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        look = ("explore.look", "看看石碑", {"target_id": 9102})
        wait = ("explore.wait", "等到天亮", {"daypart": "dawn"})
        talk = ("explore.talk_open", "找哨衛聊聊", {"npc_id": 9001})
        scripted = ("explore.talk_scripted", "問候哨衛", {"npc_id": 9001, "keyword_id": "問候"})
        accepted = self._inject_panels(page, self._ready_context(look, wait, talk))
        self.assertTrue(accepted["accepted"], accepted)

        activate_overview_chip(page, "suggestions")
        page.locator(SUGGESTIONS_CARD_SELECTOR).wait_for(state="visible", timeout=15000)
        self.assertEqual(self._depth(page), 1, "the suggestions card is not a router frame")
        page.locator(SUGGESTIONS_CARD_SELECTOR).focus()
        page.keyboard.press("ArrowDown")
        self.assertEqual(self._card_active_label(page), "等到天亮")

        # Reordered + extended commit: the same card survives at a new index.
        accepted = self._inject_panels(page, self._ready_context(talk, scripted, wait, look))
        self.assertTrue(accepted["accepted"], accepted)
        page.wait_for_timeout(120)
        self.assertEqual(
            self._card_active_label(page),
            "等到天亮",
            "the active card did not survive the re-resolution",
        )

        # The active card vanishes: the active row lands on a SURVIVING row.
        accepted = self._inject_panels(page, self._ready_context(talk, look, scripted))
        self.assertTrue(accepted["accepted"], accepted)
        page.wait_for_timeout(120)
        landed = self._card_active_label(page)
        self.assertIn(
            landed,
            ("找哨衛聊聊", "看看石碑", "問候哨衛", "清除建議"),
            "the lost-card fallback did not land on a surviving row",
        )

        # Activating the active row submits the NEW committed row's action.
        expected_action = {
            "找哨衛聊聊": "explore.talk_open",
            "看看石碑": "explore.look",
            "問候哨衛": "explore.talk_scripted",
            "清除建議": "options.dismiss",
        }[landed]
        page.locator(SUGGESTIONS_CARD_SELECTOR).focus()
        page.keyboard.press("Enter")
        # The proof is the OUTBOUND envelope only: the fabricated identity
        # cannot be accepted by the server (its own result/lock behaviour is
        # covered elsewhere), so the recorder — written synchronously at
        # dispatch — is the assertion source, not the in-flight gate.
        page.wait_for_function(
            "(id) => window.__elosernSent.filter((m) => m[0] === 'ui_action'"
            " && m[1][0] && m[1][0].action_id === id).length === 1",
            arg=expected_action,
            timeout=10000,
        )
        actions = [
            args[0]
            for cmdname, args, _kw in outbound_messages(page)
            if cmdname == "ui_action" and args
        ]
        self.assertEqual(len(actions), 1, "the activation dispatched exactly one action")
        self.assertEqual(actions[0].get("action_id"), expected_action)

    @covers_requirement("webclient-frame-resolution::unresolvable-frames-pop-one-level-only-the-root-frame-renders-a-degraded-reason-row")
    def test_whole_stack_loss_cascades_to_the_degraded_root_and_recovers(self):
        """A panel withdrawal degrades the (empty) exploration root in place
        into the single disabled marker row with the server-authored reason
        verbatim, and closes the open wait card in the same commit;
        activating the marker submits nothing, and a returning panel
        re-resolves the SAME root frame, with the compass and the place
        card's room actions back."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        pinned_context = {
            "context_actions": {
                "schema_version": 5,
                "available": True,
                "kind": "exploration",
                "affordances": [],
                "suggestions": {"status": "generating"},
            },
        }
        accepted = self._inject_panels(page, {
            "exploration": self._fabricated_exploration_panel(interact=[self._target(9001, "哨衛士兵")]),
            **pinned_context,
        })
        self.assertTrue(accepted["accepted"], accepted)

        activate_overview_chip(page, "wait")  # the place card's 等待 -> the wait card
        page.locator(WAIT_CARD_SELECTOR).wait_for(state="visible", timeout=15000)
        self.assertEqual(self._depth(page), 1)

        withdrawn = "這片區域暫時無法操作"
        accepted = self._inject_panels(page, {
            "exploration": {
                "schema_version": 4,
                "available": False,
                "reason": {"code": "exploration.unavailable", "message": withdrawn},
            },
            **pinned_context,
        })
        self.assertTrue(accepted["accepted"], accepted)

        # ONE commit settles it all: depth 1, degraded root, no card.
        self.assertEqual(self._depth(page), 1)
        self.assertEqual(
            store_state(page)["degradedRoot"],
            {
                "key": "degraded-root",
                "reason": withdrawn,
                "fallback": "畫面狀態已更新，請返回上層",
            },
        )
        self.assertIsNone(store_state(page)["roomCard"])
        page.locator(WAIT_CARD_SELECTOR).wait_for(state="detached", timeout=15000)
        # The pane presents exactly the single disabled marker row with the
        # server message verbatim — no stale row survives.
        self.assertEqual(self._pane_keys(page), ["degraded-root"])
        self.assertIn(
            withdrawn,
            page.locator('#action-dock [data-item-key="degraded-root"]').inner_text(),
        )
        # It submits nothing.
        sent_before = sent_action_count(page)
        self.assertFalse(
            page.evaluate("() => window.__elosernBridge.store.focusConfirm('keyboard')")
        )
        self.assertEqual(sent_action_count(page), sent_before)

        # The panel returns: the SAME root frame re-resolves and the degraded
        # presentation clears with the commit.
        accepted = self._inject_panels(page, {
            "exploration": self._fabricated_exploration_panel(move=[self._move_row("ex-a", "北門")]),
            **pinned_context,
        })
        self.assertTrue(accepted["accepted"], accepted)
        self.assertIsNone(store_state(page)["degradedRoot"])
        # The recovered root is the empty exploration root: no dock row; the
        # room actions are the place card's and the exit is the compass's.
        self.assertEqual(self._pane_keys(page), [])
        page.locator('[data-anchor="map"] [data-testid="place-card-wait"]').wait_for(state="visible", timeout=15000)
        self.assertEqual(compass_target_refs(page), ["ex-a"])

    @covers_requirement("webclient-frame-resolution::suggestions-frames-are-status-driven-generating-never-pops-unavailable-exits-to-the-root")
    def test_suggestions_frame_is_status_driven(self):
        """The status split on the suggestions card: `generating`/`degraded`
        commits keep the open card and its content follows the commit (no
        close, no timer); `unavailable` — the options-surface no-pane rule —
        closes the card and drops the 建議 pill WITHOUT any reason row."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        def context_actions(suggestions: dict) -> dict:
            return {
                "context_actions": {
                    "schema_version": 5,
                    "available": True,
                    "kind": "exploration",
                    "affordances": [],
                    "suggestions": suggestions,
                },
            }

        note = SUGGESTIONS_CARD_SELECTOR + ' [data-testid="choice-card-note"]'
        # A known `generating` envelope, then the 建議 pill opens the card.
        accepted = self._inject_panels(page, context_actions({"status": "generating"}))
        self.assertTrue(accepted["accepted"], accepted)
        activate_overview_chip(page, "suggestions")
        page.locator(SUGGESTIONS_CARD_SELECTOR).wait_for(state="visible", timeout=15000)
        self.assertEqual(self._depth(page), 1)
        self.assertEqual(page.locator(note).all_inner_texts(), ["AI 正在構思建議…"])

        # A fresh `generating` commit: the card STAYS with its muted note.
        accepted = self._inject_panels(page, context_actions({"status": "generating"}))
        self.assertTrue(accepted["accepted"], accepted)
        self.assertEqual(store_state(page)["roomCard"], {"kind": "suggestions"})
        self.assertEqual(page.locator(note).all_inner_texts(), ["AI 正在構思建議…"])

        # `degraded` with zero cards: the card stays and its CONTENT follows
        # the commit (the dismiss row appears).
        accepted = self._inject_panels(
            page, context_actions({"status": "degraded", "cards": []})
        )
        self.assertTrue(accepted["accepted"], accepted)
        page.locator(SUGGESTIONS_CARD_SELECTOR + ' [data-testid="suggestions-card-dismiss"]').wait_for(
            state="visible", timeout=15000
        )
        self.assertEqual(store_state(page)["roomCard"], {"kind": "suggestions"})

        # `unavailable`: no card and no pill may exist, and NO degraded
        # marker/reason row is rendered.
        accepted = self._inject_panels(page, context_actions({"status": "unavailable"}))
        self.assertTrue(accepted["accepted"], accepted)
        state = store_state(page)
        self.assertIsNone(state["roomCard"])
        self.assertIsNone(state["degradedRoot"], "the close rendered a reason row")
        page.locator(SUGGESTIONS_CARD_SELECTOR).wait_for(state="detached", timeout=15000)
        self.assertEqual(page.locator('#action-dock [data-testid="suggestions-pill"]').count(), 0)
        self.assertEqual(self._pane_keys(page), [])

    @covers_requirement("webclient-exploration-menu::exploration-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_reconnect_rebuilds_exploration_without_replay(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
        )
        page.evaluate("Evennia.connect()")
        self._wait_exploration_available(page)
        # The rebuilt dock derives from server-persisted state and no dialogue
        # or mutation is automatically replayed.
        self.assertEqual(sent_action_count(page, "explore.move"), 0)
        self.assertEqual(sent_action_count(page, "explore.talk_open"), 0)
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 0)
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)
