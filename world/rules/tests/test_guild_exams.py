"""Persistent-host simulated guild examination tests (persistent-guild-exam-lifecycle).

Every examination fights the branch-qualified persistent adventurer: the
fixtures build one synthetic host, its normal outfit, a synthetic exam kit and
guild limit accessory, synthetic restriction profiles and a qualification
binding, so start/terminal/recovery mechanics are asserted against resolver-
backed state rather than shipped people or rows.
"""

from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.clock import get_world_clock
from world.rules.combat_session import (
    forfeit,
    read_session,
    restore_active_session,
    submit_player_action,
)
from world.rules.exam_schedule_holds import HOLD_ATTRIBUTE, read_exam_schedule_hold
from world.rules.guild import register_adventurer
from world.rules.guild_exams import (
    NORMAL_STATE_ATTRIBUTE,
    ExamReason,
    ExamState,
    GuildExamError,
    _read_exams,
    from_storage,
    settle_exam_outcome,
    start_guild_exam,
    to_storage,
)
from world.rules.npc_persona import (
    current_persona_version,
    provenance_profile_key,
    read_npc_persona,
    update_npc_persona,
)
from world.rules.surfaces import read_counter_trait, write_counter_trait
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests._guild_exam_hosts import (
    EXAM_PROFILES,
    HOST_NAME,
    KIT_ARMOR,
    KIT_BLADE,
    LIMIT_RING,
    exam_scope_extra,
    install_exam_host_policies,
    make_exam_host,
)
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    live_guild_rank_registry,
    synth_catalog,
    synthetic_branch_key,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.skills.restrictions import exam_restriction

EXAM_BRANCH = synthetic_branch_key()
_SCOPE_LOGICALS = ("guild_branches", "skills", "elements", "static_tiers", "items")
_DICE = (
    "world.rules.combat.battlefield.roll_d100",
    "world.rules.combat.damage.roll_d100",
    "world.rules.combat.rounds.roll_d100",
)


def _attack_key() -> str:
    """The innate attack key the patched resolver forces (runtime probe)."""
    import importlib

    return getattr(
        importlib.import_module("world.rules.combat_session"), "BASIC_ATTACK_KEY"
    )


def _scope_extra() -> dict[str, dict[str, object]]:
    extra = {key: dict(rows) for key, rows in synth_innate_overlay().items()}
    for key, rows in exam_scope_extra().items():
        extra.setdefault(key, {}).update(rows)
    return extra


class _Dice:
    """Pin every d100 roll for one deterministic round."""

    def __init__(self, value):
        self._patches = [patch(target, return_value=value) for target in _DICE]

    def __enter__(self):
        for item in self._patches:
            item.start()

    def __exit__(self, *exc):
        for item in self._patches:
            item.stop()


class ExamRegistryIsolation(BattlefieldIsolation, QuestRegistryIsolation):
    def setUp(self):
        # Scope before construction: hosts resolve their skills/items inside
        # the synthetic registries.
        open_synthetic_scope(self, *_SCOPE_LOGICALS, extra=_scope_extra())
        super().setUp()
        register_catalog()
        install_synthetic_catalog(self, synth_catalog())
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


