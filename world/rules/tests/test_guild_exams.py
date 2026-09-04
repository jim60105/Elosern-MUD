"""Triggerable nonlethal guild examination tests (tasks 8.1-8.8)."""

from tools.spec_traceability import covers_requirement

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.guild import GUILD_RANK_REGISTRY

# Authored examiner identity for rank E (npc-title-authored-identities D8).
EXAMINER_NAME = GUILD_RANK_REGISTRY["E"].examiner_name
EXAMINER_TITLE = GUILD_RANK_REGISTRY["E"].examiner_title
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

    @covers_requirement("guild-rank-exams::exam-opponents-use-collision-free-unique-display-keys")
    def test_same_named_player_can_take_the_exam(self):
        self.player.key = EXAMINER_NAME
        self.player.save()
        self._give_merit(50)
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        self.assertIsNotNone(opponent)
        # Name occupied by the player -> conditional -{pk} disambiguator.
        self.assertEqual(opponent.key, f"{EXAMINER_NAME}-{opponent.pk}")
        self.assertNotEqual(opponent.key, self.player.key)
        self.assertIsNotNone(read_session(self.player))

    @covers_requirement("guild-rank-exams::exam-opponents-use-collision-free-unique-display-keys")
    def test_concurrent_same_rank_exams_never_share_a_key(self):
        # Two live opponents of one rank: the second spawn sees the first
        # committed same-named entity and takes its own -<pk> component.
        self._give_merit(50)
        first = start_guild_exam(self.player, self.examiner, "E")
        first_opponent = ObjectDB.objects.filter(id=first.opponent_id).first()
        self.assertEqual(first_opponent.key, EXAMINER_NAME)
        rival = create_object(PlayerCharacter, key="rival candidate")
        rival.race = "human"
        rival.apply_race_baseline()
        rival.location = self.hall
        register_adventurer(rival, self.staff)
        from world.rules.surfaces import write_counter_trait

        write_counter_trait(rival, "guild_merit", 50)
        second = start_guild_exam(rival, self.examiner, "E")
        second_opponent = ObjectDB.objects.filter(id=second.opponent_id).first()
        self.assertIsNotNone(second_opponent)
        self.assertEqual(second_opponent.key, f"{EXAMINER_NAME}-{second_opponent.pk}")
        self.assertNotEqual(first_opponent.key, second_opponent.key)

    @covers_requirement("guild-rank-exams::exam-opponents-use-collision-free-unique-display-keys")
    def test_seqentially_released_name_is_reused_verbatim(self):
        # Restated contract: the suffix is conditional. Once the first
        # opponent is deleted at forfeit, the next spawn reuses the free
        # authored name verbatim (no permanent -pk disambiguation).
        self._give_merit(100)
        first = start_guild_exam(self.player, self.examiner, "E")
        first_opponent = ObjectDB.objects.filter(id=first.opponent_id).first()
        from world.rules.combat_session import forfeit

        forfeit(self.player)
        second = start_guild_exam(self.player, self.examiner, "E")
        second_opponent = ObjectDB.objects.filter(id=second.opponent_id).first()
        self.assertIsNotNone(first_opponent)
        self.assertIsNotNone(second_opponent)
        self.assertEqual(first_opponent.key, EXAMINER_NAME)
        self.assertEqual(second_opponent.key, EXAMINER_NAME)
        self.assertNotEqual(first_opponent.pk, second_opponent.pk)

    @covers_requirement("guild-rank-exams::examination-start-is-all-or-nothing-across-opponent-record-and-session")
    def test_affinity_failure_leaves_no_orphan_session_or_registration(self):
        from world.rules.skip_safety import _BATTLEFIELDS

        self._give_merit(50)
        with patch(
            "world.rules.affinity.apply_affinity_change",
            side_effect=RuntimeError("affinity boom"),
        ):
            with self.assertRaises(RuntimeError):
                start_guild_exam(self.player, self.examiner, "E")
        self.assertIsNone(self.player.db.active_combat)
        self.assertIsNone(read_session(self.player))
        self.assertEqual(_BATTLEFIELDS, {})
        orphans = ObjectDB.objects.filter(
            db_key__startswith=EXAMINER_NAME,
            db_location=self.hall,
        )
        self.assertEqual(orphans.count(), 0)

    @covers_requirement("guild-rank-exams::examination-start-is-all-or-nothing-across-opponent-record-and-session")
    def test_reconstruction_failure_leaves_no_orphan_session_or_registration(self):
        from world.rules.combat_session import CombatSessionError, SessionReason
        from world.rules.skip_safety import _BATTLEFIELDS

        self._give_merit(50)
        with patch(
            "world.rules.combat_session.reconstruct_battlefield",
            side_effect=CombatSessionError(SessionReason.MISSING_PARTICIPANT),
        ):
            with self.assertRaises(CombatSessionError):
                start_guild_exam(self.player, self.examiner, "E")
        self.assertIsNone(self.player.db.active_combat)
        self.assertIsNone(read_session(self.player))
        self.assertEqual(_BATTLEFIELDS, {})
        orphans = ObjectDB.objects.filter(
            db_key__startswith=EXAMINER_NAME,
            db_location=self.hall,
        )
        self.assertEqual(orphans.count(), 0)


    @covers_requirement("npc-identity-titles::exam-examiners-carry-their-authored-identity")
    def test_spawn_uses_the_authored_name_and_persists_the_title(self):
        self._give_merit(50)
        with patch("world.rules.guild_exams.log_info") as logged:
            record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        self.assertIsNotNone(opponent)
        # Free name -> no disambiguator: the authored name IS the key.
        self.assertEqual(opponent.key, EXAMINER_NAME)
        self.assertEqual(opponent.npc_title, EXAMINER_TITLE)
        self.assertTrue(opponent.key.startswith(EXAMINER_NAME))
        events = [
            call for call in logged.call_args_list
            if call.args and call.args[0] == "guild_exam_opponent_created"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kwargs["context"]["char"], EXAMINER_NAME)
        self.assertEqual(events[0].kwargs["context"]["rank"], "E")

    @covers_requirement("npc-identity-titles::exam-examiners-carry-their-authored-identity")
    def test_persistently_occupied_name_forces_the_suffixed_form(self):
        # A same-named entity that survives (a second candidate mid-exam whose
        # opponent holds the authored key) forces the new spawn into the
        # suffixed form so battlefield rosters keyed by str(key) stay distinct.
        holder = create_object(NPC, key=EXAMINER_NAME, location=self.hall)
        self._give_merit(50)
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        self.assertEqual(opponent.key, f"{EXAMINER_NAME}-{opponent.pk}")
        self.assertNotEqual(opponent.key, holder.key)
        self.assertEqual(opponent.npc_title, EXAMINER_TITLE)


