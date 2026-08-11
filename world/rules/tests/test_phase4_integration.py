"""Offline Phase-4 milestone: register-to-rank-promotion command-level walk (task 12)."""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from commands.action import CmdCast
from commands.combat import CmdEngage
from commands.guild import (
    CmdGuildAccept,
    CmdGuildList,
    CmdGuildRegister,
    CmdGuildTurnIn,
)
from commands.economy import CmdBuy, CmdInventory
from world.maps.bootstrap import (
    GENERAL_STORE_TAG,
    GUILD_HALL_TAG,
    sync_grid,
    sync_service_interiors,
)
from world.quests.catalog import register_catalog
from world.quests.runtime import read_records
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.clock import AdvanceSource, WorldClock, get_world_clock
from world.rules.combat_session import read_session
from world.rules.guild_config import (
    CATALOG,
    load_catalog_into_cache,
    register_catalog_offers,
)
from world.rules.guild_economy import sync_guild_economy
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.surfaces import read_counter_trait
from world.rules.traits import get_display_value
from world.rules.tests.combat_fixtures import BattlefieldIsolation


class Phase4Isolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        register_catalog()
        from world.quests.bootstrap import sync_quest_runtime

        sync_quest_runtime()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_service_interiors()
        self._previous_catalog = CATALOG
        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        global CATALOG
        CATALOG = self._previous_catalog
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()