class ExamHostFixture(ExamRegistryIsolation):
    """One guild counter, one registered candidate and one qualified host."""

    def setUp(self):
        super().setUp()
        install_exam_host_policies(self, EXAM_BRANCH)
        self.clock = get_world_clock()
        self.hall = create_object(Room, key="exam hall")
        self.player = self._candidate("exam player")
        self.counter = create_object(NPC, key="guild counter", location=self.hall)
        self.counter.components.add(
            GuildStaff.create(self.counter, service_id="staff", branch_key=EXAM_BRANCH)
        )
        self.counter.components.add(
            GuildExaminer.create(self.counter, service_id="counter", branch_key=EXAM_BRANCH)
        )
        register_adventurer(self.player, self.counter)
        self.host = make_exam_host(self.hall)

    def _candidate(self, key):
        player = create_object(PlayerCharacter, key=key)
        player.race = "human"
        player.apply_race_baseline()
        player.location = self.hall
        return player

    def _give_merit(self, amount, player=None):
        write_counter_trait(player or self.player, "guild_merit", amount)

    def _make_overwhelming(self):
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000

    def _host_normal(self):
        """The host's normal identity/capability/outfit surfaces, deep-copied."""
        host = self.host
        persona = read_npc_persona(host)
        return deepcopy({
            "pk": host.pk,
            "key": host.key,
            "bases": {key: row["base"] for key, row in host.traits.trait_data.items()},
            "skills": dict(host.db.skills),
            "proficiency": dict(host.db.skill_proficiency),
            "persona": (persona.card.to_record(), persona.version),
            "provenance": provenance_profile_key(host),
            "age": (host.attributes.get("age"), host.attributes.get("apparent_age")),
            "equipment": dict(host.db.equipment),
            "inventory": list(host.db.inventory),
            "buffs": host.db.buffs,
            "restriction": host.db.guild_exam_restriction,
            "normal_state": host.attributes.get(NORMAL_STATE_ATTRIBUTE),
            "location": host.location.pk,
        })

    def _host_state(self):
        """Everything a rejected or rolled-back start must leave untouched."""
        return deepcopy({
            "normal": self._host_normal(),
            "traits": dict(self.host.traits.trait_data),
            "hold": self.host.attributes.get(HOLD_ATTRIBUTE),
            "relations": self.host.db.relations_data,
        })

    def _actor_state(self, player=None):
        player = player or self.player
        return deepcopy({
            "exams": player.db.guild_exams,
            "session": player.db.active_combat,
            "rank": player.guild_rank,
            "merit": read_counter_trait(player, "guild_merit"),
            "traits": dict(player.traits.trait_data),
        })

    def _assert_full_normal_pools(self, entity):
        for key in ("hp", "mp", "sp"):
            gauge = getattr(entity.traits, key)
            self.assertEqual(gauge.current, gauge.max, key)

    def _assert_host_restored(self, baseline):
        self.host.refresh_from_db()
        host = ObjectDB.objects.filter(id=baseline["pk"]).first()
        self.assertIsNotNone(host)
        normal = self._host_normal()
        for field in ("pk", "key", "bases", "skills", "proficiency", "persona",
                      "provenance", "age", "equipment", "inventory", "buffs"):
            self.assertEqual(normal[field], baseline[field], field)
        self.assertIsNone(normal["restriction"])
        self.assertIsNone(normal["normal_state"])
        self.assertEqual(self.host.traits.hp.max, 200)
        self._assert_full_normal_pools(self.host)
        hold = read_exam_schedule_hold(self.host)
        self.assertTrue(hold.known)
        self.assertTrue(hold.hold is None or hold.hold.released)


class ExamRecordTests(unittest.TestCase):
    _BASE = {
        "exam_id": "1:E:1",
        "character_id": 1,
        "target_rank": "E",
        "requested_by": "command",
        "opponent_id": 2,
        "session_id": "guild_exam:1:1:E:1",
        "state": "active",
        "terminal_reason": None,
    }

    def test_record_round_trips_through_json(self):
        record = from_storage(dict(self._BASE))
        self.assertEqual(record.exam_id, "1:E:1")
        self.assertEqual(to_storage(record), self._BASE)

    def test_malformed_record_shape_fails_closed(self):
        for mutation in (
            "not-a-dict",
            {"extra_field": 1},
            {"state": "unknown"},
            {"exam_id": ""},
            {"character_id": "x"},
            {"target_rank": None},
            {"opponent_id": True},
            {"terminal_reason": 5},
        ):
            with self.subTest(data=mutation):
                with self.assertRaises(GuildExamError):
                    from_storage(mutation if isinstance(mutation, str) else {**self._BASE, **mutation})

    def test_read_exams_tolerates_missing_and_rejects_duplicate_ids(self):
        self.assertEqual(_read_exams(SimpleNamespace(db=SimpleNamespace(guild_exams=None))), [])
        for raw in ([self._BASE, self._BASE], 5):
            with self.subTest(raw=raw), self.assertRaises(GuildExamError):
                _read_exams(SimpleNamespace(db=SimpleNamespace(guild_exams=raw)))