class ExamCombatTests(ExamRegistryIsolation, EvenniaTestCase):
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

    def test_lethal_examiner_defeat_passes_and_restores_both_sides(self):
        # Make the candidate overwhelmingly strong for one decisive hit.
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(result["outcome"], "exam_passed")
        self.assertEqual(self.player.guild_rank, "E")
        # Ordinary lethal semantics: the examiner's HP really crossed zero.
        kinds = [entry.kind for log in result["logs"] for entry in log.entries]
        self.assertIn("target_defeated", kinds)
        self.assertNotIn("target_knocked_out", kinds)
        # Simulated battle: both sides are restored to full HP/MP/SP after
        # the outcome, then the temporary opponent is deleted.
        for entity in (self.player, opponent):
            for key in ("hp", "mp", "sp"):
                self.assertEqual(
                    getattr(entity.traits, key).current,
                    getattr(entity.traits, key).max,
                    key,
                )
        self.assertIsNone(ObjectDB.objects.filter(id=record.opponent_id).first())

    def test_promotion_preserves_merit(self):
        for key in ("atk_phys", "agility", "defense", "magic_power"):
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

    @covers_requirement("guild-rank-exams::exam-opponents-use-collision-free-unique-display-keys")
    def test_same_named_player_can_complete_the_exam(self):
        self.player.key = EXAMINER_NAME
        self.player.save()
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(result["outcome"], "exam_passed")
        self.assertEqual(self.player.guild_rank, "E")
        self.assertIsNone(read_session(self.player))

    @covers_requirement("guild-rank-exams::examination-combat-is-a-simulated-lethal-battle-with-full-restoration-around-it")
    def test_candidate_lethal_defeat_fails_but_restores(self):
        # Make the examiner overwhelmingly strong so its basic_attack drives
        # the candidate's HP to 0; the exam fails without a rank change, and
        # the simulated battle restores the candidate to full HP/MP/SP.
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(opponent.traits, key).base = 500
        opponent.traits.hp.base = 2000
        opponent.traits.hp.current = 2000
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(result["outcome"], "exam_failed")
        self.assertEqual(self.player.guild_rank, "F")
        # The lethal crossing really reached zero (simulated, not floored).
        kinds = [entry.kind for log in result["logs"] for entry in log.entries]
        self.assertIn("target_defeated", kinds)
        for key in ("hp", "mp", "sp"):
            self.assertEqual(
                getattr(self.player.traits, key).current,
                getattr(self.player.traits, key).max,
                key,
            )

    def test_wounded_candidate_and_examiner_start_at_full(self):
        # A wounded or spent participant enters the simulated battle at full
        # HP/MP/SP: the start restores both sides after the spawn.
        for key in ("hp", "mp", "sp"):
            getattr(self.player.traits, key).current = 1
        original_spawn = __import__(
            "world.rules.guild_exams", fromlist=["_spawn_opponent"]
        )._spawn_opponent

        def wounded_spawn(actor, target_rank):
            opponent = original_spawn(actor, target_rank)
            for key in ("hp", "mp", "sp"):
                getattr(opponent.traits, key).current = 1
            return opponent

        with patch(
            "world.rules.guild_exams._spawn_opponent",
            side_effect=wounded_spawn,
        ):
            record = start_guild_exam(self.player, self.examiner, "E")
        for key in ("hp", "mp", "sp"):
            self.assertEqual(
                getattr(self.player.traits, key).current,
                getattr(self.player.traits, key).max,
                key,
            )
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        self.assertIsNotNone(opponent)
        for key in ("hp", "mp", "sp"):
            self.assertEqual(
                getattr(opponent.traits, key).current,
                getattr(opponent.traits, key).max,
                key,
            )

    def test_lethal_exam_defeat_grants_no_kill_rewards(self):
        # A lethal simulated defeat is tagged on the event entry, so
        # kill-credit consumers (DEFEAT progress and protected-entity
        # failure come from the quest planner) never observe an ordinary
        # kill from the examination.
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        self.assertEqual(self.player.db.quest_log, [])
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(result["outcome"], "exam_passed")
        defeated = [
            entry
            for log in result["logs"]
            for entry in log.entries
            if entry.kind == "target_defeated"
        ]
        self.assertTrue(defeated)
        self.assertTrue(all(entry.data.get("simulated") is True for entry in defeated))
        # No kill credit (kills carry no progression award) and no quest
        # mutations were planned from the simulated defeat.
        self.assertIsNone(self.player.db.magic_xp)
        self.assertEqual(self.player.db.quest_log, [])

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_exam_tick_kill_of_examiner_settles_simulated(self):
        # The candidate's damaging rate tick kills the examiner during
        # upkeep: the round settles the exam normally, tags the upkeep defeat
        # entry simulated, and grants no kill XP or quest credit.
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        from world.rules.buffs import _add_buff

        _add_buff(opponent, "fire_scorch", source_pk=int(self.player.pk))
        opponent.traits.hp.base = 3
        opponent.traits.hp.current = 3
        opponent.buffs.all["fire_scorch"].tick_elapsed_seconds = 10
        self.assertEqual(self.player.db.quest_log, [])
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(result["outcome"], "exam_passed")
        upkeep_logs = [log for log in result["logs"] if log.skill_key == "combat_upkeep"]
        defeated = [
            entry
            for log in upkeep_logs
            for entry in log.entries
            if entry.kind == "target_defeated"
        ]
        self.assertEqual(len(defeated), 1)
        self.assertTrue(defeated[0].data["simulated"])
        self.assertIsNone(self.player.db.magic_xp)
        self.assertEqual(self.player.db.quest_log, [])

    def test_failed_exam_start_restores_nothing(self):
        # A rejected start rolls the pre-restore back: the candidate keeps the
        # wounded/spent state it brought in, and no opponent survives.
        for key in ("hp", "mp", "sp"):
            getattr(self.player.traits, key).current = 1
        with patch(
            "world.rules.affinity.apply_affinity_change",
            side_effect=RuntimeError("affinity boom"),
        ):
            with self.assertRaises(RuntimeError):
                start_guild_exam(self.player, self.examiner, "E")
        for key in ("hp", "mp", "sp"):
            self.assertEqual(getattr(self.player.traits, key).current, 1, key)
        self.assertIsNone(self.player.db.active_combat)
        self.assertEqual(
            ObjectDB.objects.filter(
                db_key__startswith=EXAMINER_NAME,
                db_location=self.hall,
            ).count(),
            0,
        )


