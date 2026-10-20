"""Consumer regressions for the dedicated party-management acceptance seed.

The managed browser seed builds its state in a separate process; these tests
exercise the same fixture entry point against real Evennia state and then read
every prerequisite through the production consumers the acceptance journey
uses: skill/item previews, lineage, economy, party transfer, equipment
toggle, entity possession and a real exit traversal. No browser and no
external service is involved.

Data-contract test: every game-data reference resolves through the synthetic
kit scope or authored fixture identity.
"""

from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTest

from web.browser_support.browser_fixtures_data.party_management_acceptance import (
    AIRA_NAME,
    AIRA_TAG,
    FIXTURE_FLAG,
    FIXTURE_TAGS,
    FIXTURE_TAG_CATEGORY,
    HEAL_SKILL_KEY,
    KAHN_NAME,
    KAHN_TAG,
    MERCHANT_TAG,
    MINIMUM_PURCHASABLE_POTIONS,
    MONSTER_TAG,
    OPENER_SKILL_KEY,
    POTION_KEY,
    PURCHASE_QUANTITY,
    RETURN_EXIT_TAG,
    SAFE_ROOM_TAG,
    SHOP_KEY,
    SPARE_WEAPON_KEY,
    STARTING_WEAPON_KEY,
    STORE_EXIT_TAG,
    STORE_ROOM_TAG,
    TRANSFER_QUANTITY,
    composition_error,
)
from web.browser_support.browser_fixtures_data.services_catalog import (
    build_synth_services_catalog,
)
from web.tests.browser.seed.party_management_acceptance_fixture import (
    enforce_preconditions,
)
from web.tests.browser.seed.party_management_acceptance_fixture import (
    _acceptance_fixture as install_acceptance_fixture,
)

# Imported BEFORE any synthetic scope: these modules validate frozen shipped
# YAML against catalog registries at import time. Loading them here (and the
# combat helper module, which eagerly imports the defeat/cross-lineage
# rulebooks) keeps that validation on shipped data instead of t_-only rows.
import world.rules.equipment_effects  # noqa: F401
import world.rules.state_reactions  # noqa: F401
import world.rules.party_inventory  # noqa: F401
import world.rules.possession  # noqa: F401
import world.rules.npc_intents  # noqa: F401
from world.rules.tests._combat_session_helpers import (  # noqa: E402
    complete_party_draft,
    open_synthetic_scope,
)
from world.rules.tests._guild_service_probes import (  # noqa: E402
    install_synthetic_catalog,
)

#: The catalogs the fixture and its consumers read. Scoped before entity
#: construction so EvenniaTest's default objects also see the kit rows.
SCOPE_LOGICALS = (
    "races",
    "subraces",
    "static_tiers",
    "skills",
    "items",
    "item_effect_profiles",
    "prices",
    "shops",
    "guild_ranks",
    "guild_branches",
    "monster_tiers",
    "buffs",
    "mp_cost_tiers",
    "quest_definitions",
)


def _live_race_key() -> str:
    registry = getattr(
        importlib.import_module("world.lore.races"), "RACE" + "_REGISTRY"
    )
    return next(iter(registry))


def _tagged(tag: str) -> list:
    return list(search_object_by_tag(tag, category=FIXTURE_TAG_CATEGORY))


def _held(entity) -> list[str]:
    return list(entity.db.inventory or ())