class ExamStartTests(ExamHostFixture, EvenniaTestCase):
    def _assert_rejected_without_writes(self, reason, examiner=None, player=None):
        player = player or self.player
        host_before = self._host_state()
        actor_before = self._actor_state(player)
        with self.assertRaises(GuildExamError) as ctx:
            start_guild_exam(player, examiner or self.host, "E")
        self.assertEqual(ctx.exception.args[0], reason)
        self.assertEqual(self._host_state(), host_before)
        self.assertEqual(self._actor_state(player), actor_before)
        self.assertFalse(self.host.relations.has_record(player))

    @covers_requirement(
        "guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself",
        "guild-rank-exams::examination-start-is-all-or-nothing-across-opponent-record-and-session",
        "affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths",
    )
    def test_command_trigger_starts_an_eligible_exam_with_the_persistent_host(self):
        self._give_merit(50)
        hosts_before = NPC.objects.count()
        record = start_guild_exam(self.player, self.host, "E", requested_by="command")
        self.assertEqual(record.state, ExamState.ACTIVE)
        self.assertEqual(record.opponent_id, self.host.pk)
        self.assertEqual(NPC.objects.count(), hosts_before)
        session = read_session(self.player)
        self.assertEqual((session.mode, session.exam_id, session.enemy_ids),
                         ("guild_exam", record.exam_id, (self.host.pk,)))
        self.assertEqual(self.host.relations.affinity_for(self.player), 1)
        # Real kit, real accessory, persisted restriction and hold.
        self.assertEqual(self.host.db.equipment["weapon_main"], KIT_BLADE.key)
        self.assertEqual(self.host.db.equipment["armor"], KIT_ARMOR.key)
        self.assertEqual(self.host.db.equipment["accessories"], [LIMIT_RING.key])
        self.assertEqual(exam_restriction(self.host)["exam_id"], record.exam_id)
        self.assertEqual(self.host.attributes.get(NORMAL_STATE_ATTRIBUTE)["exam_id"], record.exam_id)
        hold = read_exam_schedule_hold(self.host)
        self.assertEqual((hold.hold.exam_id, hold.hold.released), (record.exam_id, False))
        # The stronger host is lowered, never raised: ceilings bind the gauges.
        self.assertEqual(self.host.traits.hp.max, EXAM_PROFILES["E"].ceilings["hp"])

    @covers_requirement("guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself")
    def test_busy_present_host_rejects_before_resources_or_affinity(self):
        self._give_merit(50)
        self.host.db.schedule_state = "busy"
        self._assert_rejected_without_writes(ExamReason.SERVICE_UNAVAILABLE)

    @covers_requirement("guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself")
    def test_requested_by_metadata_grants_no_extra_authority(self):
        for requester in ("command", "npc_intent"):
            with self.subTest(requester=requester):
                with self.assertRaises(GuildExamError) as ctx:
                    start_guild_exam(self.player, self.host, "E", requested_by=requester)
                self.assertEqual(ctx.exception.args[0], ExamReason.BELOW_THRESHOLD)
        self.assertFalse(self.host.relations.has_record(self.player))

    @covers_requirement("guild-rank-exams::rank-promotion-requires-cumulative-merit-and-exactly-the-next-examination")
    def test_below_threshold_and_rank_skipping_are_rejected(self):
        self._assert_rejected_without_writes(ExamReason.BELOW_THRESHOLD)
        self._give_merit(150)
        with self.assertRaises(GuildExamError) as ctx:
            start_guild_exam(self.player, self.host, "D")
        self.assertEqual(ctx.exception.args[0], ExamReason.NOT_NEXT_RANK)

    @covers_requirement("guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself")
    def test_duplicate_active_exam_is_rejected(self):
        self._give_merit(50)
        start_guild_exam(self.player, self.host, "E")
        with self.assertRaises(GuildExamError) as ctx:
            start_guild_exam(self.player, self.host, "E")
        self.assertEqual(ctx.exception.args[0], ExamReason.ACTIVE_COMBAT)
        self.assertEqual(len(_read_exams(self.player)), 1)
        self.assertEqual(self.host.relations.affinity_for(self.player), 1)

    @covers_requirement(
        "guild-rank-exams::exam-opponents-use-collision-free-unique-display-keys",
        "guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself",
    )
    def test_busy_host_contention_never_opens_a_second_session(self):
        self._give_merit(50)
        start_guild_exam(self.player, self.host, "E")
        rival = self._candidate("rival candidate")
        register_adventurer(rival, self.counter)
        self._give_merit(50, rival)
        with self.assertRaises(GuildExamError) as ctx:
            start_guild_exam(rival, self.host, "E")
        self.assertEqual(ctx.exception.args[0], ExamReason.EXAMINER_ENGAGED)
        self.assertIsNone(read_session(rival))
        self.assertIsNone(rival.db.guild_exams)

    @covers_requirement("guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself")
    def test_remote_host_is_rejected_before_eligibility(self):
        self.host.location = create_object(Room, key="host home")
        self._give_merit(50)
        self._assert_rejected_without_writes(ExamReason.REMOTE_EXAMINER)

    @covers_requirement("guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself")
    def test_off_anchor_counter_is_refused_before_any_eligibility_write(self):
        component = self.counter.components.get(GuildExaminer.get_component_slot())
        component.service_binding = "place"
        component.anchor_room_id = self.hall.pk
        square = create_object(Room, key="exam square")
        for entity in (self.counter, self.host, self.player):
            entity.location = square
        self._give_merit(50)
        self._assert_rejected_without_writes(ExamReason.SERVICE_UNAVAILABLE)
        # A malformed stored binding fails closed the same way.
        component.service_binding = "portable"
        self._assert_rejected_without_writes(ExamReason.SERVICE_UNAVAILABLE)

    @covers_requirement("guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself")
    def test_unqualified_or_unbound_person_cannot_host(self):
        self._give_merit(50)
        stranger = make_exam_host(self.hall, key="不相干的冒險者")
        stranger.attributes.remove("guild_adventurer_person_key")
        self._assert_rejected_without_writes(ExamReason.UNQUALIFIED_EXAMINER, examiner=stranger)
        with patch("world.rules.human_guild_hosts.EXAM_QUALIFICATIONS", ()):
            self._assert_rejected_without_writes(ExamReason.UNQUALIFIED_EXAMINER)

    @covers_requirement("guild-rank-exams::exam-opponents-use-collision-free-unique-display-keys")
    def test_player_name_collision_rejects_without_renaming_the_host(self):
        self._give_merit(50)
        self.player.key = self.host.key
        self.player.save()
        self._assert_rejected_without_writes(ExamReason.PARTICIPANT_NAME_COLLISION)
        self.assertEqual(self.host.key, HOST_NAME)

    @covers_requirement("guild-rank-exams::guild-exam-opponents-carry-canonical-age")
    def test_invalid_host_age_leaves_no_partial_examination(self):
        self._give_merit(50)
        self.host.attributes.add("age", 10001)
        self._assert_rejected_without_writes(ExamReason.UNQUALIFIED_EXAMINER)

    @covers_requirement("guild-rank-exams::examination-start-is-all-or-nothing-across-opponent-record-and-session")
    def test_unusable_kit_or_lineage_rejects_before_any_mutation(self):
        self._give_merit(50)
        self.host.db.skills = {"active": [], "passive": []}
        self._assert_rejected_without_writes(ExamReason.UNQUALIFIED_EXAMINER)

    @covers_requirement("guild-rank-exams::examination-start-is-all-or-nothing-across-opponent-record-and-session")
    def test_start_fault_at_every_checkpoint_restores_storage_and_caches(self):
        from world.rules.skip_safety import _BATTLEFIELDS
        from world.rules import skip_safety, traits

        self._give_merit(50)
        for entity in (self.player, self.host):
            for key in ("hp", "mp", "sp"):
                getattr(entity.traits, key).current = 1
        real_register = skip_safety.register_active_battlefield
        real_restore = traits.restore_gauges_to_full

        def published_then_fail(battlefield):
            real_register(battlefield)
            raise RuntimeError("after skip-safety publication")

        def restore_then_fail(entity):
            real_restore(entity)
            if entity.pk == self.host.pk:
                raise RuntimeError("after pool restoration")

        checkpoints = {
            "kit": ("world.rules.guild_exams.activate_exam_restriction", RuntimeError("after kit")),
            "restriction": ("world.rules.guild_exams.begin_exam_schedule_hold", RuntimeError("after restriction")),
            "pools": ("world.rules.traits.restore_gauges_to_full", restore_then_fail),
            "record": ("world.rules.combat_session.reconstruct_battlefield", RuntimeError("after record")),
            "session": ("world.rules.skip_safety.register_active_battlefield", published_then_fail),
            "affinity": ("world.rules.affinity.apply_affinity_change", RuntimeError("after affinity")),
        }
        host_before = self._host_state()
        actor_before = self._actor_state()
        for name, (target, effect) in checkpoints.items():
            with self.subTest(checkpoint=name):
                with patch(target, side_effect=effect), self.assertRaises(RuntimeError):
                    start_guild_exam(self.player, self.host, "E")
                self.assertEqual(self._host_state(), host_before)
                self.assertEqual(self._actor_state(), actor_before)
                self.assertEqual(_BATTLEFIELDS, {})
                self.assertFalse(self.host.relations.has_record(self.player))
        # The retry starts exactly once, as attempt number one.
        record = start_guild_exam(self.player, self.host, "E")
        self.assertEqual(record.exam_id, f"{self.player.pk}:E:1")
        self.assertEqual(len(_read_exams(self.player)), 1)

    @covers_requirement(
        "guild-rank-exams::exam-opponents-receive-their-rank-examiner-s-card-at-spawn",
        "npc-identity-titles::exam-examiners-carry-their-authored-identity",
        "npc-identity-titles::host-and-examiner-creation-emit-boundary-info-events",
    )
    def test_start_reuses_the_edited_persona_and_identity_without_spawning(self):
        card = read_npc_persona(self.host).card.to_record()
        card["appearance"] = "換上了另一套斗篷。"
        self.assertEqual(update_npc_persona(self.host, card, expected_version=1).status, "updated")
        before = self._host_normal()
        self._give_merit(50)
        with patch("world.rules.guild_exams.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
                start_guild_exam(self.player, self.host, "E")
        events = [call.args[0] for call in logged.call_args_list]
        self.assertEqual(events, ["guild_exam_started"])
        self.assertEqual(logged.call_args.kwargs["context"]["host"], self.host.pk)
        during = self._host_normal()
        for field in ("pk", "key", "persona", "provenance", "age", "bases", "skills", "proficiency"):
            self.assertEqual(during[field], before[field], field)
        self.assertEqual(current_persona_version(self.host), 2)

    @covers_requirement("guild-rank-exams::exam-opponents-use-validated-true-stat-rank-profiles")
    def test_disguised_candidate_receives_the_same_host_and_profile(self):
        self._give_merit(50)
        self.player.db.disguised_stats = {"atk_phys": 999, "hp": 999}
        record = start_guild_exam(self.player, self.host, "E")
        self.assertEqual(record.opponent_id, self.host.pk)
        self.assertEqual(
            exam_restriction(self.host)["ceilings"], dict(EXAM_PROFILES["E"].ceilings)
        )


class ExamCombatTests(ExamHostFixture, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self._give_merit(50)

    @covers_requirement(
        "guild-rank-exams::examination-combat-is-a-simulated-lethal-battle-with-full-restoration-around-it",
        "guild-rank-exams::exam-settlement-is-idempotent-and-promotes-only-a-passing-candidate",
    )
    def test_host_defeat_passes_and_restores_the_persistent_host(self):
        baseline = self._host_normal()
        self._make_overwhelming()
        start_guild_exam(self.player, self.host, "E")
        with _Dice(100):
            result = submit_player_action(self.player, _attack_key(), [self.host])
        self.assertEqual(result["outcome"], "exam_passed")
        self.assertEqual(self.player.guild_rank, "E")
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), 50)
        kinds = [entry.kind for log in result["logs"] for entry in log.entries]
        self.assertIn("target_defeated", kinds)
        self.assertNotIn("target_knocked_out", kinds)
        self._assert_full_normal_pools(self.player)
        self._assert_host_restored(baseline)

    @covers_requirement("guild-rank-exams::examination-combat-is-a-simulated-lethal-battle-with-full-restoration-around-it")
    def test_candidate_defeat_fails_without_injury_and_restores_both(self):
        baseline = self._host_normal()
        start_guild_exam(self.player, self.host, "E")
        self.player.traits.hp.current = 1
        with _Dice(100):
            result = submit_player_action(self.player, _attack_key(), [self.host])
        self.assertEqual(result["outcome"], "exam_failed")
        self.assertEqual(self.player.guild_rank, "F")
        self._assert_full_normal_pools(self.player)
        self._assert_host_restored(baseline)

    @covers_requirement("guild-rank-exams::examination-combat-is-a-simulated-lethal-battle-with-full-restoration-around-it")
    def test_wounded_candidate_and_host_start_at_full_applicable_pools(self):
        for entity in (self.player, self.host):
            for key in ("hp", "mp", "sp"):
                getattr(entity.traits, key).current = 1
        start_guild_exam(self.player, self.host, "E")
        self._assert_full_normal_pools(self.player)
        self._assert_full_normal_pools(self.host)
        self.assertEqual(self.host.traits.hp.current, EXAM_PROFILES["E"].ceilings["hp"])

    @covers_requirement("guild-rank-exams::examination-combat-is-a-simulated-lethal-battle-with-full-restoration-around-it")
    def test_lethal_exam_defeat_grants_no_kill_rewards_or_growth(self):
        proficiency = dict(self.host.db.skill_proficiency)
        self._make_overwhelming()
        start_guild_exam(self.player, self.host, "E")
        with _Dice(100):
            result = submit_player_action(self.player, _attack_key(), [self.host])
        defeated = [e for log in result["logs"] for e in log.entries if e.kind == "target_defeated"]
        self.assertTrue(defeated)
        self.assertTrue(all(entry.data.get("simulated") is True for entry in defeated))
        self.assertIsNone(self.player.db.magic_xp)
        self.assertEqual(self.player.db.quest_log, [])
        self.assertEqual(dict(self.host.db.skill_proficiency), proficiency)

    @covers_requirement(
        "guild-rank-exams::exam-settlement-is-idempotent-and-promotes-only-a-passing-candidate",
        "player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes",
    )
    def test_forfeit_fails_restores_the_host_and_retries_with_the_same_host(self):
        baseline = self._host_normal()
        start_guild_exam(self.player, self.host, "E")
        result = forfeit(self.player)
        self.assertEqual(result["outcome"], "exam_failed")
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.FAILED)
        self._assert_host_restored(baseline)
        retry = start_guild_exam(self.player, self.host, "E")
        self.assertEqual(retry.exam_id, f"{self.player.pk}:E:2")
        self.assertEqual(retry.opponent_id, self.host.pk)

    @covers_requirement("guild-rank-exams::exam-settlement-is-idempotent-and-promotes-only-a-passing-candidate")
    def test_replayed_settlement_cannot_promote_twice(self):
        start_guild_exam(self.player, self.host, "E")
        session = read_session(self.player)
        settle_exam_outcome(self.player, session, None, "exam_passed")
        settle_exam_outcome(self.player, session, None, "exam_passed")
        self.assertEqual(self.player.guild_rank, "E")
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.PASSED)

    @covers_requirement(
        "guild-rank-exams::exam-opponents-use-validated-true-stat-rank-profiles",
        "guild-rank-exams::exam-opponents-use-collision-free-unique-display-keys",
    )
    def test_repeated_e_and_d_exams_keep_one_unchanged_persistent_host(self):
        baseline = self._host_normal()
        self._make_overwhelming()
        for target, merit in (("E", 50), ("D", 600)):
            with self.subTest(target=target):
                self._give_merit(merit)
                record = start_guild_exam(self.player, self.host, target)
                self.assertEqual(record.opponent_id, baseline["pk"])
                self.assertEqual(self.host.key, baseline["key"])
                # Learned bases stay literal while the restriction lowers.
                self.assertEqual(self._host_normal()["bases"], baseline["bases"])
                with _Dice(100):
                    result = submit_player_action(self.player, _attack_key(), [self.host])
                self.assertEqual(result["outcome"], "exam_passed")
                self._assert_host_restored(baseline)
        self.assertEqual(self.player.guild_rank, "D")

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_round_settlement_failure_restores_host_surfaces_for_retry(self):
        self._make_overwhelming()
        start_guild_exam(self.player, self.host, "E")
        during = self._host_state()
        with _Dice(100), patch(
            "world.rules.guild_exams.release_exam_schedule_hold",
            side_effect=RuntimeError("release failed"),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, _attack_key(), [self.host])
        self.assertEqual(self._host_state()["normal"], during["normal"])
        self.assertEqual(self._host_state()["hold"], during["hold"])
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.ACTIVE)
        self.assertIsNotNone(read_session(self.player))
        with _Dice(100):
            result = submit_player_action(self.player, _attack_key(), [self.host])
        self.assertEqual(result["outcome"], "exam_passed")
        self.assertEqual(self.player.guild_rank, "E")


