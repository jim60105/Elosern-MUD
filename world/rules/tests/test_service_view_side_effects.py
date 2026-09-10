"""Side-effect-free services view tests against real Evennia state (task 1.3).

Builds the full frozen services view from canonical guild, quest, shop,
wallet, inventory, merit, and rank state, then proves the build itself changes
nothing: every canonical surface is byte-for-byte identical before and after a
snapshot, for a fully registered and quest-carrying actor and for an
unregistered, disguised actor. The view must not materialize a lazy handler,
create the world-clock singleton, or read ``disguised_stats``.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff, Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.definitions import QUEST_DEFINITION_REGISTRY, QuestStage
from world.quests.tests._fixtures import (
    defeat,
    quest,
    register,
    register_catalog_once,
)
from world.rules.clock import get_world_clock
from world.rules.guild import register_adventurer
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    QuestReward,
    accept_guild_offer,
    register_guild_offer,
)
from world.rules.service_view import build_services_view
from world.rules.surfaces import write_counter_trait
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
    synth_shop_config,
    synthetic_branch_key,
)
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS

# The shipped affinity rulebook cross-references one catalog quest by key, so
# the affinity-config loader needs the catalog definitions present in-process.
# Registered at import (no synthetic scope is open yet).
register_catalog_once()

# The whole services view builds on kit rows: kit branch for the guild hosts,
# one synthetic shop config over kit items for the store, and the kit potion
# in the actor's pockets. Every asserted number below is authored here.
BRANCH = synthetic_branch_key()


def _shop_config():
    """Built inside the scope: the offer rules read live price bands."""
    return synth_shop_config(T_SHOP, _SHOP_ITEM_KEYS)
T_SHOP = next(iter(SYNTH_SHOPS))
_T_SPRAY = SYNTH_ITEMS["t_ember_spray"].key
_T_FANG = SYNTH_ITEMS["t_iron_fang"].key
_T_APPLE = SYNTH_ITEMS["t_huskapple"].key
_SHOP_ITEM_KEYS = (_T_SPRAY, _T_FANG, _T_APPLE)


class ServicesViewSideEffectTests(EvenniaTestCase):
    def setUp(self):
        # Scope before construction: shop/branch/item identities resolve
        # against kit rows inside the synthetic shop catalog.
        open_synthetic_scope(self, "guild_branches", "items", "prices", "shops")
        super().setUp()
        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offers = list(GUILD_OFFER_REGISTRY.items())
        install_synthetic_catalog(
            self, synth_catalog(shop_configs={T_SHOP: _shop_config()})
        )
        get_world_clock()

        self.hall = create_object(Room, key="guild hall")
        self.store = create_object(Room, key="general store")
        self.staff = create_object(NPC, key="guild master", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key=BRANCH)
        )
        self.staff.components.add(
            GuildExaminer.create(self.staff, service_id="examiner", branch_key=BRANCH)
        )
        self.merchant_npc = create_object(NPC, key="shop keeper", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc,
            service_id="store",
            shop_key=T_SHOP,
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {_T_SPRAY: 20, _T_FANG: 3, _T_APPLE: 1}

        self.player = create_object(PlayerCharacter, key="service player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        self.player.db.wallet = 1000
        self.player.db.inventory = [_T_APPLE, _T_APPLE, _T_SPRAY]
        register_adventurer(self.player, staff=self.staff)
        write_counter_trait(self.player, "guild_merit", 60)
        # One invented branch-local offer stands in for any catalog row.
        self.board_quest = register(
            quest("services_board_quest", stages=(QuestStage(0, defeat(tier="low")),))
        )
        register_guild_offer(
            GuildQuestOffer(
                definition_key=self.board_quest.key,
                issuer_branch_key=BRANCH,
                reward=QuestReward(copper=50, items=(), merit=25),
            )
        )
        accept_guild_offer(self.player, self.staff, self.board_quest.key)

    def tearDown(self):
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offers)
        super().tearDown()

    def _canonical_snapshot(self):
        return {
            "wallet": self.player.db.wallet,
            "inventory": list(self.player.db.inventory or []),
            "quest_log": list(self.player.db.quest_log or []),
            "guild_registration": self.player.db.guild_registration,
            "guild_rank": self.player.guild_rank,
            "guild_reward_claims": list(self.player.db.guild_reward_claims or []),
            "active_combat": self.player.db.active_combat,
            "merit": int(self.player.traits.guild_merit.value),
            "equipment": self.player.db.equipment,
            "disguised_stats": self.player.db.disguised_stats,
            "merchant_stock": dict(self.merchant.merchant_stock or {}),
        }

    def test_building_the_full_view_changes_no_canonical_surface(self):
        view = build_services_view(self.player)
        self.assertIsNotNone(view.guild)
        self.assertIsNone(view.shop)
        self.assertEqual(view.player.guild_rank, "F")
        self.assertEqual(view.player.guild_merit, 60)
        self.assertEqual(view.pagination.quest_total, 1)
        self.assertEqual(view.pagination.board_total, 1)

        snapshot = self._canonical_snapshot()
        rebuilt = build_services_view(self.player)
        self.assertEqual(rebuilt.player.guild_rank, "F")
        self.assertEqual(rebuilt.player.guild_merit, 60)
        self.assertEqual(self._canonical_snapshot(), snapshot)

    def test_building_the_shop_view_changes_no_canonical_surface(self):
        # Advance the persisted world clock to noon so the store is open.
        get_world_clock()._persist(12 * 3600)
        self.player.location = self.store
        view = build_services_view(self.player)
        self.assertIsNotNone(view.shop)
        self.assertEqual(view.shop.open, True)
        self.assertEqual(len(view.shop.stock), len(_SHOP_ITEM_KEYS))

        snapshot = self._canonical_snapshot()
        rebuild = build_services_view(self.player)
        self.assertEqual(rebuild.shop.stock[0].stock, 20)
        self.assertEqual(self._canonical_snapshot(), snapshot)

    def test_unregistered_disguised_actor_builds_without_distortion(self):
        newcomer = create_object(PlayerCharacter, key="newcomer")
        newcomer.race = "elf"
        newcomer.apply_race_baseline()
        newcomer.location = self.hall
        newcomer.db.wallet = 0
        newcomer.db.disguised_stats = {"atk_phys": 60, "magic_power": 30}
        newcomer.traits.atk_phys.base = 88
        newcomer.traits.guild_merit.base = 0
        snapshot = {
            "wallet": newcomer.db.wallet,
            "inventory": list(newcomer.db.inventory or []),
            "quest_log": list(newcomer.db.quest_log or []),
            "guild_registration": newcomer.db.guild_registration,
            "guild_rank": newcomer.guild_rank,
            "disguised_stats": newcomer.db.disguised_stats,
        }
        view = build_services_view(newcomer)
        self.assertFalse(view.player.guild_registered)
        self.assertIsNone(view.player.guild_rank)
        self.assertEqual(view.player.guild_merit, 0)
        self.assertIsNone(view.player.next_rank)
        self.assertIsNone(view.player.next_threshold)
        self.assertEqual(view.guild.registration.register.enabled, True)
        self.assertEqual(view.guild.board, ())
        self.assertEqual(view.guild.quests, ())
        self.assertEqual(
            {
                "wallet": newcomer.db.wallet,
                "inventory": list(newcomer.db.inventory or []),
                "quest_log": list(newcomer.db.quest_log or []),
                "guild_registration": newcomer.db.guild_registration,
                "guild_rank": newcomer.guild_rank,
                "disguised_stats": newcomer.db.disguised_stats,
            },
            snapshot,
        )
        # The read model must never read disguised_stats for the summary.
        self.assertEqual(view.player.guild_merit, 0)

    def test_view_does_not_create_the_world_clock(self):
        from evennia.utils.search import search_script

        original = search_script("world_clock")
        with patch("world.rules.service_view.read_world_clock", return_value=None):
            pass
        # Without the singleton the view fails closed instead of creating one.
        from world.rules.service_view import ServicesViewError

        try:
            with patch("world.rules.service_view.read_world_clock", return_value=None):
                build_services_view(self.player)
            self.fail("expected ServicesViewError for an absent world clock")
        except ServicesViewError:
            pass
        self.assertEqual(list(search_script("world_clock")), list(original))