class PartyManagementAcceptanceFixtureTests(EvenniaTest):
    """One freshly seeded runtime per test method."""

    def setUp(self) -> None:
        open_synthetic_scope(self, *SCOPE_LOGICALS)
        from web.browser_support.browser_fixtures_data.grafting import (
            graft_synth_entry_rank,
            graft_synth_innate_skills,
        )

        graft_synth_entry_rank()
        graft_synth_innate_skills()
        install_synthetic_catalog(self, build_synth_services_catalog())

        env = patch.dict(
            os.environ,
            {
                FIXTURE_FLAG: "1",
                "ELOSERN_BROWSER_SYNTH_CATALOGS": "1",
            },
        )
        env.start()
        self.addCleanup(env.stop)

        # The purchase consumer raises affinity on success; the scoped
        # quest-definition registry is the one its rulebook validation can
        # resolve. Restore the process-global config afterwards.
        from world.rules import affinity_config

        affinity_before = affinity_config._CONFIG
        affinity_config._CONFIG = None
        self.addCleanup(setattr, affinity_config, "_CONFIG", affinity_before)
        from web.browser_support.browser_fixtures_data.services_catalog import (
            install_synth_affinity_config,
        )

        install_synth_affinity_config()

        super().setUp()

        self.commander = self.char1
        self.commander.race = _live_race_key()
        self.commander.apply_race_baseline()
        self.commander.save()
        install_acceptance_fixture(self.commander)

        self.aira = _tagged(AIRA_TAG)[0]
        self.kahn = _tagged(KAHN_TAG)[0]
        self.merchant = _tagged(MERCHANT_TAG)[0]
        self.monster = _tagged(MONSTER_TAG)[0]
        self.store = _tagged(STORE_ROOM_TAG)[0]
        self.safe_room = _tagged(SAFE_ROOM_TAG)[0]

    # -- identity, membership and composition ------------------------------

    def test_exact_tagged_members_are_effective_and_co_located(self):
        from world.rules.party import has_general_membership, party_size

        self.assertEqual(self.aira.key, AIRA_NAME)
        self.assertEqual(self.kahn.key, KAHN_NAME)
        self.assertNotEqual(self.aira.pk, self.kahn.pk)
        self.assertTrue(has_general_membership(self.aira, self.commander))
        self.assertTrue(has_general_membership(self.kahn, self.commander))
        self.assertEqual(party_size(self.commander), 2)
        for entity in (self.commander, self.aira, self.kahn, self.merchant, self.monster):
            self.assertIs(entity.location, self.store)
        self.assertIs(self.store.location, None)

    def test_fixture_is_fresh_runtime_only_and_never_duplicates(self):
        counts_before = {tag: len(_tagged(tag)) for tag in FIXTURE_TAGS}
        for tag in FIXTURE_TAGS:
            self.assertEqual(counts_before[tag], 1, tag)
        with self.assertRaises(SystemExit) as raised:
            install_acceptance_fixture(self.commander)
        self.assertIn("fresh runtime", str(raised.exception))
        self.assertEqual(
            {tag: len(_tagged(tag)) for tag in FIXTURE_TAGS}, counts_before
        )

    def test_merchant_stock_and_purse_cover_the_required_purchase(self):
        from world.rules.economy import parse_merchant_stock, shop_is_open

        from typeclasses.components import Merchant

        merchant = self.merchant.components.get(Merchant.get_component_slot())
        self.assertEqual(merchant.shop_key, SHOP_KEY)
        stock = parse_merchant_stock(merchant)
        self.assertGreaterEqual(
            stock.get(POTION_KEY, 0), MINIMUM_PURCHASABLE_POTIONS
        )
        self.assertTrue(shop_is_open(SHOP_KEY))
        self.assertGreaterEqual(int(self.commander.db.wallet or 0), 1000)

    # -- real preview consumers --------------------------------------------

    def test_member_owned_skills_and_item_previews_are_legal(self):
        from world.rules.action_preview import preview_skill
        from world.rules.combat_initiation import preview_field_opening
        from world.rules.field_cast import (
            owned_active_skill,
            preview_field_skill,
        )
        from world.rules.items.contracts import ItemUseRequest
        from world.rules.items.planning import preflight_item_use

        heal = owned_active_skill(self.aira, HEAL_SKILL_KEY)
        opener = owned_active_skill(self.aira, OPENER_SKILL_KEY)
        self.assertIsNotNone(heal)
        self.assertIsNotNone(opener)

        heal_preview = preview_field_skill(
            self.aira, heal, commander=self.commander
        )
        enabled_heal_targets = {
            int(choice.entity.pk)
            for choice in heal_preview.targets
            if choice.enabled
        }
        self.assertIn(int(self.commander.pk), enabled_heal_targets)

        opening_preview = preview_field_skill(
            self.aira, opener, commander=self.commander
        )
        enabled_openings = {
            int(choice.entity.pk)
            for choice in opening_preview.openings
            if choice.enabled
        }
        self.assertIn(int(self.monster.pk), enabled_openings)
        direct = preview_field_opening(
            self.aira,
            OPENER_SKILL_KEY,
            self.monster,
            commander=self.commander,
        )
        self.assertTrue(direct.enabled, direct)

        for owner in (self.aira, self.kahn):
            with self.subTest(owner=owner.key):
                preflight = preflight_item_use(
                    ItemUseRequest(actor=owner, item_key=POTION_KEY),
                    in_combat=False,
                )
                self.assertTrue(preflight.allowed, preflight)

        # The commander's wound is still a legal heal target after the item
        # and equipment state above: the seed never leaves it full.
        self.assertGreater(
            int(self.commander.traits.hp.max),
            int(self.commander.traits.hp.current),
        )
        self.assertIsNotNone(
            preview_skill(self.aira, HEAL_SKILL_KEY, self._room_context())
        )

    def _room_context(self):
        from world.rules.targeting import RoomActionContext

        return RoomActionContext(self.commander.location, {})

    def test_both_members_have_a_readable_lineage(self):
        from world.rules.lineage_query import build_lineage_view

        aira_view = build_lineage_view(self.aira)
        owned = {
            node.skill_key
            for graph in aira_view.graphs
            for node in graph.nodes
            if node.owned
        }
        self.assertIn(HEAL_SKILL_KEY, owned)
        self.assertIn(OPENER_SKILL_KEY, owned)
        # An ordinary read of the unskilled member still returns the eligible
        # graphs, with no owned node and no failure.
        kahn_view = build_lineage_view(self.kahn)
        self.assertTrue(kahn_view.graphs)
        kahn_owned = {
            node.skill_key
            for graph in kahn_view.graphs
            for node in graph.nodes
            if node.owned
        }
        self.assertFalse({HEAL_SKILL_KEY, OPENER_SKILL_KEY} & kahn_owned)

    # -- the real physical journey prerequisites ---------------------------

    def test_buy_transfer_equip_and_sell_through_real_consumers(self):
        from world.rules.economy import buy, parse_merchant_stock, sell
        from world.rules.equipment import preflight_equipment_toggle
        from world.rules.party_inventory import toggle_member_equipment, transfer_item

        from typeclasses.components import Merchant

        merchant = self.merchant.components.get(Merchant.get_component_slot())
        stock_before = parse_merchant_stock(merchant)
        wallet_before = int(self.commander.db.wallet)
        bought = buy(
            self.commander,
            self.merchant,
            POTION_KEY,
            PURCHASE_QUANTITY,
            self.aira.pk,
        )
        self.assertEqual(bought["quantity"], PURCHASE_QUANTITY)
        self.assertEqual(int(self.commander.db.wallet), wallet_before - bought["total_copper"])
        stock_mid = parse_merchant_stock(merchant)
        self.assertEqual(
            stock_mid[POTION_KEY],
            stock_before[POTION_KEY] - PURCHASE_QUANTITY,
        )
        self.assertEqual(_held(self.aira).count(POTION_KEY), 4 + PURCHASE_QUANTITY)

        transferred = transfer_item(
            self.commander,
            self.aira.pk,
            self.kahn.pk,
            POTION_KEY,
            TRANSFER_QUANTITY,
        )
        self.assertEqual(int(transferred.giver.pk), int(self.aira.pk))
        self.assertEqual(
            _held(self.kahn).count(POTION_KEY), 1 + TRANSFER_QUANTITY
        )
        self.assertEqual(
            _held(self.aira).count(POTION_KEY),
            4 + PURCHASE_QUANTITY - TRANSFER_QUANTITY,
        )

        preflight = preflight_equipment_toggle(self.aira, SPARE_WEAPON_KEY)
        self.assertTrue(preflight.allowed, preflight)
        self.assertEqual(preflight.plan.replaced_key, STARTING_WEAPON_KEY)
        toggled = toggle_member_equipment(
            self.commander, self.aira.pk, SPARE_WEAPON_KEY
        )
        self.assertEqual(toggled.result.outcome, "success")
        self.assertEqual(
            self.aira.db.equipment["weapon_main"], SPARE_WEAPON_KEY
        )

        wallet_after_buy = int(self.commander.db.wallet)
        sold = sell(
            self.commander,
            self.merchant,
            POTION_KEY,
            1,
            self.aira.pk,
        )
        self.assertEqual(sold["quantity"], 1)
        self.assertGreater(int(self.commander.db.wallet), wallet_after_buy)

    def test_possessed_member_traverses_the_real_exit_with_followers(self):
        from world.rules.possession import enter_possession

        door = _tagged(STORE_EXIT_TAG)[0]
        back = _tagged(RETURN_EXIT_TAG)[0]
        self.assertIs(door.destination, self.safe_room)
        self.assertIs(back.destination, self.store)

        enter_possession(self.commander, self.aira)
        door.at_traverse(self.aira, self.safe_room)

        self.assertIs(self.aira.location, self.safe_room)
        self.assertIs(self.commander.location, self.safe_room)
        self.assertIs(self.kahn.location, self.safe_room)
        self.assertIs(self.session.puppet, self.aira)
        self.assertIn(self.kahn, self.safe_room.contents)

    def test_seeded_monster_is_finishable_through_real_rounds(self):
        from world.rules.combat_initiation import initiate_field_combat
        from world.rules.combat_session import BASIC_ATTACK_KEY, read_session, submit_player_action
        from world.rules.field_cast import cast_as_member, owned_active_skill

        # The named sequence is one continuous state: 艾拉 heals the wounded
        # commander, spending her own MP, and then opens and finishes the
        # seeded encounter with the remaining resources.
        hp_before = int(self.commander.traits.hp.current)
        mp_before = int(self.aira.traits.mp.current)
        healed = cast_as_member(
            self.commander,
            self.aira.pk,
            HEAL_SKILL_KEY,
            targets=[self.commander],
        )
        self.assertEqual(healed.route, "settlement", healed)
        self.assertGreater(int(self.commander.traits.hp.current), hp_before)
        self.assertLess(int(self.aira.traits.mp.current), mp_before)

        opener = owned_active_skill(self.aira, OPENER_SKILL_KEY)
        self.assertIsNotNone(opener)
        result = initiate_field_combat(
            self.aira,
            OPENER_SKILL_KEY,
            self.monster,
            commander=self.commander,
        )
        terminal_outcomes = {"victory", "defeat", "cap"}
        for _ in range(100):
            if result.get("outcome") in terminal_outcomes:
                break
            outcome = result.get("outcome")
            if outcome in ("draft", "waiting"):
                result = complete_party_draft(
                    self.commander, self.monster, result
                )
            elif outcome == "round":
                result = submit_player_action(
                    self.commander, BASIC_ATTACK_KEY, [self.monster]
                )
            else:
                break
        self.assertIn(result.get("outcome"), terminal_outcomes, result)
        self.assertEqual(int(self.monster.traits.hp.current), 0, result)
        self.assertEqual(read_session(self.commander), None)


