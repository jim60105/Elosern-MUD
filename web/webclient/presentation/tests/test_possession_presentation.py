"""Comprehensive tests for companion possession presentation, affordances, and actions.

Covers capabilities:
- webclient-possession-presentation
- webclient-party-panel
- exploration-affordances
- webclient-action-dispatch
"""

import unittest
from types import SimpleNamespace
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
    _engage_adapter,
    _possess_adapter,
    _possess_release_adapter,
    _wait_adapter,
    _talk_freeform_adapter,
    _talk_open_adapter,
    _talk_scripted_adapter,
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
from world.rules.fatigue import SleepPosture, read_fatigue_state, write_fatigue_state
from world.rules.party import join_party
from world.rules.possession import (
    POSSESSED_REFUSAL_MESSAGES,
    PossessionGateError,
    REASON_IN_COMBAT,
    REASON_NOT_CO_LOCATED,
    REASON_POSSESSED_ENGAGE,
    REASON_POSSESSED_TALK,
    REASON_STALE_HANDOFF,
    enter_possession,
    release_possession,
    sleep_handoff_candidates,
)
from world.rules.time_skip import enter_sleep


class PossessionPresentationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog()
        get_world_clock()
        self.player = create_object(PlayerCharacter, key="勇者", location=self.room1)
        self.player.account = self.account
        self.account.characters.add(self.player)
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.db.wallet = 5000
        self.player.db.inventory = ["t_possession_blade"]
        self.session.puppet = self.player
        self.player.sessions.add(self.session)
        self.npc = create_object(LLMNPC, key="同伴小艾", location=self.room1)
        self.npc.race = "human"
        self.npc.apply_race_baseline()
        self.npc.db.inventory = ["t_possession_draught", "t_possession_ration"]
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

    @covers_requirement(
        "webclient-character-roster::each-roster-row-reports-only-canonical-owned-character-facts",
        "webclient-character-roster::the-account-roster-is-a-committed-presentation-panel-available-in-every-mode",
    )
    def test_real_possession_retains_the_owner_party_and_catalog_identity(self):
        other = create_object(LLMNPC, key="測試同行乙", location=self.room1)
        other.race = "human"
        other.apply_race_baseline()
        join_party(other, self.player)
        before = party_presenter(PresentationContext(self.player, 1))
        roster_before = self.registry.render("roster", PresentationContext(self.player, 1))
        self.assertTrue(roster_before["available"])
        owner_before = next(row for row in roster_before["characters"] if row["current"])
        enter_possession(self.player, self.npc)
        context = PresentationContext(self.npc, 1)
        self.assertEqual(party_presenter(context), before)
        catalog = self.registry.render("art", context)["portrait_catalog"]
        self.assertIn(str(self.npc.pk), catalog)
        self.assertIn(str(other.pk), catalog)
        self.assertEqual(status_presenter(context)["actor"]["identity"], str(self.npc.pk))
        roster = self.registry.render("roster", context)
        self.assertTrue(roster["available"])
        owner_row = next(row for row in roster["characters"] if row["current"])
        self.assertEqual(owner_row, owner_before)
        self.assertEqual(owner_row["identity"], self.player.pk)
        self.assertFalse(any(row["identity"] == self.npc.pk for row in roster["characters"]))
        self.assertFalse(roster["switch_locked"])
        self.assertIsNone(roster["lock_reason"])
        with patch("world.rules.account_roster.is_in_active_session", side_effect=lambda actor: actor == self.npc):
            combat_roster = self.registry.render("roster", context)
        self.assertTrue(combat_roster["switch_locked"])
        self.assertEqual(combat_roster["lock_reason"], "戰鬥中無法切換角色")
        self.assertEqual(combat_roster["characters"], roster["characters"])
        release_possession(self.player)
        after = party_presenter(PresentationContext(self.player, 1))
        # The panel's own facts are unchanged by release: the same ordered rows
        # with the same identity/display/HP/bond/membership vocabulary. The
        # only field that may move is `portrait_ref`, because a reference names
        # the current bounded art view's ADMISSION and release leaves the
        # possessed companion unlocated — a remote row keeps the truthful null
        # (the panel never expands the catalog to cover a subject that is not
        # present).
        self.assertEqual(
            [slot["identity"] for slot in after["slots"]],
            [slot["identity"] for slot in before["slots"]],
        )
        for old, new in zip(before["slots"], after["slots"]):
            self.assertEqual(
                {key: value for key, value in old.items() if key != "portrait_ref"},
                {key: value for key, value in new.items() if key != "portrait_ref"},
            )
        # Row 0 is the commander's own row; the companions follow. Release
        # leaves both companions in the owner's room, so each stays admitted to
        # the current art view and keeps its own catalog key. (The assertions
        # are joined by identity because the possession transition may rewrite
        # the binding order.)
        after_rows = {row["identity"]: row for row in after["slots"]}
        self.assertEqual(after_rows[int(self.npc.pk)]["portrait_ref"], str(self.npc.pk))
        self.assertEqual(after_rows[int(other.pk)]["portrait_ref"], str(other.pk))
        self.assertEqual(self.npc.location, self.room1)
        self.assertEqual(other.location, self.room1)
        self.assertEqual(self.registry.render("roster", PresentationContext(self.player, 1)), roster_before)

    def test_possessed_roster_rejects_foreign_or_unbound_owner(self):
        context = PresentationContext(self.npc, 1)
        self.assertFalse(self.registry.render("roster", context)["available"])
        self.npc.account = self.account
        self.npc.db.possessed_by = self.player.pk
        self.assertTrue(self.registry.render("roster", context)["available"])
        self.npc.db.party_member = None
        self.assertFalse(self.registry.render("roster", context)["available"])
        self.assertFalse(self.registry.render("party", context)["available"])
        self.assertIn(self.npc.pk, self.player.db.party)
        self.assertIn(self.player, self.account.characters.all())
        self.npc.db.party_member = self.player.pk
        self.account.characters.remove(self.player)
        self.assertFalse(self.registry.render("roster", context)["available"])
        self.npc.db.possessed_by = None

    def tearDown(self):
        try:
            set_clock_for_testing(None)
            if getattr(self.player.db, "possession", None):
                release_possession(self.player, reason="disconnect")
        except Exception:
            pass
        super().tearDown()

    @covers_requirement(
        "exploration-affordances::the-shared-read-only-affordance-vocabulary-supports-possessed-shop-access"
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
        "exploration-affordances::the-shared-read-only-affordance-vocabulary-supports-possessed-shop-access"
    )
    def test_possessed_actor_keeps_shop_navigation_and_omits_guild(self):
        """Shop navigation stays enabled; guild navigation is absent everywhere."""
        from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
        from typeclasses.npcs import NPC
        from world.rules.dialogue import GUILD_STAFF_DIALOGUE_KEY

        staff = create_object(NPC, key="公會職員", location=self.room1)
        staff.components.add(
            GuildStaff.create(
                staff,
                service_id="t_possession_staff",
                branch_key="t_possession_branch",
            )
        )
        staff.components.add(
            ScriptedDialogue.create(staff, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        shop = create_object(NPC, key="行商", location=self.room1)
        shop.components.add(
            Merchant.create(
                shop, service_id="shop", shop_key="t_possession_shop"
            )
        )
        monster = create_object(Monster, key="哥布林", location=self.room1)
        enter_possession(self.player, self.npc)

        vocabulary = exploration_affordances(self.npc)
        navigation = [entry for entry in vocabulary if entry.navigation]
        self.assertEqual([entry.surface for entry in navigation], ["shop"])
        self.assertTrue(navigation[0].enabled)
        self.assertIsNone(navigation[0].disabled_reason)

        talk = [
            entry
            for entry in vocabulary
            if entry.action_id == "explore.talk_scripted"
        ]
        self.assertTrue(talk)
        for entry in talk:
            self.assertFalse(entry.enabled)
            self.assertEqual(entry.disabled_reason[0], REASON_POSSESSED_TALK)
        engage = [entry for entry in vocabulary if entry.action_id == "explore.engage"]
        self.assertEqual(len(engage), 1)
        self.assertEqual(engage[0].disabled_reason[0], REASON_POSSESSED_ENGAGE)
        self.assertIsNotNone(monster.pk)

        context = PresentationContext(actor=self.npc, protocol_version=1)
        exploration = self.registry.render("exploration", context)
        exploration_navigation = [
            affordance
            for target in exploration["interact"]
            for affordance in target["affordances"]
            if affordance.get("kind") == "navigate"
            and affordance.get("surface") in {"guild", "shop"}
        ]
        self.assertEqual(
            [affordance["surface"] for affordance in exploration_navigation],
            ["shop"],
        )
        self.assertTrue(exploration_navigation[0]["enabled"])

        form = self.registry.render("context_actions", context)
        self.assertEqual(form["kind"], "exploration")
        form_navigation = [
            affordance
            for affordance in form["affordances"]
            if affordance.get("navigation") is True
        ]
        self.assertEqual(
            [affordance["surface"] for affordance in form_navigation], ["shop"]
        )
        self.assertTrue(form_navigation[0]["enabled"])
        self.assertFalse(
            any(
                affordance.get("surface") == "guild"
                for affordance in form["affordances"]
            )
        )

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
        self.player.traits.hp.current = 37
        self.npc.traits.hp.current = 81
        status_before = status_presenter(ctx_player)
        services_before = services_presenter(ctx_player)

        # Enter possession
        enter_possession(self.player, self.npc)
        ctx_npc = PresentationContext(actor=self.npc, protocol_version=1)

        # 1. character_presenter: wallet is byte-identical to A's wallet
        char_panel = character_presenter(ctx_npc)
        self.assertTrue(char_panel["available"])
        self.assertEqual(char_panel["wallet"], 5000)
        self.assertEqual(char_panel["wallet"], wallet_before)

        # 2. services_presenter: player.wallet is A's and the payload is
        # identical to the unpossessed one (services v7 carries no personal
        # inventory; party_inventory owns the bag rows).
        serv_panel = services_presenter(ctx_npc)
        self.assertTrue(serv_panel["available"])
        self.assertEqual(serv_panel["player"]["wallet"], 5000)
        self.assertNotIn("inventory", serv_panel)
        self.assertIsNone(serv_panel["shop"])
        self.assertEqual(serv_panel, services_before)

        # 3. status_presenter: name and status belong to A
        stat_panel = status_presenter(ctx_npc)
        self.assertTrue(stat_panel["available"])
        self.assertEqual(stat_panel["actor"]["name"], self.player.key)
        self.assertEqual(stat_panel["actor"]["identity"], str(self.npc.pk))
        self.assertEqual(stat_panel["resources"], status_before["resources"])
        self.assertEqual(stat_panel["conditions"], status_before["conditions"])

        # 4. objectives_presenter: available without error
        obj_panel = objectives_presenter(ctx_npc)
        self.assertTrue(obj_panel["available"])

    @covers_requirement(
        "webclient-status-presentation::equipment-condition-provenance-preserves-independent-sources"
    )
    def test_possession_provenance_uses_resource_owner_equipment(self):
        from contextlib import ExitStack
        from world.rules.rulebook.schema import Rule
        from world.skills.equipment import EquipmentSlot

        enter_possession(self.player, self.npc)
        self.player.db.equipment = {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": ["t_owner"]}
        self.npc.db.equipment = {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": ["t_host"]}
        self.player.sexual.exposure.value = "中等"
        self.npc.sexual.exposure.value = "極高"
        items = {
            key: SimpleNamespace(key=key, modifier_key=key, equipment_slot=EquipmentSlot.ACCESSORY, display_name_zh=label)
            for key, label in (("t_owner", "合成主人護符"), ("t_host", "合成宿主護符"))
        }
        effects = {key: SimpleNamespace(exposure_bias=1, attached_buffs=()) for key in items}
        with ExitStack() as stack:
            stack.enter_context(patch.dict("world.rules.equipment.ITEM_REGISTRY", items))
            stack.enter_context(patch.dict("world.rules.equipment_effects.ITEM_REGISTRY", items))
            stack.enter_context(patch.dict("world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", effects))
            stack.enter_context(patch("world.rules.combat_modifiers._RULES", [
                Rule("t_exposure", {"field": "exposure", "gte": "高"}, {"defense": -15}),
            ]))
            stack.enter_context(
                patch(
                    "world.rules.status_query.conditions.display_for",
                    return_value=SimpleNamespace(label="合成警告", severity="warning"),
                )
            )
            panel = status_presenter(PresentationContext(self.npc, 1))
        self.assertEqual(panel["actor"]["identity"], str(self.npc.pk))
        self.assertEqual(panel["conditions"][0]["provenance"], {
            "kind": "equipment", "equipment_sources": [{"item_key": "t_owner", "label": "合成主人護符"}],
        })

    @covers_requirement(
        "webclient-possession-presentation::the-dispatcher-preserves-talk-and-engage-refusals-during-possession",
    )
    def test_possession_keeps_talk_and_engage_refusals_zero_write(self):
        """Talk opening and combat engagement stay refused while possessed."""
        enter_possession(self.player, self.npc)
        listener = create_object(LLMNPC, key="旁聽者", location=self.room1)
        monster = create_object(Monster, key="哥布林", location=self.room1)
        wallet_before = self.player.db.wallet
        player_inventory = list(self.player.db.inventory)
        npc_inventory = list(self.npc.db.inventory)
        dialogue_before = self.npc.db.dialogue_session
        combat_before = self.player.db.active_combat
        results = (
            _talk_open_adapter(self.npc, {"npc_id": listener.pk}),
            _talk_scripted_adapter(
                self.npc, {"npc_id": listener.pk, "keyword": "問候"}
            ),
            _talk_freeform_adapter(
                self.npc, {"npc_id": listener.pk, "speech": "你好"}
            ),
            _engage_adapter(self.npc, {"monster_id": monster.pk}),
        )
        for result, code in zip(
            results,
            (
                REASON_POSSESSED_TALK,
                REASON_POSSESSED_TALK,
                REASON_POSSESSED_TALK,
                REASON_POSSESSED_ENGAGE,
            ),
        ):
            self.assertEqual(result["outcome"], "rejected")
            self.assertEqual(result["code"], code)
            self.assertEqual(result["message"], POSSESSED_REFUSAL_MESSAGES[code])
        self.assertEqual(self.player.db.wallet, wallet_before)
        self.assertEqual(list(self.player.db.inventory), player_inventory)
        self.assertEqual(list(self.npc.db.inventory), npc_inventory)
        self.assertEqual(self.npc.db.dialogue_session, dialogue_before)
        self.assertEqual(self.player.db.active_combat, combat_before)
        self.assertIsNone(self.npc.db.active_combat)
        self.assertIsNotNone(monster.pk)

    @covers_requirement(
        "shop-economy::purchases-debit-the-party-purse-and-fill-the-recipient-s-bag",
        "shop-economy::sales-draw-from-the-seller-s-unequipped-items-and-credit-the-party-purse",
        "affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths",
        "shop-economy::possessed-trades-use-the-named-bag-and-the-party-purse",
    )
    def test_possessed_shop_trades_settle_normally(self):
        """Web buy/sell use the puppet's bag and the commander's purse."""
        from typeclasses.components import Merchant
        from typeclasses.npcs import NPC
        from world.rules.tests._combat_session_helpers import open_synthetic_scope
        from world.rules.tests._guild_service_probes import (
            install_synthetic_catalog,
            synth_catalog,
            synth_offer_rule,
            synth_shop_config,
        )
        from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS

        open_synthetic_scope(self, "items", "prices", "shops")
        shop_key = next(iter(SYNTH_SHOPS))
        potion = SYNTH_ITEMS["t_ember_spray"].key
        offer = synth_offer_rule(potion, max_stock=10, initial_stock=5)
        install_synthetic_catalog(
            self,
            synth_catalog(
                shop_configs={
                    shop_key: synth_shop_config(
                        shop_key, (potion,), offer_rules=(offer,)
                    )
                }
            ),
        )
        get_world_clock()._persist(12 * 3600)
        merchant_host = create_object(NPC, key="合成商人", location=self.room1)
        merchant = Merchant.create(
            merchant_host, service_id="possession_store", shop_key=shop_key
        )
        merchant_host.components.add(merchant)
        merchant.merchant_stock = {potion: 5}
        enter_possession(self.player, self.npc)
        npc_bag = list(self.npc.db.inventory)
        commander_bag = list(self.player.db.inventory)

        buy_result = _buy_adapter(
            self.npc,
            {
                "item_key": potion,
                "quantity": 2,
                "recipient_id": self.npc.pk,
            },
        )
        self.assertEqual(buy_result["outcome"], "success")
        self.assertEqual(buy_result["code"], "bought")
        self.assertEqual(self.player.db.wallet, 5000 - 2 * offer.buy_copper)
        self.assertEqual(list(self.npc.db.inventory), npc_bag + [potion, potion])
        self.assertEqual(list(self.player.db.inventory), commander_bag)
        self.assertEqual(merchant.merchant_stock[potion], 3)
        self.assertEqual(merchant_host.relations.affinity_for(self.player), 1)
        self.assertFalse(merchant_host.relations.has_record(self.npc))

        sell_result = _sell_adapter(
            self.npc,
            {
                "item_key": potion,
                "quantity": 1,
                "seller_id": self.npc.pk,
            },
        )
        self.assertEqual(sell_result["outcome"], "success")
        self.assertEqual(sell_result["code"], "sold")
        self.assertEqual(
            self.player.db.wallet, 5000 - 2 * offer.buy_copper + offer.sell_copper
        )
        self.assertEqual(list(self.npc.db.inventory), npc_bag + [potion])
        self.assertEqual(merchant.merchant_stock[potion], 4)
        self.assertEqual(merchant_host.relations.affinity_for(self.player), 2)

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

    def _sleeping_possession_with_candidate(self):
        """Possess ``self.npc``, sleep it, and bind one awake candidate."""
        candidate = create_object(LLMNPC, key="接手同伴", location=self.room1)
        candidate.race = "human"
        candidate.apply_race_baseline()
        join_party(candidate, self.player)
        write_fatigue_state(self.npc, 180000, SleepPosture.AWAKE)
        write_fatigue_state(candidate, 360000, SleepPosture.AWAKE)
        enter_possession(self.player, self.npc)
        entry = enter_sleep(self.npc)
        self.assertTrue(entry.handoff_offered)
        return candidate, entry

    @covers_requirement(
        "webclient-possession-presentation::the-possession-controls-complete-the-action-round-trip"
    )
    @covers_requirement(
        "webclient-possession-presentation::browser-and-text-expose-the-same-non-acting-handoff-choices"
    )
    def test_sleep_handoff_adapter_rejects_a_stale_selection_with_current_choices(self):
        """A candidate that left before confirmation changes no control or time."""
        candidate, _entry = self._sleeping_possession_with_candidate()
        before_tick = int(get_world_clock().tick)
        candidate.location = self.room2
        result = _possess_adapter(
            self.npc, {"npc_id": int(candidate.pk)}, session=None
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], REASON_STALE_HANDOFF)
        self.assertNotIn("data", result)
        self.assertEqual(int(get_world_clock().tick), before_tick)
        self.assertEqual(
            self.player.db.possession["npc_dbid"], int(self.npc.pk)
        )

    @covers_requirement(
        "webclient-possession-presentation::the-possession-controls-complete-the-action-round-trip"
    )
    @covers_requirement(
        "webclient-possession-presentation::browser-and-text-expose-the-same-non-acting-handoff-choices"
    )
    def test_sleep_handoff_stale_selection_is_a_protocol_valid_refusal(self):
        """The dispatcher emits the stable refusal, never an internal error."""
        candidate, _entry = self._sleeping_possession_with_candidate()
        candidate.location = self.room2
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": self.coordinator.epoch,
            "request_id": "req-handoff-stale-choice",
            "base_revision": self.coordinator.revision,
            "action_id": "explore.possess",
            "payload": {"npc_id": int(candidate.pk)},
        }
        handle_ui_action(
            self.session,
            self.npc,
            envelope,
            self.action_registry,
            self.registry,
        )
        result = next(
            kw["ui_action_result"][0][0]
            for _args, kw in reversed(self.sent_messages)
            if "ui_action_result" in kw
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], REASON_STALE_HANDOFF)
        self.assertNotIn("data", result)
        self.assertEqual(
            self.player.db.possession["npc_dbid"], int(self.npc.pk)
        )

    @covers_requirement(
        "webclient-possession-presentation::the-possession-controls-complete-the-action-round-trip"
    )
    @covers_requirement(
        "webclient-possession-presentation::browser-and-text-expose-the-same-non-acting-handoff-choices"
    )
    def test_sleep_handoff_adapter_commits_and_repoints_the_epoch(self):
        """A lawful candidate moves control once and the old epoch is refused."""
        candidate, _entry = self._sleeping_possession_with_candidate()
        before_tick = int(get_world_clock().tick)
        epoch_before = self.coordinator.epoch
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": self.coordinator.epoch,
            "request_id": "req-handoff-1",
            "base_revision": self.coordinator.revision,
            "action_id": "explore.possess",
            "payload": {"npc_id": int(candidate.pk)},
        }
        handle_ui_action(
            self.session,
            self.npc,
            envelope,
            self.action_registry,
            self.registry,
        )
        result = next(
            kw["ui_action_result"][0][0]
            for _args, kw in reversed(self.sent_messages)
            if "ui_action_result" in kw
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "handoff_pending")
        self.assertIn("正在交接控制權", result["message"])
        self.clock.advance(0.1)
        self.assertEqual(self.session.puppet, candidate)
        self.assertEqual(self.player.db.possession["npc_dbid"], int(candidate.pk))
        self.assertEqual(self.session.ndb.elosern_actor_id, str(candidate.pk))
        self.assertNotEqual(self.coordinator.epoch, epoch_before)
        self.assertIs(read_fatigue_state(self.npc).posture, SleepPosture.VOLUNTARY)
        self.assertIsNone(self.npc.db.possessed_by)
        self.assertEqual(int(get_world_clock().tick), before_tick)

        # The retired epoch can no longer act, and control stays put.
        stale_envelope = {
            "protocol_version": 1,
            "presentation_epoch": epoch_before,
            "request_id": "req-handoff-stale",
            "base_revision": self.coordinator.revision,
            "action_id": "explore.possess",
            "payload": {"npc_id": int(self.npc.pk)},
        }
        handle_ui_action(
            self.session,
            candidate,
            stale_envelope,
            self.action_registry,
            self.registry,
        )
        self.clock.advance(0.1)
        stale = next(
            kw["ui_action_result"][0][0]
            for _args, kw in reversed(self.sent_messages)
            if "ui_action_result" in kw
        )
        self.assertEqual(stale["outcome"], "stale")
        self.assertEqual(self.player.db.possession["npc_dbid"], int(candidate.pk))

    @covers_requirement(
        "webclient-possession-presentation::the-possession-controls-complete-the-action-round-trip"
    )
    @covers_requirement(
        "webclient-possession-presentation::browser-and-text-expose-the-same-non-acting-handoff-choices"
    )
    def test_sleep_handoff_admission_never_claims_completion_on_failure(self):
        """A candidate that turns stale before execution gets a refusal, not success."""
        candidate, _entry = self._sleeping_possession_with_candidate()
        admission = _possess_adapter(
            self.npc, {"npc_id": int(candidate.pk)}, session=self.session
        )
        self.assertEqual(admission["outcome"], "success")
        self.assertEqual(admission["code"], "handoff_pending")
        candidate.location = self.room2
        self.clock.advance(0.1)
        self.assertEqual(self.player.db.possession["npc_dbid"], int(self.npc.pk))
        self.assertEqual(self.session.puppet, self.npc)
        messages = []
        for args, kw in self.sent_messages:
            if kw.get("text") and kw["text"][0]:
                messages.append(str(kw["text"][0][0]))
            elif args:
                messages.append(str(args[0]))
        self.assertTrue(
            any("交接選項已經失效" in line for line in messages), messages
        )

    @covers_requirement(
        "time-skip-commands::recovery-waiting-preserves-skip-safety"
    )
    @covers_requirement(
        "webclient-possession-presentation::browser-and-text-expose-the-same-non-acting-handoff-choices"
    )
    def test_wait_adapter_recovers_a_sleeping_controlled_body(self):
        """Recovery waiting stays available without any handoff selection."""
        self._sleeping_possession_with_candidate()
        reserve_before = read_fatigue_state(self.npc).reserve_units
        before_tick = int(get_world_clock().tick)
        result = _wait_adapter(self.npc, {"seconds": 600})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(int(get_world_clock().tick) - before_tick, 600)
        self.assertEqual(
            read_fatigue_state(self.npc).reserve_units,
            min(reserve_before + 600 * 12, 360000),
        )
        self.assertIs(
            read_fatigue_state(self.npc).posture, SleepPosture.VOLUNTARY
        )
        self.assertEqual(self.player.db.possession["npc_dbid"], int(self.npc.pk))

        # An explicit continuation wakes the body only after the committed sleep.
        wake = _wait_adapter(self.npc, {"sleep": True})
        self.assertEqual(wake["outcome"], "success")
        self.assertIs(read_fatigue_state(self.npc).posture, SleepPosture.AWAKE)
        self.assertEqual(self.player.db.possession["npc_dbid"], int(self.npc.pk))


    @covers_requirement(
        "webclient-party-panel::the-party-window-member-tab-offers-possession-controls-per-companion"
    )
    def test_party_panel_schema_untouched_and_companion_affordance_present(self):
        """party panel payload schema carries no possession field; vocabulary offers possess."""
        # The party v3 shape carries no possession-specific field: the panel
        # adds the general quota and the viewed member, and each row carries
        # the version-3 vocabulary (the commander row included).
        ctx = PresentationContext(actor=self.player, protocol_version=1)
        panel = party_presenter(ctx)
        self.assertEqual(panel["schema_version"], 3)
        self.assertTrue(panel["available"])
        self.assertEqual(
            set(panel.keys()),
            {
                "schema_version",
                "available",
                "general_quota",
                "slots",
                "viewed_member_id",
            },
        )

        for slot in panel["slots"]:
            # Slot is the exact version-3 row contract.
            self.assertEqual(
                set(slot.keys()),
                {
                    "identity", "display_name", "portrait_ref", "bond_stage",
                    "hp_current", "hp_maximum",
                    "mp_current", "mp_maximum", "sp_current", "sp_maximum",
                    "role", "knocked_out", "unread", "membership",
                },
            )
            self.assertNotIn("possessed", slot)
            self.assertNotIn("possess", slot)