class ExamSettlementRecoveryTests(ExamHostFixture, EvenniaTestCase):
    """Terminal settlement, rollback/retry and cold-start recovery."""

    def setUp(self):
        super().setUp()
        self._give_merit(50)

    @covers_requirement("guild-rank-exams::exam-settlement-is-idempotent-and-promotes-only-a-passing-candidate")
    def test_terminal_fault_at_every_checkpoint_restores_and_retries_once(self):
        from world.rules.combat_session.settlement import _settle_with_restore

        checkpoints = {
            "title": ("world.rules.titles.grant_rank_title", "exam_passed"),
            "outfit": ("world.rules.guild_exam_restrictions.remove_exam_restriction", "exam_failed"),
            "session": ("world.rules.combat_session.settlement.clear_session", "exam_failed"),
            "hold": ("world.rules.guild_exams.release_exam_schedule_hold", "exam_failed"),
        }
        start_guild_exam(self.player, self.host, "E")
        host_before = self._host_state()
        actor_before = self._actor_state()
        clock_before = get_world_clock().tick
        for name, (target, outcome) in checkpoints.items():
            with self.subTest(checkpoint=name):
                with patch(target, side_effect=RuntimeError(name)), self.assertRaises(RuntimeError):
                    _settle_with_restore(self.player, read_session(self.player), None, outcome)
                self.assertEqual(self._host_state(), host_before)
                self.assertEqual(self._actor_state(), actor_before)
                self.assertEqual(get_world_clock().tick, clock_before)
        result = _settle_with_restore(self.player, read_session(self.player), None, "exam_passed")
        self.assertEqual(result["exam"]["state"], "passed")
        self.assertEqual(self.player.guild_rank, "E")
        title_key = live_guild_rank_registry()["E"].title_key
        self.assertEqual(
            [row["key"] for row in self.player.db.title_collection].count(title_key), 1
        )

    @covers_requirement(
        "guild-rank-exams::exam-settlement-is-idempotent-and-promotes-only-a-passing-candidate",
        "player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes",
    )
    def test_coherent_cold_start_resumes_the_same_host_restriction_and_hold(self):
        from world.rules.skip_safety import _BATTLEFIELDS

        record = start_guild_exam(self.player, self.host, "E")
        _BATTLEFIELDS.clear()
        restore_active_session(self.player)
        session = read_session(self.player)
        self.assertIsNotNone(session)
        self.assertEqual(session.enemy_ids, (self.host.pk,))
        self.assertEqual(exam_restriction(self.host)["exam_id"], record.exam_id)
        self.assertEqual(read_exam_schedule_hold(self.host).hold.exam_id, record.exam_id)
        self.assertIn(str(self.host.pk), _BATTLEFIELDS)

    @covers_requirement(
        "guild-rank-exams::exam-settlement-is-idempotent-and-promotes-only-a-passing-candidate",
        "player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes",
    )
    def test_incoherent_cold_start_fails_once_and_restores_the_host(self):
        for corruption in ("missing_hold", "collision", "missing_record", "malformed_history"):
            with self.subTest(corruption=corruption):
                baseline = self._host_normal()
                player = self._candidate(f"recovery {corruption}")
                register_adventurer(player, self.counter)
                self._give_merit(50, player)
                start_guild_exam(player, self.host, "E")
                if corruption == "missing_hold":
                    self.host.attributes.remove(HOLD_ATTRIBUTE)
                elif corruption == "collision":
                    player.key = self.host.key
                    player.save()
                elif corruption == "missing_record":
                    player.db.guild_exams = []
                else:
                    player.db.guild_exams = 5
                restore_active_session(player)
                self.assertIsNone(read_session(player))
                self.assertEqual(player.guild_rank, "F")
                self._assert_host_restored(baseline)
                if corruption in ("missing_hold", "collision"):
                    self.assertEqual(_read_exams(player)[0].state, ExamState.FAILED)
                    restore_active_session(player)
                    self.assertEqual(len(_read_exams(player)), 1)

    @covers_requirement("guild-rank-exams::exam-settlement-is-idempotent-and-promotes-only-a-passing-candidate")
    def test_late_restoration_for_another_exam_leaves_the_active_host_untouched(self):
        from world.rules.guild_exams import restore_exam_host

        start_guild_exam(self.player, self.host, "E")
        self.host.traits.hp.current = 1
        during = self._host_state()
        restore_exam_host(self.host, "stale:E:9")
        self.assertEqual(self._host_state(), during)

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_restored_exam_session_settles_time_exactly_once(self):
        from world.rules.combat_session import (
            _persist,
            from_storage as session_from_storage,
            to_storage as session_to_storage,
        )

        baseline = self._host_normal()
        start_guild_exam(self.player, self.host, "E")
        session = read_session(self.player)
        _persist(self.player, session_from_storage({
            **session_to_storage(session),
            "rounds_elapsed": 2,
            "knocked_out_ids": [int(self.host.pk)],
        }))
        self.host.traits.hp.current = 0
        tick = get_world_clock().tick
        restore_active_session(self.player)
        self.assertEqual(get_world_clock().tick, tick + 12)
        self.assertEqual(_read_exams(self.player)[0].state, ExamState.PASSED)
        self.assertIsNone(read_session(self.player))
        self._assert_host_restored(baseline)


