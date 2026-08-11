"""Triggerable nonlethal guild examination tests (tasks 8.1-8.8)."""

from tools.spec_traceability import covers_requirement

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.races import STATIC_TIER_REGISTRY
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.combat_session import (
    read_session,
    restore_active_session,
    submit_player_action,
)
from world.rules.guild import register_adventurer
from world.rules.guild_config import load_guild_catalog
from world.rules.guild_exams import (
    ExamReason,
    ExamState,
    GuildExamError,
    _read_exams,
    from_storage,
    settle_exam_outcome,
    start_guild_exam,
    to_storage,
)
from world.rules.guild_offers import register_guild_offer
from world.rules.surfaces import read_counter_trait
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.quests.definitions import QUEST_DEFINITION_REGISTRY


class ExamRegistryIsolation(BattlefieldIsolation, QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        register_catalog()
        self._previous_catalog = __import__(
            "world.rules.guild_config", fromlist=["CATALOG"]
        ).CATALOG
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        import world.rules.guild_config as guild_config
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        guild_config.CATALOG = self._previous_catalog
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()


class ExamRecordTests(unittest.TestCase):
    def test_record_round_trips_through_json(self):
        record = from_storage(
            {
                "exam_id": "1:E:1",
                "character_id": 1,
                "target_rank": "E",
                "requested_by": "command",
                "opponent_id": 2,
                "session_id": "guild_exam:1:1:E:1",
                "state": "active",
                "terminal_reason": None,
            }
        )
        self.assertEqual(record.exam_id, "1:E:1")
        self.assertEqual(to_storage(record)["state"], "active")

    def test_malformed_record_fails_closed(self):
        base = {
            "exam_id": "1:E:1",
            "character_id": 1,
            "target_rank": "E",
            "requested_by": "command",
            "opponent_id": 2,
            "session_id": "guild_exam:1:1:E:1",
            "state": "active",
            "terminal_reason": None,
        }
        for mutation in (
            {"state": "unknown"},
            {"exam_id": ""},
            {"character_id": "x"},
        ):
            with self.subTest(data=mutation):
                with self.assertRaises(GuildExamError):
                    from_storage({**base, **mutation})

    def test_malformed_record_shape_fails_closed(self):
        base = {
            "exam_id": "1:E:1",
            "character_id": 1,
            "target_rank": "E",
            "requested_by": "command",
            "opponent_id": 2,
            "session_id": "guild_exam:1:1:E:1",
            "state": "active",
            "terminal_reason": None,
        }
        for mutation in (
            "not-a-dict",
            {"extra_field": 1},
            {"target_rank": None},
            {"opponent_id": True},
            {"terminal_reason": 5},
        ):
            with self.subTest(data=mutation):
                with self.assertRaises(GuildExamError):
                    from_storage(mutation if isinstance(mutation, str) else {**base, **mutation})

    def test_read_exams_tolerates_missing_and_rejects_duplicate_ids(self):
        empty = SimpleNamespace(db=SimpleNamespace(guild_exams=None))
        self.assertEqual(_read_exams(empty), [])

        base = {
            "exam_id": "1:E:1",
            "character_id": 1,
            "target_rank": "E",
            "requested_by": "command",
            "opponent_id": 2,
            "session_id": "guild_exam:1:1:E:1",
            "state": "active",
            "terminal_reason": None,
        }
        duplicate = SimpleNamespace(db=SimpleNamespace(guild_exams=[base, base]))
        with self.assertRaises(GuildExamError):
            _read_exams(duplicate)

        bad_root = SimpleNamespace(db=SimpleNamespace(guild_exams=5))
        with self.assertRaises(GuildExamError):
            _read_exams(bad_root)


class ExamStartTests(ExamRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="exam hall")
        self.player = create_object(PlayerCharacter, key="exam player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        self.staff = create_object(NPC, key="guild staff", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        self.examiner = create_object(NPC, key="examiner", location=self.hall)
        self.examiner.components.add(
            GuildExaminer.create(
                self.examiner,
                service_id="examiner",
                branch_key="guild_branch_altoria",
            )
        )
        register_adventurer(self.player, self.staff)

    def _give_merit(self, amount):
        from world.rules.surfaces import write_counter_trait

        write_counter_trait(self.player, "guild_merit", amount)

    @covers_requirement("guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself", "guild-rank-exams::examination-start-is-all-or-nothing-across-opponent-record-and-session", "affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths")
    def test_command_trigger_starts_an_eligible_exam(self):
        self._give_merit(50)
        record = start_guild_exam(
            self.player,
            self.examiner,
            "E",
            requested_by="command",
        )
        self.assertEqual(record.target_rank, "E")
        self.assertEqual(record.state, ExamState.ACTIVE)
        session = read_session(self.player)
        self.assertEqual(session.mode, "guild_exam")
        self.assertEqual(session.exam_id, record.exam_id)
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        self.assertIsNotNone(opponent)
        self.assertEqual(opponent.location, self.hall)
        self.assertEqual(self.examiner.relations.affinity_for(self.player), 1)

    @covers_requirement("guild-rank-exams::guild-exam-opponents-carry-adult-identity")
    def test_spawned_exam_opponent_carries_adult_identity(self):
        from world.art.adult import portrait_eligibility

        self._give_merit(50)
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        self.assertIsNotNone(opponent)
        self.assertEqual(int(opponent.attributes.get("age")), 18)
        self.assertEqual(int(opponent.attributes.get("apparent_age")), 18)
        self.assertEqual(portrait_eligibility(opponent), (18, 18))

    def test_npc_intent_has_no_extra_authority(self):
        # No merit -> rejected identically for both requesters.
        for requester in ("command", "npc_intent"):
            with self.subTest(requester=requester):
                with self.assertRaises(GuildExamError) as ctx:
                    start_guild_exam(
                        self.player,
                        self.examiner,
                        "E",
                        requested_by=requester,
                    )
                self.assertEqual(ctx.exception.args[0], ExamReason.BELOW_THRESHOLD)

    def test_below_threshold_request_is_rejected(self):
        with self.assertRaises(GuildExamError) as ctx:
            start_guild_exam(self.player, self.examiner, "E")
        self.assertEqual(ctx.exception.args[0], ExamReason.BELOW_THRESHOLD)

    def test_rank_skipping_is_rejected(self):
        self._give_merit(150)
        with self.assertRaises(GuildExamError) as ctx:
            start_guild_exam(self.player, self.examiner, "D")
        self.assertEqual(ctx.exception.args[0], ExamReason.NOT_NEXT_RANK)

    def test_duplicate_active_exam_is_rejected(self):
        self._give_merit(50)
        start_guild_exam(self.player, self.examiner, "E")
        # The active exam also holds an active combat session, which the sole
        # trigger rejects first; no second opponent/record/session is created.
        with self.assertRaises(GuildExamError) as ctx:
            start_guild_exam(self.player, self.examiner, "E")
        self.assertEqual(ctx.exception.args[0], ExamReason.ACTIVE_COMBAT)
        self.assertEqual(self.examiner.relations.affinity_for(self.player), 1)

    def test_remote_examiner_is_rejected(self):
        other = create_object(Room, key="elsewhere")
        far = create_object(NPC, key="far examiner", location=other)
        far.components.add(
            GuildExaminer.create(far, service_id="far", branch_key="guild_branch_altoria")
        )
        self._give_merit(50)
        with self.assertRaises(GuildExamError) as ctx:
            start_guild_exam(self.player, far, "E")
        self.assertEqual(ctx.exception.args[0], ExamReason.REMOTE_EXAMINER)

    @covers_requirement("guild-rank-exams::rank-promotion-requires-cumulative-merit-and-exactly-the-next-examination")
    def test_threshold_alone_does_not_promote(self):
        self._give_merit(50)
        self.assertEqual(self.player.guild_rank, "F")
        # No exam started => rank stays F.
        self.assertIsNone(read_session(self.player))


class ExamCombatTests(ExamRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="exam hall")
        self.player = create_object(PlayerCharacter, key="exam fighter")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        self.staff = create_object(NPC, key="guild staff", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        self.examiner = create_object(NPC, key="examiner", location=self.hall)
        self.examiner.components.add(
            GuildExaminer.create(
                self.examiner,
                service_id="examiner",
                branch_key="guild_branch_altoria",
            )
        )
        register_adventurer(self.player, self.staff)
        from world.rules.surfaces import write_counter_trait

        write_counter_trait(self.player, "guild_merit", 50)

    def test_nonlethal_opponent_knockout_is_not_a_kill(self):
        from world.rules.action import _ENTRY_TEMPLATES
        from world.rules.event_log import EventEntry

        # Make the candidate overwhelmingly strong for one decisive hit.
        for key in ("atk_phys", "agility", "defense", "magic_level"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(result["outcome"], "exam_passed")
        self.assertEqual(self.player.guild_rank, "E")
        self.assertEqual(opponent.traits.hp.current, 1)
        self.assertTrue(opponent.traits.hp.current > 0)

    def test_promotion_preserves_merit(self):
        for key in ("atk_phys", "agility", "defense", "magic_level"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(result["outcome"], "exam_passed")
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), 50)
        self.assertEqual(self.player.guild_rank, "E")

    def test_failed_attempt_can_be_retried_with_next_number(self):
        # Fail via forfeit.
        record = start_guild_exam(self.player, self.examiner, "E")
        from world.rules.combat_session import forfeit

        result = forfeit(self.player)
        self.assertEqual(result["outcome"], "exam_failed")
        records = _read_exams(self.player)
        self.assertEqual(records[0].state, ExamState.FAILED)
        # Retry gets attempt number 2.
        record2 = start_guild_exam(self.player, self.examiner, "E")
        self.assertEqual(record2.exam_id, f"{self.player.pk}:E:2")

    @covers_requirement("guild-rank-exams::exam-settlement-is-idempotent-and-promotes-only-a-passing-candidate")
    def test_replayed_settlement_cannot_promote_twice(self):
        from world.rules.combat_session import read_session

        record = start_guild_exam(self.player, self.examiner, "E")
        session = read_session(self.player)
        settle_exam_outcome(self.player, session, None, "exam_passed")
        self.assertEqual(self.player.guild_rank, "E")
        # Replay -> idempotent, no double promotion.
        settle_exam_outcome(self.player, session, None, "exam_passed")
        self.assertEqual(self.player.guild_rank, "E")

    def test_flee_records_fail(self):
        record = start_guild_exam(self.player, self.examiner, "E")
        from world.rules.combat_session import read_session, submit_player_action

        session = read_session(self.player)
        settle_exam_outcome(self.player, session, None, "exam_failed")
        self.assertEqual(self.player.guild_rank, "F")
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.FAILED)

    @covers_requirement("guild-rank-exams::examination-combat-is-nonlethal-and-grants-no-ordinary-defeat-rewards")
    def test_candidate_knockout_is_nonfatal_but_fails(self):
        # Make the examiner overwhelmingly strong so its basic_attack floors
        # the candidate's HP at 1 and knocks it out; the exam fails without a
        # kill, and the candidate survives at 1 HP.
        record = start_guild_exam(self.player, self.examiner, "E")
        from evennia.objects.models import ObjectDB
        from world.rules.combat_session import read_session, submit_player_action

        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        for key in ("atk_phys", "agility", "defense", "magic_level"):
            getattr(opponent.traits, key).base = 500
        opponent.traits.hp.base = 2000
        opponent.traits.hp.current = 2000
        session = read_session(self.player)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(result["outcome"], "exam_failed")
        self.assertEqual(self.player.guild_rank, "F")
        self.assertGreaterEqual(self.player.traits.hp.current, 1)


class ExamProfileValidationTests(ExamRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="profile hall")
        self.staff = create_object(NPC, key="profile staff", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        self.examiner = create_object(NPC, key="profile examiner", location=self.hall)
        self.examiner.components.add(
            GuildExaminer.create(
                self.examiner,
                service_id="examiner",
                branch_key="guild_branch_altoria",
            )
        )

    @covers_requirement("guild-rank-exams::exam-opponents-use-validated-true-stat-rank-profiles")
    def test_every_rank_profile_stays_inside_its_lore_band(self):
        from world.rules.guild_config import validate_exam_profiles

        raw = __import__(
            "world.rules.guild_config", fromlist=["load_config"]
        ).load_config()["exam_profiles"]
        profiles = validate_exam_profiles(raw)
        for rank, profile in profiles.items():
            tier = STATIC_TIER_REGISTRY[profile.static_tier_key]
            band = tier.band
            for axis in ("atk_phys", "agility", "defense"):
                self.assertTrue(band[0] <= getattr(profile, axis) <= band[1])

    def test_spawned_opponent_uses_true_profile_stats(self):
        self.player = create_object(PlayerCharacter, key="profile player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)
        from world.rules.surfaces import write_counter_trait

        write_counter_trait(self.player, "guild_merit", 50)
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        profile = __import__(
            "world.rules.guild_config", fromlist=["get_catalog"]
        ).get_catalog().exam_profiles["E"]
        self.assertEqual(opponent.traits.atk_phys.base, profile.atk_phys)
        self.assertEqual(opponent.traits.agility.base, profile.agility)


if __name__ == "__main__":
    import unittest

    unittest.main()
