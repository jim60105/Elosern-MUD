"""Assembled real-runtime party acceptance (party-combat-runtime-acceptance).

The 20-change batch's assembled gate, exercised on the managed localhost
runtime the harness already owns: one journey commands two real allies
through a companion-owned SELF skill and a companion-owned item, revises an
earlier confirmed choice before completion, resolves only on the final
confirmation and observes the fresh next draft; another keeps an unfinished
persistent draft across a transport reconnect without replaying intent; a
third cancels and confirms the party-scope exits and proves a settled exit
cannot settle twice.

Every assertion reads the canonical store published from the server
(`wait_for_store_state`), never a mocked client, and every panel fact is the
committed combat panel. Full managed-browser execution and the complete
traceability evidence run stay CI-owned (see the browser shards).
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from web.browser_support.browser_fixtures_data import combat_journey_values

from world.rules.item_effects import GaugeAdjustEffect, ItemStat
from world.tests.synthetic_data import SYNTH_ITEM_EFFECT_PROFILES

from .browser_base import ACCEPTANCE_VIEWPORTS, BrowserAcceptanceTest
from .browser_helpers import (
    evaluate_tolerating_navigation,
    focus_action_dock,
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    store_state,
    store_state_or_none,
    suppress_one_shot_recovery_reload,
    wait_for_presentation_settled,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin

# The SELF-shape skill and the usable consumable the acceptance seed grants to
# the bound companion's own inventory and lineage: the real engagement's second
# allied actor carries both, and neither belongs to the commander.
COMPANION_SKILL_KEY = "t_moss_veil"
COMPANION_ITEM_KEY = "t_ember_spray"

# The party-scope exit rows the dock opens through the server prompt.
EXIT_ROW_RETREAT = "retreat"
EXIT_ROW_SURRENDER = "surrender"

# The companion item's authored self-scoped HP restore, read from the same
# rulebook-side profile map settlement resolves the item through
# (world/tests/synthetic_data/data_items.py): the journey's heal arithmetic is
# derived from the shipped rulebook row, never a guessed number.
COMPANION_ITEM_HEAL = next(
    effect.amount
    for effect in SYNTH_ITEM_EFFECT_PROFILES[COMPANION_ITEM_KEY].effects
    if isinstance(effect, GaugeAdjustEffect) and effect.stat is ItemStat.HP
)


class PartyAcceptanceBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Real two-actor combat journeys on a dedicated isolated runtime.

    Each test boots its own managed server: a live party session leaves the
    Evennia session in a state a later fresh login on the same server cannot
    reuse cleanly, exactly like the other combat suites.
    """

    def setUp(self) -> None:
        self.server = ManagedServer()
        # The acceptance seed gives the bound companion one real usable
        # consumable of its own; every other suite boots without the flag.
        self.server.runtime.env["ELOSERN_BROWSER_PARTY_ACCEPTANCE"] = "1"
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    # -- runtime plumbing ---------------------------------------------------

    def _engage(self, page) -> None:
        target = combat_journey_values()["engage_target"]
        page.evaluate("([t]) => Evennia.msg('text', [`engage ${t}`], {})", [target])
        self._wait_combat_mode(page)

    def _wait_combat_mode(self, page, timeout: int = 30000) -> None:
        wait_for_store_state(
            page,
            lambda s: s.get("mode") == "combat"
            and ((s.get("panels") or {}).get("context_actions") or {}).get("available")
            is True,
            timeout=timeout,
        )

    def _panel(self, page) -> dict:
        return store_state(page)["panels"]["context_actions"]

    def _press(self, page, key: str) -> None:
        page.keyboard.press(key)
        page.wait_for_timeout(80)

    def _focus_key(self, page):
        return store_state(page).get("focus", {}).get("key")

    def _walk_to(self, page, key: str, limit: int = 40) -> None:
        """Walk the mounted command list down to ``key`` (bounded)."""
        for _ in range(limit):
            if self._focus_key(page) == key:
                return
            self._press(page, "ArrowDown")
        self.assertEqual(self._focus_key(page), key, f"never reached {key}")

    def _wait_unlocked(self, page, timeout: int = 30000) -> None:
        wait_for_store_state(
            page, lambda s: not (s.get("dispatch") or {}).get("inFlight"), timeout=timeout
        )

    def _root(self, page) -> None:
        """Return the dock to exactly the combat root, then focus it."""
        for _ in range(4):
            state = store_state(page)
            if state.get("dockSource") == "combat.root" and state.get("dockDepth") == 1:
                break
            self._press(page, "Escape")
        focus_action_dock(page)

    def _commands_sent(self, page) -> int:
        return sent_action_count(page, "combat.command")

    def _draft_entry(self, page, actor_id: int) -> dict | None:
        draft = self._panel(page)["draft"]
        for entry in draft["entries"]:
            if entry["actor_id"] == actor_id:
                return entry
        return None

    def _party_identities(self, page) -> list[int]:
        return [
            int(p["identity"])
            for p in self._panel(page)["participants"]
            if p["team"] == "party"
        ]

    def _commanded_identity(self, page) -> int:
        return int(self._panel(page)["choices"]["actor_id"])

    def _wait_beat_settled(self, page, timeout: int = 60000) -> None:
        """Wait until the resolved round's playback finished and the card is ready."""
        # The round's playback binds just after the session panel commits, so
        # give it one settle window before requiring the ready root.
        page.wait_for_timeout(600)
        wait_for_store_state(
            page,
            lambda s: (s.get("beatPlayback") is None
                       or (s.get("beatPlayback") or {}).get("phase") == "done")
            and not s.get("beatHold")
            and not (s.get("dispatch") or {}).get("beatLocked")
            and s.get("combatProgress") is not None,
            timeout=timeout,
        )

    def _switch_actor(self, page, identity: int) -> None:
        """Command another living member through the card's actor selector.

        The selector asks the server for that member's canonical choices (one
        read-only query) and returns to exactly one root. The card chrome only
        renders the control at the root, so the dock is first returned there
        (a resolved round leaves the last opened frame behind).
        """
        self._root(page)
        change = page.locator('[data-testid="combat-actor-change"]')
        change.wait_for(state="visible", timeout=30000)
        change.click()
        row = page.locator(f'#action-dock [data-item-key="actor-{identity}"]')
        row.wait_for(state="visible", timeout=15000)
        row.click()
        wait_for_store_state(
            page,
            lambda s: (
                (s.get("panels") or {}).get("context_actions") or {}
            ).get("choices", {}).get("actor_id")
            == identity,
            timeout=30000,
        )
        wait_for_store_state(
            page,
            lambda s: s.get("dockSource") == "combat.root" and s.get("dockDepth") == 1,
            timeout=15000,
        )

    def _open_items_frame(self, page) -> None:
        self._walk_to(page, "items")
        self._press(page, "Enter")

    def _open_skill_frame(self, page, skill_key: str) -> None:
        """Open the single-subgroup category that owns ``skill_key``."""
        panel = self._panel(page)
        row_key = None
        for index, category in enumerate(panel["choices"]["skills"]):
            for group in category.get("groups") or []:
                if any(skill["key"] == skill_key for skill in group.get("skills") or []):
                    row_key = f"skill-cat-{index}"
                    break
            if row_key:
                break
        self.assertIsNotNone(row_key, f"{skill_key} is not in the committed skills")
        self._walk_to(page, "skills")
        self._press(page, "Enter")
        self._walk_to(page, row_key)
        self._press(page, "Enter")
        # The single-subgroup category opens the skill frame directly.
        self._walk_to(page, skill_key)
        self._press(page, "Enter")

    def _commit_player_attack(self, page, foe_id: int) -> None:
        """Command the player's basic attack at ``foe_id`` and submit it."""
        self._walk_to(page, "attack")
        self._press(page, "Enter")
        self._walk_to(page, f"target-{foe_id}")
        self._press(page, "Enter")

    def _first_foe(self, page) -> int:
        for participant in self._panel(page)["participants"]:
            if participant["team"] == "foes" and participant["state"] == "active":
                return int(participant["identity"])
        raise AssertionError("no active foe")

    def _open_exit_card(self, page, row: str) -> None:
        """Open the server-bound party exit prompt from the combat root."""
        self._root(page)
        wait_for_presentation_settled(page)
        before = store_state(page)["lastActionResult"]
        self._walk_to(page, row)
        self._press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId")
            not in (None, (before or {}).get("requestId"))
            and (s.get("dispatch") or {}).get("inFlight") is None,
            timeout=20000,
        )
        card = page.locator('[data-testid="party-exit-question"]')
        card.wait_for(state="visible", timeout=30000)
        self.assertEqual(
            page.evaluate(
                "() => { const el = document.activeElement; "
                "return el && el.closest('[data-testid=\"party-exit-question\"]') "
                "? el.textContent.trim() : null; }"
            ),
            "否",
            "the safe answer holds focus",
        )
        return card

    # -- 1.1 / assembled member journey -------------------------------------

    @covers_requirement(
        "webclient-browser-verification::actual-party-combat-acceptance-completes-skills-items-drafts-and-reconnect"
    )
    def test_member_journey_commands_a_companion_skill_and_item_and_revises_a_choice(self):
        """One real two-actor journey across two rounds at both desktop viewports.

        The commanded member switch proves the committed resource/item
        choices belong to the selected companion (the commander's own skill
        set is not offered to it), an earlier confirmed skill is replaced by
        the companion's own item before completion, and the final
        confirmation is what resolves the round. Round two then executes the
        companion's SELF skill, standing on the companion's figure rather
        than the controlled portrait.
        """
        page = self.logged_in_page(ACCEPTANCE_VIEWPORTS[0])
        install_outbound_recorder(page)
        self._engage(page)
        wait_for_presentation_settled(page)

        panel = self._panel(page)
        party = self._party_identities(page)
        self.assertEqual(len(party), 2, "the real party carries two allied actors")
        commandable = [
            int(actor["identity"]) for actor in panel["actors"] if actor["commandable"]
        ]
        self.assertEqual(sorted(commandable), sorted(party), "every ally is commandable")
        required = set(panel["draft"]["required_actor_ids"])
        self.assertEqual(required, set(party), "the draft requires the whole party")
        player = self._commanded_identity(page)
        companion = next(identity for identity in party if identity != player)
        foes = self._first_foe(page)

        # -- command the companion: its own SELF skill ----------------------
        self._switch_actor(page, companion)
        choices = self._panel(page)["choices"]
        self.assertEqual(choices["actor_id"], companion)
        skill_keys = [
            skill["key"]
            for category in choices["skills"]
            for group in category.get("groups") or []
            for skill in group.get("skills") or []
        ]
        self.assertIn(COMPANION_SKILL_KEY, skill_keys, "the companion carries its own skill")
        self.assertNotIn(
            combat_journey_values()["spell_key"],
            skill_keys,
            "the commander's own spell is never offered to the companion",
        )
        item_keys = [item["item_key"] for item in choices["items"]]
        self.assertIn(COMPANION_ITEM_KEY, item_keys, "the companion carries its own stock")
        quantity_before = next(
            item["quantity"]
            for item in choices["items"]
            if item["item_key"] == COMPANION_ITEM_KEY
        )
        self.assertTrue(
            next(
                item["enabled"]
                for item in choices["items"]
                if item["item_key"] == COMPANION_ITEM_KEY
            ),
            "the companion's own consumable is a legal choice",
        )

        self._open_skill_frame(page, COMPANION_SKILL_KEY)
        # The SELF step stands on the commanded companion's own figure.
        stage = store_state(page)["stageTarget"]
        self.assertEqual(stage["form"], "self")
        self.assertEqual(
            [position["identities"] for position in stage["positions"]],
            [[str(companion)]],
            "the SELF position is the commanded companion, never the controlled figure",
        )
        time_before_round = store_state(page)["serverTime"]
        commands_before = self._commands_sent(page)
        self._press(page, "Enter")
        self._wait_unlocked(page)
        self.assertEqual(self._commands_sent(page), commands_before + 1)
        wait_for_store_state(
            page,
            lambda s: any(
                entry["actor_id"] == companion
                and entry["command"].get("kind") == "skill"
                for entry in (
                    ((s.get("panels") or {}).get("context_actions") or {}).get("draft")
                    or {}
                ).get("entries", [])
            ),
            timeout=20000,
        )
        self.assertEqual(self._panel(page)["session"]["round"], 0, "no round before completion")
        self.assertEqual(self._panel(page)["session"]["round_revision"], 0)

        # -- revise it: the companion's own item replaces the skill ---------
        # A committed command republishes the panel with the commander as the
        # commanded actor, so the companion is selected once more (one
        # read-only choices query) before its own stock is offered.
        self._switch_actor(page, companion)
        self._open_items_frame(page)
        self._walk_to(page, f"item-{COMPANION_ITEM_KEY}")
        self._press(page, "Enter")  # review
        self._press(page, "Enter")  # submit the replacement
        self._wait_unlocked(page)
        wait_for_store_state(
            page,
            lambda s: any(
                entry["actor_id"] == companion
                and entry["command"].get("kind") == "item"
                for entry in (
                    ((s.get("panels") or {}).get("context_actions") or {}).get("draft")
                    or {}
                ).get("entries", [])
            ),
            timeout=20000,
        )
        entries = [e for e in self._panel(page)["draft"]["entries"] if e["actor_id"] == companion]
        self.assertEqual(len(entries), 1, "the replacement keeps exactly one entry")
        self.assertEqual(entries[0]["command"]["kind"], "item")
        # A replacement executes nothing: no round, no revision, no time, and
        # the companion's stock is still untouched until the final member
        # confirms the complete round. A committed command republishes the
        # panel with the commander as the commanded actor, so the companion's
        # own stock is read back through the read-only switch.
        self._switch_actor(page, companion)
        after_replace = self._panel(page)
        self.assertEqual(after_replace["session"]["round"], 0, "the replacement ran no round")
        self.assertEqual(after_replace["session"]["round_revision"], 0)
        self.assertEqual(store_state(page)["serverTime"], time_before_round)
        self.assertEqual(
            next(
                item["quantity"]
                for item in after_replace["choices"]["items"]
                if item["item_key"] == COMPANION_ITEM_KEY
            ),
            quantity_before,
            "the replacement consumed nothing",
        )
        # The companion is still the wounded actor the round will heal (the
        # seed wounds it by exactly the kit item's own heal; nothing between
        # here and the resolution touches it).
        companion_before_hp = next(
            p["hp_current"]
            for p in after_replace["participants"]
            if int(p["identity"]) == companion
        )

        # -- the commander's command completes the round --------------------
        self._switch_actor(page, player)
        self._commit_player_attack(page, foes)
        self._wait_unlocked(page)
        wait_for_store_state(
            page,
            lambda s: (
                ((s.get("panels") or {}).get("context_actions") or {}).get("session") or {}
            ).get("round")
            == 1,
            timeout=30000,
        )
        self._wait_beat_settled(page)
        resolved = self._panel(page)
        self.assertEqual(resolved["draft"]["entries"], [], "the resolved round leaves a fresh draft")
        self.assertEqual(set(resolved["draft"]["needs_selection_ids"]), set(party))
        commander_hp = next(
            p["hp_current"] for p in resolved["participants"] if int(p["identity"]) == player
        )
        companion_hp = next(
            p["hp_current"] for p in resolved["participants"] if int(p["identity"]) == companion
        )
        companion_maximum = next(
            p["hp_maximum"] for p in resolved["participants"] if int(p["identity"]) == companion
        )
        # The companion's own item is the kit's self-scoped HP restore
        # (COMPANION_ITEM_HEAL, capped by its own maximum), and the round
        # carries no other heal: the committed HP is exactly that capped
        # restore of its own actor. The seeded foe's target is pinned to the
        # wounded commander (web/tests/browser/seed/runner.py), so no enemy
        # strike reaches the companion in this round and the value is exact
        # in every environment rather than a direction the encounter's dice
        # could flip.
        self.assertEqual(
            companion_hp,
            min(companion_maximum, companion_before_hp + COMPANION_ITEM_HEAL),
            "the companion's own item healed the companion, its own actor",
        )
        self.assertLess(commander_hp, panel["participants"][0]["hp_maximum"] + 1)
        # The resolved panel returns the commander as the commanded actor; the
        # companion's own stock is read back through the read-only switch.
        self._switch_actor(page, companion)
        self.assertEqual(quantity_before, 1, "the companion owns one consumable")
        self.assertEqual(
            [
                item
                for item in self._panel(page)["choices"]["items"]
                if item["item_key"] == COMPANION_ITEM_KEY
            ],
            [],
            "the executed round consumed the companion's own stock",
        )

        # -- round two executes the companion's own SELF skill --------------
        self._switch_actor(page, companion)
        self._open_skill_frame(page, COMPANION_SKILL_KEY)
        self._press(page, "Enter")
        self._wait_unlocked(page)
        wait_for_store_state(
            page,
            lambda s: any(
                entry["actor_id"] == companion
                for entry in (
                    ((s.get("panels") or {}).get("context_actions") or {}).get("draft")
                    or {}
                ).get("entries", [])
            ),
            timeout=20000,
        )
        cast_entry = next(
            entry
            for entry in self._panel(page)["draft"]["entries"]
            if entry["actor_id"] == companion
        )
        self.assertEqual(
            cast_entry["command"],
            {"kind": "skill", "payload": {"scale": 1, "skill_key": COMPANION_SKILL_KEY}},
            "the completed round carries the companion's own SELF skill verbatim",
        )
        self._switch_actor(page, player)
        self._commit_player_attack(page, foes)
        self._wait_unlocked(page)
        wait_for_store_state(
            page,
            lambda s: (
                ((s.get("panels") or {}).get("context_actions") or {}).get("session") or {}
            ).get("round")
            == 2,
            timeout=30000,
        )
        self._wait_beat_settled(page)
        second_round = self._panel(page)
        companion_after = next(
            p for p in second_round["participants"] if int(p["identity"]) == companion
        )
        self.assertTrue(
            companion_after["conditions"],
            "the companion's executed SELF skill left its own applied effect",
        )
        # The actor-local accounting is observable as the companion's own
        # stock (round one) and its own applied effect (round two); the
        # commander's HP movement here is the enemy's ordinary round, which is
        # not this journey's subject.
        self.assertTrue(commander_hp > 0)
        self._wait_beat_settled(page)

        # -- the existing centred-card/target/warning contracts hold at the
        #    second accepted viewport as well --------------------------------
        self._root(page)
        page.set_viewport_size(
            {"width": ACCEPTANCE_VIEWPORTS[1][0], "height": ACCEPTANCE_VIEWPORTS[1][1]}
        )
        page.wait_for_timeout(200)

        # The stage-target contract is exercised at the second viewport too:
        # the companion's SELF step still stands on the companion's own figure.
        self._switch_actor(page, companion)
        self._open_skill_frame(page, COMPANION_SKILL_KEY)
        stage_wide = store_state(page)["stageTarget"]
        self.assertEqual(stage_wide["form"], "self")
        self.assertEqual(
            [position["identities"] for position in stage_wide["positions"]],
            [[str(companion)]],
            "the companion SELF figure holds at the second accepted viewport",
        )
        self._press(page, "Escape")
        self._root(page)

        box = page.locator("#action-dock").bounding_box()
        viewport = page.viewport_size
        self.assertLessEqual(
            abs((box["x"] + box["width"] / 2) - viewport["width"] / 2),
            2.0,
            "the command card stays centred at the second accepted viewport",
        )
        lefts = page.evaluate(
            """() => Array.from(
                 document.querySelectorAll(
                   '#action-dock [data-testid="dock-menu"] [data-item-key]'))
               .map((el) => Math.round(el.getBoundingClientRect().x))"""
        )
        self.assertTrue(lefts, "the root list renders rows")
        self.assertEqual(len(set(lefts)), 1, "the root stays one column")
        card = self._open_exit_card(page, EXIT_ROW_SURRENDER)
        self.assertIn(
            "確定要全隊投降？",
            card.locator('[data-testid="question-card-question"]').inner_text(),
        )
        card.locator('[data-testid="question-card-no"]').click()
        page.wait_for_selector(
            '[data-testid="party-exit-question"]', state="detached", timeout=30000
        )

    @covers_requirement(
        "webclient-browser-verification::actual-party-combat-acceptance-completes-skills-items-drafts-and-reconnect"
    )
    def test_unfinished_draft_survives_reconnect_without_replaying_intent(self):
        """An unfinished persistent draft is restored unchanged, never replayed.

        Only the companion's command is confirmed before an abnormal transport
        close. After the client reconnects to the same session the draft entry,
        the draft version and the round revision are exactly the pre-disconnect
        facts, no command is sent again, and no round starts by itself.
        """
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        wait_for_presentation_settled(page)

        party = self._party_identities(page)
        self.assertEqual(len(party), 2, "the real party carries two allied actors")
        player = self._commanded_identity(page)
        companion = next(identity for identity in party if identity != player)
        session_id = self._panel(page)["session"]["session_id"]

        self._switch_actor(page, companion)
        self._open_skill_frame(page, COMPANION_SKILL_KEY)
        self._press(page, "Enter")
        self._wait_unlocked(page)
        wait_for_store_state(
            page,
            lambda s: any(
                entry["actor_id"] == companion
                for entry in (
                    ((s.get("panels") or {}).get("context_actions") or {}).get("draft")
                    or {}
                ).get("entries", [])
            ),
            timeout=20000,
        )
        before_panel = self._panel(page)
        draft_before = before_panel["draft"]
        revision_before = before_panel["session"]["round_revision"]
        self.assertEqual(before_panel["session"]["round"], 0)
        commands_before = self._commands_sent(page)

        suppress_one_shot_recovery_reload(page)
        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(page, lambda s: not s.get("connected"))
        wait_for_store_state(page, lambda s: not s.get("connected"),
                             dom_readiness={
                                 "selector": "#elosern-offline-overlay",
                                 "predicate": (
                                     "() => { const o = document.querySelector('#elosern-offline-overlay'); "
                                     "return o && o.getAttribute('data-visible') === 'true'; }"
                                 ),
                                 "description": "offline overlay visible",
                             })

        deadline = time.monotonic() + 60
        state = None
        while time.monotonic() < deadline:
            state = store_state_or_none(page)
            panel = (
                ((state or {}).get("panels") or {}).get("context_actions") or {}
                if state
                else {}
            )
            if (
                state
                and state.get("connected")
                and state.get("mode") == "combat"
                and panel.get("available") is True
                and panel["session"]["session_id"] == session_id
            ):
                break
            if time.monotonic() > deadline - 25:
                evaluate_tolerating_navigation(
                    page,
                    "() => { if (window.Evennia && Evennia.connect) Evennia.connect(); }",
                )
            page.wait_for_timeout(500)
        else:
            self.fail("combat session was not restored after reconnect")

        after_panel = self._panel(page)
        self.assertEqual(after_panel["session"]["session_id"], session_id)
        self.assertEqual(after_panel["session"]["round"], 0)
        self.assertEqual(after_panel["session"]["round_revision"], revision_before)
        self.assertEqual(after_panel["draft"], draft_before, "the draft is restored verbatim")
        self.assertEqual(
            self._commands_sent(page),
            commands_before,
            "reconnect never re-sends a committed command",
        )

    # -- 2.1 / exit acceptance ----------------------------------------------

    @covers_requirement(
        "webclient-browser-verification::actual-party-exit-acceptance-covers-cancellation-committed-outcomes-and-text-parity"
    )
    def test_cancelled_exit_keeps_the_whole_draft_and_a_committed_exit_settles_once(self):
        """The party-scope exits against a real two-actor draft.

        Cancelling retreat preserves every confirmed actor entry, the round
        revision and the clock; confirming surrender emits exactly one
        confirmation, settles the whole party once and cannot settle again
        from the same server-bound token.
        """
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        wait_for_presentation_settled(page)

        party = self._party_identities(page)
        self.assertEqual(len(party), 2, "the real party carries two allied actors")
        player = self._commanded_identity(page)
        companion = next(identity for identity in party if identity != player)
        # A non-empty, unfinished draft (the companion's command only): the
        # last member's confirmation is what would auto-submit the round, so
        # cancellation has to preserve the whole saved draft.
        self._switch_actor(page, companion)
        self._open_skill_frame(page, COMPANION_SKILL_KEY)
        self._press(page, "Enter")
        self._wait_unlocked(page)
        wait_for_store_state(
            page,
            lambda s: any(
                entry["actor_id"] == companion
                for entry in (
                    ((s.get("panels") or {}).get("context_actions") or {}).get("draft")
                    or {}
                ).get("entries", [])
            ),
            timeout=20000,
        )
        panel = self._panel(page)
        draft_before = panel["draft"]
        self.assertEqual(len(draft_before["entries"]), 1, "the companion's entry is saved")
        self.assertEqual(draft_before["entries"][0]["actor_id"], companion)
        self.assertEqual(draft_before["needs_selection_ids"], [player])
        revision_before = panel["session"]["round_revision"]
        time_before = store_state(page)["serverTime"]

        # -- retreat: cancel keeps everything ------------------------------
        card = self._open_exit_card(page, EXIT_ROW_RETREAT)
        self.assertIn(
            "確定要全隊撤退？",
            card.locator('[data-testid="question-card-question"]').inner_text(),
        )
        card.locator('[data-testid="question-card-no"]').click()
        page.wait_for_selector(
            '[data-testid="party-exit-question"]', state="detached", timeout=30000
        )
        self.assertEqual(sent_action_count(page, "combat.exit_confirm"), 0)
        after_cancel = self._panel(page)
        self.assertEqual(after_cancel["draft"], draft_before)
        self.assertEqual(after_cancel["session"]["round_revision"], revision_before)
        self.assertEqual(store_state(page)["serverTime"], time_before)
        self.assertEqual(self._focus_key(page), EXIT_ROW_RETREAT)

        # -- surrender: confirm settles the whole party once ----------------
        card = self._open_exit_card(page, EXIT_ROW_SURRENDER)
        self.assertIn(
            "確定要全隊投降？",
            card.locator('[data-testid="question-card-question"]').inner_text(),
        )
        card.locator('[data-testid="question-card-yes"]').click()
        page.wait_for_selector(
            '[data-testid="party-exit-question"]', state="detached", timeout=30000
        )
        wait_for_store_state(
            page,
            lambda s: s.get("mode") == "exploration"
            and ((s.get("panels") or {}).get("context_actions") or {}).get("available")
            is True,
            timeout=40000,
        )
        confirms = [
            args[0]
            for cmdname, args, _ in outbound_messages(page)
            if cmdname == "ui_action"
            and args
            and isinstance(args[0], dict)
            and args[0].get("action_id") == "combat.exit_confirm"
        ]
        self.assertEqual(len(confirms), 1, confirms)
        settled_at = store_state(page)["serverTime"]

        # Replaying the accepted confirmation through the real transport is
        # rejected and changes nothing.
        token = confirms[0]["payload"]["confirmation_token"]
        previous = store_state(page)["lastActionResult"]
        page.evaluate(
            "([payload]) => Elosern.actions.submit('combat.exit_confirm', payload)",
            [confirms[0]["payload"]],
        )
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId")
            not in (None, (previous or {}).get("requestId")),
            timeout=20000,
        )
        replay = store_state(page)["lastActionResult"]
        # The settled session answers the replayed token as already committed:
        # one recorded settlement, never a second one.
        self.assertEqual(replay["outcome"], "success")
        self.assertEqual(replay["code"], "already_committed")
        self.assertNotEqual(replay["requestId"], (previous or {}).get("requestId"))
        self.assertTrue(token)
        self.assertEqual(store_state(page)["serverTime"], settled_at, "no second settlement")
        # Exactly one deliberate confirmation preceded the replay; the replay
        # itself settled nothing.
        self.assertEqual(
            sent_action_count(page, "combat.exit_confirm"),
            len(confirms) + 1,
        )
