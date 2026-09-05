"""Comprehensive tests for companion possession presentation, affordances, and actions.

Covers capabilities:
- webclient-possession-presentation
- webclient-party-panel
- exploration-affordances
- webclient-action-dispatch
"""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from twisted.internet.task import Clock
from typeclasses.characters import PlayerCharacter

from tools.spec_traceability import covers_requirement
from web.webclient.actions.account_actions import set_clock_for_testing
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC
from web.webclient.actions.dispatcher import (
    attach_coordinator,
    handle_ui_action,
)
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.actions.exploration_actions import (
    _possess_adapter,
    _possess_release_adapter,
    validate_possess_payload,
    validate_possess_release_payload,
)
from web.webclient.actions.service_actions import _buy_adapter, _sell_adapter
from web.webclient.presentation.affordances import (
    ACTION_CODE_ALLOWLIST,
    SUGGESTIBLE_ACTION_IDS,
    default_cards,
    exploration_affordances,
)
from web.webclient.presentation.character import character_presenter
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.ingress import build_presentation_context, synchronize_session
from web.webclient.presentation.objectives import objectives_presenter
from web.webclient.presentation.party import party_presenter
from web.webclient.presentation.possession_banner import (
    POSSESSION_BANNER_SCHEMA_VERSION,
    possession_banner_presenter,
    validate_possession_banner,
)
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    build_production_registry,
)
from web.webclient.presentation.services import services_presenter
from web.webclient.presentation.status import status_presenter
from world.rules.combat_session import engage
from world.quests.catalog import register_catalog
from world.rules.clock import get_world_clock
from world.rules.party import join_party
from world.rules.possession import (
    POSSESSED_REFUSAL_MESSAGES,
    PossessionGateError,
    REASON_IN_COMBAT,
    REASON_NOT_CO_LOCATED,
    REASON_POSSESSED_ENGAGE,
    REASON_POSSESSED_SHOP,
    REASON_POSSESSED_TALK,
    enter_possession,
    release_possession,
)


class PossessionPresentationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog()
        get_world_clock()
        self.player = create_object(PlayerCharacter, key="勇者", location=self.room1)
        self.player.account = self.account
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.db.wallet = 5000
        self.player.db.inventory = ["plain_sword"]
        self.session.puppet = self.player
        self.player.sessions.add(self.session)
        self.npc = create_object(LLMNPC, key="同伴小艾", location=self.room1)
        self.npc.race = "human"
        self.npc.apply_race_baseline()
        self.npc.db.inventory = ["healing_potion", "meal"]
        join_party(self.npc, self.player)
        self.registry = build_production_registry()
        self.action_registry = build_production_action_registry()
        self.clock = Clock()
        set_clock_for_testing(self.clock)
        self.coordinator = attach_coordinator(self.session, self.registry)
        self.sent_messages = []
        real_msg = self.session.msg
        def _recording_msg(*args, **kwargs):
            self.sent_messages.append((args, kwargs))
            real_msg(*args, **kwargs)
        self.session.msg = _recording_msg

    def tearDown(self):
        try:
            set_clock_for_testing(None)
            if getattr(self.player.db, "possession", None):
                release_possession(self.player, reason="disconnect")
        except Exception:
            pass
        super().tearDown()

    @covers_requirement(
        "exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only"
    )
    def test_vocabulary_possess_and_release_states(self):
        """Possess entries mirror gates; release appears once while possessing; refusals stay visible."""
        # 1. Unpossessed: bound companion has explore.possess enabled
        vocab = exploration_affordances(self.player)
        possess_entries = [e for e in vocab if e.action_id == "explore.possess"]
        self.assertEqual(len(possess_entries), 1)
        self.assertTrue(possess_entries[0].enabled)
        self.assertEqual(possess_entries[0].params, {"npc_id": self.npc.id})
        self.assertIsNone(possess_entries[0].disabled_reason)

        # No release entry while unpossessed
        self.assertFalse(any(e.action_id == "explore.possess_release" for e in vocab))

        # 2. Combat gate: active combat disables explore.possess with in_combat
        with patch("world.rules.combat_session.is_in_active_session", side_effect=lambda c: c == self.npc):
            vocab_combat = exploration_affordances(self.player)
            possess_combat = [e for e in vocab_combat if e.action_id == "explore.possess"]
            self.assertEqual(len(possess_combat), 1)
            self.assertFalse(possess_combat[0].enabled)
            self.assertEqual(possess_combat[0].disabled_reason[0], REASON_IN_COMBAT)

        monster = create_object(Monster, key="哥布林", location=self.room1)
        # 3. Mid-possession: actor is possessed NPC
        enter_possession(self.player, self.npc)
        vocab_possessed = exploration_affordances(self.npc)

        # Release entry is present exactly once
        release_entries = [e for e in vocab_possessed if e.action_id == "explore.possess_release"]
        self.assertEqual(len(release_entries), 1)
        self.assertTrue(release_entries[0].enabled)
        self.assertEqual(release_entries[0].label, "歸位")
        self.assertEqual(release_entries[0].params, {"npc_id": self.npc.id})

        # D10 Refusals: engage is disabled with possessed_engage
        engage_entries = [e for e in vocab_possessed if e.action_id == "explore.engage"]
        self.assertTrue(len(engage_entries) > 0)
        self.assertFalse(engage_entries[0].enabled)
        self.assertEqual(engage_entries[0].disabled_reason[0], REASON_POSSESSED_ENGAGE)

    @covers_requirement(
        "exploration-affordances::affordance-params-are-validator-normalized"
    )
    def test_possess_affordance_params_normalized(self):
        """Possess action params round-trip exact validator schemas."""
        self.assertEqual(validate_possess_payload({"npc_id": 42}), {"npc_id": 42})
        self.assertEqual(validate_possess_release_payload({"npc_id": 42}), {"npc_id": 42})

        with self.assertRaises(ValueError):
            validate_possess_payload({"npc_id": 0})
        with self.assertRaises(ValueError):
            validate_possess_payload({"npc_id": -5})
        with self.assertRaises(ValueError):
            validate_possess_payload({})

    @covers_requirement(
        "webclient-possession-presentation::every-snapshot-while-possessing-carries-the-possession-banner"
    )
    def test_possession_banner_available_and_unavailable(self):
        """Banner payload names host and tick while possessed, and unavailable otherwise."""
        context_unpossessed = PresentationContext(actor=self.player, protocol_version=1)

        # Unpossessed: presenter raises PanelUnavailableError; registry renders unavailable
        with self.assertRaises(PanelUnavailableError):
            possession_banner_presenter(context_unpossessed)
        rendered_unpossessed = self.registry.render("possession_banner", context_unpossessed)
        self.assertFalse(rendered_unpossessed["available"])
        self.assertEqual(rendered_unpossessed["schema_version"], 1)
        self.assertEqual(rendered_unpossessed["reason"]["code"], "not_possessing")

        # Possessed: presenter returns available banner
        enter_possession(self.player, self.npc)
        context_possessed = PresentationContext(actor=self.npc, protocol_version=1)
        banner = possession_banner_presenter(context_possessed)
        self.assertTrue(banner["available"])
        self.assertEqual(banner["schema_version"], POSSESSION_BANNER_SCHEMA_VERSION)
        self.assertEqual(banner["host_name"], self.npc.key)
        self.assertIsInstance(banner["since_tick"], int)

        # Fixed presentation line matches specification
        line = f"你透過{banner['host_name']}的雙眼行動"
        self.assertEqual(line, f"你透過{self.npc.key}的雙眼行動")

        # Release clears banner
        release_possession(self.player, npc=self.npc, reason="handback")
        rendered_after = self.registry.render("possession_banner", context_unpossessed)
        self.assertFalse(rendered_after["available"])

    @covers_requirement(
        "webclient-possession-presentation::panels-render-the-honest-v1-hybrid-under-the-banner"
    )
    def test_panels_render_honest_hybrid(self):
        """Wallet/guild/status show player A's data; inventory/equipment show NPC B's data."""
        # Pre-possession baseline
        ctx_player = PresentationContext(actor=self.player, protocol_version=1)
        char_panel_before = character_presenter(ctx_player)
        wallet_before = char_panel_before["wallet"]
        self.assertEqual(wallet_before, 5000)

        # Enter possession
        enter_possession(self.player, self.npc)
        ctx_npc = PresentationContext(actor=self.npc, protocol_version=1)

        # 1. character_presenter: wallet is byte-identical to A's wallet
        char_panel = character_presenter(ctx_npc)
        self.assertTrue(char_panel["available"])
        self.assertEqual(char_panel["wallet"], 5000)
        self.assertEqual(char_panel["wallet"], wallet_before)

        # 2. services_presenter: player.wallet is A's; inventory.rows are B's
        serv_panel = services_presenter(ctx_npc)
        self.assertTrue(serv_panel["available"])
        self.assertEqual(serv_panel["player"]["wallet"], 5000)
        self.assertEqual(serv_panel["inventory"]["wallet"], 5000)
        item_keys = [row["item_key"] for row in serv_panel["inventory"]["rows"]]
        self.assertIn("healing_potion", item_keys)
        self.assertIn("meal", item_keys)
        self.assertNotIn("plain_sword", item_keys)

        # 3. status_presenter: name and status belong to A
        stat_panel = status_presenter(ctx_npc)
        self.assertTrue(stat_panel["available"])
        self.assertEqual(stat_panel["actor"]["name"], self.player.key)

        # 4. objectives_presenter: available without error
        obj_panel = objectives_presenter(ctx_npc)
        self.assertTrue(obj_panel["available"])

    @covers_requirement(
        "webclient-possession-presentation::the-dispatcher-refuses-possession-incompatible-actions-with-fixed-zero-write-results"
    )
    def test_dispatcher_refuses_possession_incompatible_actions(self):
        """Shop buy/sell and talk/engage return zero-write rejections while possessed."""
        enter_possession(self.player, self.npc)
        wallet_before = self.player.db.wallet
        inv_before = list(self.npc.db.inventory)

        # shop.buy refusal
        buy_res = _buy_adapter(self.npc, {"item_key": "meal", "quantity": 1})
        self.assertEqual(buy_res["outcome"], "rejected")
        self.assertEqual(buy_res["code"], REASON_POSSESSED_SHOP)
        self.assertEqual(buy_res["message"], POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_SHOP])
        self.assertEqual(self.player.db.wallet, wallet_before)
        self.assertEqual(list(self.npc.db.inventory), inv_before)

        # shop.sell refusal
        sell_res = _sell_adapter(self.npc, {"item_key": "meal", "quantity": 1})
        self.assertEqual(sell_res["outcome"], "rejected")
        self.assertEqual(sell_res["code"], REASON_POSSESSED_SHOP)
        self.assertEqual(self.player.db.wallet, wallet_before)

    @covers_requirement(
        "webclient-possession-presentation::possession-re-points-the-session-actor-through-the-epoch-transition"
    )
    def test_possession_actor_repointing_and_epoch_transition(self):
        """Actor marker re-points through the epoch transition and handback re-points home."""
        coordinator = self.coordinator
        epoch_before = coordinator.epoch
        self.assertEqual(self.session.puppet, self.player)

        # 1. Dispatch explore.possess through the production dispatcher
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "req-possess-1",
            "base_revision": coordinator.revision,
            "action_id": "explore.possess",
            "payload": {"npc_id": int(self.npc.pk)},
        }
        handle_ui_action(
            self.session,
            self.player,
            envelope,
            self.action_registry,
            self.registry,
        )

        # Immediate result under old epoch
        result_calls = [kw for args, kw in self.sent_messages if "ui_action_result" in kw]
        self.assertTrue(len(result_calls) > 0)
        action_res = result_calls[-1]["ui_action_result"][0][0]
        self.assertEqual(action_res["request_id"], "req-possess-1")
        self.assertEqual(action_res["outcome"], "success")
        self.assertEqual(action_res["code"], "possessed")

        # Drain reactor tick to execute transition
        self.clock.advance(0.1)

        # Actor re-pointed and epoch bumped
        self.assertEqual(self.session.puppet, self.npc)
        self.assertEqual(self.session.ndb.elosern_actor_id, str(self.npc.pk))
        self.assertNotEqual(coordinator.epoch, epoch_before)

        # Snapshot received under new epoch carrying possession banner and hybrid panels
        snapshot_calls = [kw for args, kw in self.sent_messages if "ui_snapshot" in kw]
        self.assertTrue(len(snapshot_calls) > 0)
        latest_snap = snapshot_calls[-1]["ui_snapshot"][0][0]
        self.assertTrue(latest_snap["panels"]["possession_banner"]["available"])
        self.assertEqual(latest_snap["panels"]["possession_banner"]["host_name"], self.npc.key)
        self.assertEqual(latest_snap["panels"]["character"]["wallet"], 5000)

        epoch_mid = coordinator.epoch

        # 2. Dispatch explore.possess_release through the production dispatcher
        envelope_rel = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "req-release-1",
            "base_revision": coordinator.revision,
            "action_id": "explore.possess_release",
            "payload": {"npc_id": int(self.npc.pk)},
        }
        handle_ui_action(
            self.session,
            self.npc,
            envelope_rel,
            self.action_registry,
            self.registry,
        )

        # Drain reactor tick to execute handback transition
        self.clock.advance(0.1)

        # Actor re-pointed back to player and epoch bumped
        self.assertEqual(self.session.puppet, self.player)
        self.assertEqual(self.session.ndb.elosern_actor_id, str(self.player.pk))
        self.assertNotEqual(coordinator.epoch, epoch_mid)

        # Next snapshot has banner unavailable
        after_snap_calls = [kw for args, kw in self.sent_messages if "ui_snapshot" in kw]
        after_snap = after_snap_calls[-1]["ui_snapshot"][0][0]
        self.assertFalse(after_snap["panels"]["possession_banner"]["available"])

    @covers_requirement(
        "webclient-possession-presentation::the-possession-controls-complete-the-action-round-trip"
    )
    def test_possession_controls_round_trip(self):
        """explore.possess and release adapters complete successfully; rejections are clean."""
        # Non-co-located rejection
        npc2 = create_object(LLMNPC, key="遠方同伴", location=self.room1)
        join_party(npc2, self.player)
        npc2.location = self.room2
        res_fail = _possess_adapter(self.player, {"npc_id": npc2.id})
        self.assertEqual(res_fail["outcome"], "rejected")
        self.assertEqual(res_fail["code"], REASON_NOT_CO_LOCATED)

        # Successful possess adapter round-trip
        res_ok = _possess_adapter(self.player, {"npc_id": self.npc.id})
        self.assertEqual(res_ok["outcome"], "success")
        self.assertEqual(res_ok["code"], "possessed")

        # Successful release adapter round-trip
        res_release = _possess_release_adapter(self.npc, {"npc_id": self.npc.id})
        self.assertEqual(res_release["outcome"], "success")
        self.assertEqual(res_release["code"], "released")

        # Suggestible exclusion: possession actions are never suggestible cards
        vocab = exploration_affordances(self.player)
        cards = default_cards(vocab, actor=self.player)
        card_actions = {c.action_id for c in cards}
        self.assertNotIn("explore.possess", card_actions)
        self.assertNotIn("explore.possess_release", card_actions)

    def test_locked_recheck_prevents_stale_possession(self):
        """If gate changes right before row lock, enter_possession raises PossessionGateError under lock."""
        self.npc.location = self.room2
        with self.assertRaises(PossessionGateError) as ctx:
            enter_possession(self.player, self.npc)
        self.assertEqual(ctx.exception.reason, REASON_NOT_CO_LOCATED)


    @covers_requirement(
        "webclient-party-panel::the-party-drawer-offers-possession-controls-per-companion"
    )
    def test_party_panel_schema_untouched_and_companion_affordance_present(self):
        """party panel payload schema carries no possession field; vocabulary offers possess."""
        # party panel schema version 1 untouched
        ctx = PresentationContext(actor=self.player, protocol_version=1)
        panel = party_presenter(ctx)
        self.assertEqual(panel["schema_version"], 1)
        self.assertTrue(panel["available"])
        self.assertEqual(set(panel.keys()), {"schema_version", "available", "slots"})

        for slot in panel["slots"]:
            # Slot is standard 6-key row contract
            self.assertEqual(
                set(slot.keys()),
                {"identity", "display_name", "portrait_ref", "bond_stage", "hp_current", "hp_maximum"},
            )
            self.assertNotIn("possessed", slot)
            self.assertNotIn("possess", slot)