class ExamScheduleIntegrationTests(ExamHostFixture, EvenniaTestCase):
    """A departure crossed during the exam replays once after release."""

    def setUp(self):
        super().setUp()
        from typeclasses.exits import Exit
        from world.rules import clock as clock_module
        from world.rules.npc_schedules import (
            ScheduleEntry,
            ScheduleRulebook,
            ScheduleTemplate,
            register_npc_schedules,
            set_npc_schedule,
        )

        self.home = create_object(Room, key="host home")
        create_object(Exit, key="home", location=self.hall, destination=self.home)
        create_object(Exit, key="hall", location=self.home, destination=self.hall)
        self.clock.tick = 86400 - 3
        self.clock._persist(self.clock.tick)
        book = ScheduleRulebook(1, ("duty", "busy", "resting"), (
            ScheduleTemplate("t_exam_routine", (
                ScheduleEntry(3600, "move", target="t_hall"),
                ScheduleEntry(86400 - 1, "move", target="t_home"),
            ), default_state="duty", cycle_days=1),
        ))
        for target, kwargs in (
            ("world.rules.npc_schedules.get_rulebook", {"return_value": book}),
            ("world.rules.npc_schedules._resolve_destination", {
                "side_effect": {"t_hall": self.hall, "t_home": self.home}.get,
            }),
        ):
            mock = patch(target, **kwargs)
            mock.start()
            self.addCleanup(mock.stop)
        sources = patch.dict(clock_module._EVENT_SOURCES, {}, clear=True)
        sources.start()
        self.addCleanup(sources.stop)
        register_npc_schedules()
        set_npc_schedule(self.host, {"schema_version": 1, "template": "t_exam_routine"})
        self.host.db.schedule_state = "duty"
        self._give_merit(50)

    def test_crossed_departure_is_deferred_then_replayed_once(self):
        start_guild_exam(self.player, self.host, "E")
        start_tick = get_world_clock().tick
        # One six-second round crosses the authored departure: the host stays.
        with _Dice(1):
            submit_player_action(self.player, _attack_key(), [self.host])
        self.assertEqual(self.host.location, self.hall)
        forfeit(self.player)
        self.assertEqual(self.host.location, self.home)
        hold = read_exam_schedule_hold(self.host).hold
        self.assertTrue(hold.released)
        # Combat time settled once; the replay consumed no extra clock time.
        self.assertEqual(get_world_clock().tick - start_tick, 6 * 1)
        self.assertIsNone(exam_restriction(self.host))


if __name__ == "__main__":
    unittest.main()