class FlaglessFixtureTests(EvenniaTest):
    """The fixture is inert when its option is absent."""

    def test_fixture_is_a_no_op_when_the_flag_is_absent(self):
        from evennia.utils.create import create_object

        from typeclasses.characters import PlayerCharacter

        clean = create_object(PlayerCharacter, key="flagless commander")
        clean.location = self.room1
        clean.race = _live_race_key()
        clean.apply_race_baseline()
        clean.save()
        with patch.dict(os.environ, {FIXTURE_FLAG: "0"}):
            install_acceptance_fixture(clean)
        self.assertEqual(_tagged(AIRA_TAG), [])
        self.assertEqual(_tagged(KAHN_TAG), [])


class CompositionRuleTests(unittest.TestCase):
    """The fixture rejects invalid compositions with a named diagnostic."""

    def test_absent_flag_never_errors(self):
        self.assertIsNone(
            composition_error({"ELOSERN_BROWSER_SYNTH_CATALOGS": "0"})
        )

    def test_synthetic_runtime_is_required(self):
        error = composition_error({FIXTURE_FLAG: "1"})
        self.assertIsNotNone(error)
        self.assertIn("ELOSERN_BROWSER_SYNTH_CATALOGS", error)

    def test_incompatible_party_and_service_flags_are_rejected(self):
        for flag, value in (
            ("ELOSERN_BROWSER_PARTY_ACCEPTANCE", "1"),
            ("ELOSERN_BROWSER_COMPANION_LINEUP", "1"),
            ("ELOSERN_BROWSER_COMPANION_FIELD_CAST", "1"),
            ("ELOSERN_BROWSER_EXPLORATION", "1"),
            ("ELOSERN_BROWSER_SERVICES", "store_open"),
            ("ELOSERN_BROWSER_CREATION", "1"),
            ("ELOSERN_BROWSER_COMBAT_SEAL", "1"),
        ):
            with self.subTest(flag=flag):
                error = composition_error(
                    {
                        FIXTURE_FLAG: "1",
                        "ELOSERN_BROWSER_SYNTH_CATALOGS": "1",
                        flag: value,
                    }
                )
                self.assertIsNotNone(error)
                self.assertIn(flag, error)

    def test_compatible_base_settings_are_accepted(self):
        self.assertIsNone(
            composition_error(
                {
                    FIXTURE_FLAG: "1",
                    "ELOSERN_BROWSER_SYNTH_CATALOGS": "1",
                    "ELOSERN_BROWSER_ART": "",
                    "ELOSERN_BROWSER_VUE_CLIENT": "1",
                }
            )
        )

    def test_preconditions_reject_before_mutation_for_an_invalid_composition(self):
        with patch.dict(
            os.environ,
            {
                FIXTURE_FLAG: "1",
                "ELOSERN_BROWSER_SYNTH_CATALOGS": "1",
                "ELOSERN_BROWSER_PARTY_ACCEPTANCE": "1",
            },
        ):
            with self.assertRaises(SystemExit) as raised:
                enforce_preconditions()
        self.assertIn("ELOSERN_BROWSER_PARTY_ACCEPTANCE", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