class OfflinePhase4MilestoneTests(BattlefieldIsolation, Phase4Isolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        sync_guild_economy()
        # Compact deterministic balance: E threshold 50 (catalog), intro hunt
        # reward 25 merit per completion, so two completions reach E.
        self.guild_hall = search_object_by_tag(GUILD_HALL_TAG)[0]
        self.store = search_object_by_tag(GENERAL_STORE_TAG)[0]
        self.player = self.char1
        self.player.location = self.guild_hall
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.db.wallet = 0

    def _register(self):
        self.call(CmdGuildRegister(), "", "你已註冊為冒險者")
        self.assertEqual(self.player.guild_rank, "F")

    def _accept_intro(self):
        self.call(CmdGuildList(), "", "任務板")
        self.call(CmdGuildAccept(), "introductory_hunt", "你接取了任務")

    def _spawn_hunt_monster(self, hp=1):
        from evennia.objects.models import ObjectDB

        for existing in ObjectDB.objects.filter(db_key__startswith="hunt-goblin"):
            if existing is not None:
                existing.delete()
        monster = create_object(Monster, key="hunt-goblin", location=self.player.location)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = hp
        monster.traits.hp.current = hp
        return monster

    def _complete_hunt(self):
        monster = self._spawn_hunt_monster()
        self.call(CmdEngage(), monster.key, "戰鬥開始")
        self.assertIsNotNone(self.player.db.active_combat)
        with patch("world.rules.combat.roll_d100", return_value=100):
            self.call(CmdCast(), f"basic_attack={monster.key}", None)
        self.assertIsNone(self.player.db.active_combat)
        from world.quests.runtime import QuestState

        records = read_records(self.player)
        completed = [
            r
            for r in records
            if r.definition_key == "introductory_hunt"
            and r.state is QuestState.COMPLETED
        ]
        self.assertTrue(completed, "hunt did not auto-complete")

    def _turn_in(self):
        quest_id = self.player.db.quest_log[-1]["quest_id"]
        self.call(CmdGuildTurnIn(), quest_id, "你回報了任務")

    def test_register_to_promotion_loop(self):
        # 1. Registration + first hunt completion + turn-in (exact reward).
        self._register()
        self._accept_intro()
        self._complete_hunt()
        self._turn_in()
        self.assertEqual(self.player.db.wallet, 50)
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), 25)
        self.assertIn("healing_potion", self.player.db.inventory)

        # 2. Buy an item at the store while open.
        self.player.location = self.store
        clock = WorldClock(12 * 3600)
        with patch("world.rules.economy.get_world_clock", return_value=clock):
            self.call(CmdBuy(), "meal 1", "你買了 1 個")
        self.assertEqual(self.player.db.wallet, 40)
        self.call(CmdInventory(), "", "錢包")

        # 3. Cross a closed/open/restock boundary via the world clock.
        self.player.location = self.guild_hall
        real_clock = get_world_clock()
        # Move from day 0 00:00 to day 1 08:00 (32h): caravan restock at 06:00
        # then shop open at 08:00. Both sources registered by sync_guild_economy.
        from world.rules.economy import shop_is_open

        with patch("world.rules.clock.get_world_clock", return_value=real_clock):
            events = real_clock.advance(
                32 * 3600,
                AdvanceSource.COMMAND,
                [self.player],
            )
        kinds = [event.kind for event in events]
        self.assertIn("caravan_arrivals", kinds)
        self.assertIn("shop_hours", kinds)
        self.assertTrue(shop_is_open("altoria_general_store"))

        # 4. Repeat the hunt to reach E merit threshold (second completion).
        self.player.location = self.guild_hall
        self._accept_intro()
        self._complete_hunt()
        self._turn_in()
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), 50)

        # 5. Trigger the E examination, defeat the examiner, observe E rank.
        from commands.combat import CmdGuildExam

        self.player.location = self.guild_hall
        # Give the player decisive power so the nonlethal exam resolves.
        for key in ("atk_phys", "agility", "defense", "magic_level"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        self.call(CmdGuildExam(), "E", "你開始了 E 階的考核")
        self.assertIsNotNone(self.player.db.active_combat)
        session = read_session(self.player)
        self.assertEqual(session.mode, "guild_exam")
        from evennia.objects.models import ObjectDB

        opponent = ObjectDB.objects.filter(id=session.enemy_ids[0]).first()
        with patch("world.rules.combat.roll_d100", return_value=100):
            self.call(CmdCast(), f"basic_attack={opponent.key}", None)
        self.assertEqual(self.player.guild_rank, "E")
        self.assertIsNone(self.player.db.active_combat)

        # 6. No active session or orphan opponent remains.
        self.assertIsNone(self.player.db.active_combat)
        from evennia.objects.models import ObjectDB

        self.assertIsNone(
            ObjectDB.objects.filter(id=session.enemy_ids[0]).first()
        )

    def test_true_combat_stats_used_despite_disguise(self):
        self._register()
        self.player.traits.atk_phys.base = 88
        self.player.db.disguised_stats = {"atk_phys": 8}
        self.assertEqual(get_display_value(self.player, "atk_phys"), 8)
        self.assertEqual(self.player.traits.atk_phys.base, 88)
        # Combat reads the true stat: a decisive hit uses atk 88.
        self._accept_intro()
        monster = self._spawn_hunt_monster()
        self.call(CmdEngage(), monster.key, "戰鬥開始")
        with patch("world.rules.combat.roll_d100", return_value=100):
            self.call(CmdCast(), f"basic_attack={monster.key}", None)
        self.assertIsNone(self.player.db.active_combat)

    def test_future_npc_intent_contract(self):
        from world.rules.guild_exams import ExamReason, GuildExamError, start_guild_exam
        from typeclasses.components import GuildExaminer
        from typeclasses.npcs import NPC

        staff = create_object(NPC, key="exam staff", location=self.guild_hall)
        staff.components.add(
            GuildExaminer.create(staff, service_id="exam", branch_key="guild_branch_altoria")
        )
        self._register()
        # Below-threshold request via npc_intent is rejected identically.
        with self.assertRaises(GuildExamError) as ctx:
            start_guild_exam(
                self.player,
                staff,
                "E",
                requested_by="npc_intent",
            )
        self.assertEqual(ctx.exception.args[0], ExamReason.BELOW_THRESHOLD)