class ExamSettlementRecoveryTests(ExamRegistryIsolation, EvenniaTestCase):
    """fix-combat-settlement-recovery: exam time settles exactly once.

    The old ordering (exam write and clear before the clock advance) lost the
    exam's time when the process died between the two commits; the new
    settlement is one durable transaction with a settled marker, so a restart
    never re-settles and never loses the time.
    """

    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="exam hall")
        self.player = create_object(PlayerCharacter, key="exam recovery")
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

    def test_restored_exam_session_settles_time_exactly_once(self):
        # Simulate a restart from the durable state BEFORE the settlement
        # committed: the exam is still ACTIVE, its terminal session still
        # present with two rounds elapsed, the clock unadvanced (a crash
        # mid-transaction). Restoration must settle the exam's rounds exactly
        # once -- the time is never lost and never doubled.
        from world.rules.clock import WorldClock
        from world.rules.combat_session import (
            _persist,
            from_storage as session_from_storage,
            to_storage as session_to_storage,
        )

        record = start_guild_exam(self.player, self.examiner, "E")
        session = read_session(self.player)
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        _persist(
            self.player,
            session_from_storage(
                {
                    **session_to_storage(session),
                    "rounds_elapsed": 2,
                    "knocked_out_ids": [int(opponent.pk)],
                }
            ),
        )
        opponent.traits.hp.current = 1
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            restore_active_session(self.player)
        self.assertEqual(clock.tick, 12)
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.PASSED)
        self.assertEqual(self.player.guild_rank, "E")
        self.assertIsNone(read_session(self.player))

    def test_restored_marked_exam_session_is_not_resettled(self):
        # Simulate the clock-commit-before-clear window for an exam: the exam
        # outcome and the marker committed, the clear never ran. Restoration
        # skips settlement (no second clock advance) and clears the leftover
        # session state.
        from dataclasses import replace

        from world.rules.clock import WorldClock
        from world.rules.combat_session import (
            _persist,
            from_storage as session_from_storage,
            to_storage as session_to_storage,
        )
        from world.rules.guild_exams import _write_exams

        record = start_guild_exam(self.player, self.examiner, "E")
        session = read_session(self.player)
        _write_exams(
            self.player,
            [
                replace(
                    exam,
                    state=ExamState.FAILED,
                    terminal_reason="exam_failed",
                )
                for exam in _read_exams(self.player)
            ],
        )
        _persist(
            self.player,
            session_from_storage(
                {**session_to_storage(session), "settled_tick": 6}
            ),
        )
        clock = WorldClock(6)
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            restore_active_session(self.player)
        self.assertEqual(clock.tick, 6)
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.FAILED)
        self.assertIsNone(read_session(self.player))

    def test_failed_exam_settlement_keeps_opponent_alive_for_retry(self):
        # The opponent is deleted only after the settlement commits: a failed
        # settlement (clock write error) rolls the exam outcome back and the
        # temporary opponent survives for exactly one retry, which then
        # settles, deletes it, and advances the clock exactly once.
        from world.rules.clock import WorldClock

        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        opponent.traits.hp.base = 1
        opponent.traits.hp.current = 1
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch(
                "world.rules.combat_session.settle_combat_result",
                side_effect=RuntimeError("clock write failed"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(clock.tick, 0)
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.ACTIVE)
        self.assertIsNotNone(ObjectDB.objects.filter(id=record.opponent_id).first())
        self.assertIsNotNone(read_session(self.player))
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(result["outcome"], "exam_passed")
        # The overwhelming candidate defeats the examiner in one lethal
        # round (exam defeats are not battlefield-tracked), settling 6 s once.
        self.assertEqual(clock.tick, 6)
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.PASSED)
        self.assertEqual(self.player.guild_rank, "E")
        self.assertIsNone(ObjectDB.objects.filter(id=record.opponent_id).first())
        self.assertIsNone(read_session(self.player))

    def test_forfeit_restore_failure_rolls_back_settlement_and_gauges(self):
        # The full restoration is part of the settlement transaction: a
        # restore failure rolls the exam outcome, session clear, and gauge
        # writes back, and the degraded forfeit path restores the in-process
        # trait surfaces (the idmapper cache is not transaction-aware). A
        # retry then settles and restores normally.
        from world.rules.combat_session import forfeit

        record = start_guild_exam(self.player, self.examiner, "E")
        self.player.traits.hp.current = 1
        with patch(
            "world.rules.traits.restore_gauges_to_full",
            side_effect=RuntimeError("restore failed"),
        ):
            with self.assertRaises(RuntimeError):
                forfeit(self.player)
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.ACTIVE)
        self.assertIsNotNone(read_session(self.player))
        self.assertIsNotNone(ObjectDB.objects.filter(id=record.opponent_id).first())
        self.assertEqual(self.player.traits.hp.current, 1)
        result = forfeit(self.player)
        self.assertEqual(result["outcome"], "exam_failed")
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.FAILED)
        self.assertEqual(self.player.traits.hp.current, self.player.traits.hp.max)
        self.assertIsNone(ObjectDB.objects.filter(id=record.opponent_id).first())
        self.assertIsNone(read_session(self.player))

    def test_submit_path_restore_failure_rolls_back_the_round(self):
        # In the submit path the restore runs inside the shared outer
        # round-and-settlement transaction: a restore failure rolls the round
        # effects and the settlement back, leaving the exam ACTIVE and both
        # sides' in-process gauges at their pre-round values.
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        record = start_guild_exam(self.player, self.examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        with patch(
            "world.rules.traits.restore_gauges_to_full",
            side_effect=RuntimeError("restore failed"),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "basic_attack", [opponent])
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.ACTIVE)
        self.assertIsNotNone(read_session(self.player))
        self.assertEqual(self.player.guild_rank, "F")
        self.assertEqual(opponent.traits.hp.current, opponent.traits.hp.max)
        self.assertEqual(self.player.traits.hp.current, self.player.traits.hp.max)


class ExamProfileValidationTests(ExamRegistryIsolation, EvenniaTestCase):
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
