"""Guild registration and local service-host resolution tests (tasks 4.1-4.6)."""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.maps.bootstrap import GUILD_HALL_TAG
from world.rules.clock import WorldClock
from world.rules.guild import (
    GuildDataError,
    GuildError,
    GuildServiceError,
    RegistrationReason,
    parse_guild_registration,
    register_adventurer,
    resolve_local_service_host,
)
from world.rules.traits import get_display_value


def _attach_staff(npc: NPC, branch_key: str = "guild_branch_altoria") -> NPC:
    npc.components.add(
        GuildStaff.create(npc, service_id="staff", branch_key=branch_key)
    )
    return npc


class GuildRegistrationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="guild lobby")
        self.player = create_object(PlayerCharacter, key="guild player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.staff = _attach_staff(create_object(NPC, key="guild staff", location=self.room))

    def _register(self, **kwargs):
        return register_adventurer(self.player, **kwargs)

    @covers_requirement("guild-registration::registration-grants-f-rank-and-records-one-displayed-stat-snapshot", "affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths")
    def test_undisguised_character_registers_at_f_with_true_snapshot(self):
        record = self._register(staff=self.staff)
        self.assertEqual(self.player.guild_rank, "F")
        self.assertEqual(record["branch_key"], "guild_branch_altoria")
        for key in ("hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_level", "guild_merit"):
            self.assertEqual(
                record["displayed_stats"][key],
                int(getattr(self.player.traits, key).value),
            )
        self.assertEqual(
            record["displayed_stats"]["atk_phys"],
            get_display_value(self.player, "atk_phys"),
        )
        self.assertEqual(self.staff.relations.affinity_for(self.player), 1)

    def test_disguise_affects_only_the_registration_snapshot(self):
        self.player.traits.atk_phys.base = 88
        self.player.db.disguised_stats = {"atk_phys": 8}
        record = self._register(staff=self.staff)
        self.assertEqual(record["displayed_stats"]["atk_phys"], 8)
        self.assertEqual(self.player.guild_rank, "F")
        self.assertEqual(int(self.player.traits.atk_phys.value), 88)

    def test_register_granted_tick_is_current_world_tick(self):
        clock = WorldClock(1234)
        with patch("world.rules.guild.get_world_clock", return_value=clock):
            record = self._register(staff=self.staff)
        self.assertEqual(record["registered_tick"], 1234)

    def test_staff_component_is_sole_branch_authority(self):
        record = self._register(staff=self.staff)
        self.assertEqual(record["branch_key"], self.staff.components.get(GuildStaff.get_component_slot()).branch_key)

    def test_registration_is_atomic_on_rank_write_failure(self):
        original = (
            self.player.db.guild_registration,
            self.player.guild_rank,
            self.staff.db.relations_data,
        )
        # Fault-inject the transaction context: the writer body runs and sets
        # both fields plus the affinity gain, then the fake atomic exits with
        # an error. The handler must restore the database and the in-process
        # attribute caches to their pre-registration values.
        class FakeAtomic:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                raise RuntimeError("db failure")

        with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
            with self.assertRaises(RuntimeError):
                register_adventurer(self.player, staff=self.staff)
        self.assertEqual(
            (
                self.player.db.guild_registration,
                self.player.guild_rank,
                self.staff.db.relations_data,
            ),
            original,
        )

    def test_repeat_registration_preserves_historical_values(self):
        first = self._register(staff=self.staff)
        self.player.db.disguised_stats = {"atk_phys": 88}
        second = self._register(staff=self.staff)
        self.assertEqual(second, first)
        self.assertEqual(
            self.player.db.guild_registration["displayed_stats"]["atk_phys"],
            first["displayed_stats"]["atk_phys"],
        )

    def test_remote_staff_cannot_register(self):
        other_room = create_object(Room, key="other room")
        remote = _attach_staff(create_object(NPC, key="remote staff", location=other_room))
        with self.assertRaises(GuildError) as ctx:
            self._register(staff=remote)
        self.assertEqual(ctx.exception.args[0], RegistrationReason.REMOTE_STAFF)
        self.assertIsNone(self.player.guild_rank)
        self.assertIsNone(self.player.db.guild_registration)

    def test_non_player_rejected(self):
        npc = create_object(NPC, key="npc actor", location=self.room)
        with self.assertRaises(GuildError) as ctx:
            register_adventurer(npc, staff=self.staff)
        self.assertEqual(ctx.exception.args[0], RegistrationReason.NOT_A_PLAYER)

    @covers_requirement("guild-registration::registration-access-is-local-idempotent-and-strict-about-persisted-data")
    def test_partial_membership_fails_closed(self):
        self.player.guild_rank = "F"
        self.player.db.guild_registration = {
            "branch_key": "guild_branch_altoria",
            "registered_tick": 0,
        }
        with self.assertRaises(GuildDataError):
            self._register(staff=self.staff)
        self.assertEqual(self.player.guild_rank, "F")
        self.assertIsNotNone(self.player.db.guild_registration)

    def test_malformed_registration_parsing(self):
        self.player.db.guild_registration = {
            "branch_key": "guild_branch_altoria",
            "registered_tick": 0,
            "displayed_stats": {"atk_phys": 5},
        }
        with self.assertRaises(GuildDataError):
            parse_guild_registration(self.player)
        self.player.db.guild_registration = {"garbage": True}
        with self.assertRaises(GuildDataError):
            parse_guild_registration(self.player)


class ServiceHostResolutionTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="resolution room")
        self.player = create_object(PlayerCharacter, key="resolution player")
        self.player.location = self.room

    def test_zero_hosts_fail_with_named_reason(self):
        with self.assertRaises(GuildServiceError):
            resolve_local_service_host(self.player, GuildStaff)

    def test_one_host_resolves(self):
        npc = _attach_staff(create_object(NPC, key="only staff", location=self.room))
        self.assertEqual(resolve_local_service_host(self.player, GuildStaff), npc)

    def test_ambiguous_hosts_fail(self):
        _attach_staff(create_object(NPC, key="staff a", location=self.room))
        _attach_staff(create_object(NPC, key="staff b", location=self.room))
        with self.assertRaises(GuildServiceError):
            resolve_local_service_host(self.player, GuildStaff)

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_host_in_another_room_is_not_local(self):
        other = create_object(Room, key="other")
        _attach_staff(create_object(NPC, key="far staff", location=other))
        with self.assertRaises(GuildServiceError):
            resolve_local_service_host(self.player, GuildStaff)


class RegistrationBoundaryScanTests(unittest.TestCase):
    @covers_requirement("disguised-stats-boundary::disguised-stats-keys-are-readable-by-exactly-three-consumers-including-implemented-guild-registration")
    def test_get_display_value_docstring_names_exactly_three_consumers(self):
        doc = inspect.getdoc(get_display_value).lower()
        self.assertIn("look", doc)
        self.assertIn("registration", doc)
        self.assertIn("appraisal", doc)
        self.assertIn("combat", doc)
        self.assertIn("must never call this function", doc)

    def test_only_registration_path_reads_disguise_in_guild_modules(self):
        import ast
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        source = (root / "world/rules/guild.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("disguised_stats"), 0)
        tree = ast.parse(source)
        calls = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "get_display_value"
        ]
        self.assertEqual(calls, ["get_display_value"])


class GuildServicePCIntegrationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.quests.tests._fixtures import register_catalog_once
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        register_catalog_once()
        import world.maps.bootstrap as bootstrap

        self.hall = create_object(Room, key="guild lobby")
        self.hall.tags.add(GUILD_HALL_TAG)
        self.player = create_object(PlayerCharacter, key="guild player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        self.staff = _attach_staff(create_object(NPC, key="guild staff", location=self.hall))

    def tearDown(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()

    def test_pipeline_flow_registers_then_returns_record(self):
        record = register_adventurer(self.player)
        self.assertEqual(record["branch_key"], "guild_branch_altoria")
        resolved = resolve_local_service_host(self.player, GuildStaff)
        self.assertIs(resolved, self.staff)


if __name__ == "__main__":
    import unittest

    unittest.main()
