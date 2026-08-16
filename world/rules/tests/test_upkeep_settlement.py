"""Upkeep settlement tests (fix-dot-kill-credit task 3.6)."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.quests.definitions import QuestStage
from world.quests.planner import quest_event_effect_planner
from world.quests.runtime import accept_quest, read_records, to_storage
from world.quests.tests._fixtures import QuestRegistryIsolation, defeat, quest, register
from world.rules.action import (
    PendingEffect,
    RejectReason,
    _EVENT_EFFECT_PLANNERS,
    _commit,
    register_event_effect_planner,
)
from world.rules.buffs import TickRecord, _add_buff, tick_buffs
from world.rules.combat import Battlefield
from world.rules.party import join_party
from world.rules.progression import COMBAT_KILL_XP_TABLE
from world.rules.upkeep import UPKEEP_SKILL_KEY, settle_upkeep


def _player(key="upkeep player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.traits.magic_level.base = 30
    return player


def _monster(key="upkeep goblin", hp=10, tier="low"):
    monster = create_object(Monster, key=key)
    monster.threat_tier = tier
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


def _npc(key="upkeep npc", hp=10):
    npc = create_object(NPC, key=key)
    npc.race = "human"
    npc.apply_race_baseline()
    npc.traits.hp.base = hp
    npc.traits.hp.current = hp
    return npc


def _field(*entities):
    teams = {}
    roster = {}
    for index, entity in enumerate(entities):
        team = "party" if index == 0 else "foes"
        teams.setdefault(team, set()).add(entity.key)
        roster[entity.key] = entity
    return Battlefield(
        {team: frozenset(members) for team, members in teams.items()},
        roster,
    )


def _tick_records(entity, seconds=10) -> dict[str, tuple[TickRecord, ...]]:
    """Fire one upkeep tick on an entity and return the record grouping."""
    return {entity.key: tick_buffs(entity, seconds)}


class UpkeepSettlementTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.actor = _player()
        self.monster = _monster(hp=3)

    def _logs(self, records_by_key, **kwargs):
        field = _field(self.actor, self.monster)
        return settle_upkeep(field, records_by_key, **kwargs)

    def _kinds(self, logs):
        return [
            entry.kind
            for log in logs
            for entry in log.entries
        ]

    @covers_requirement("combat-upkeep-settlement::damaging-rate-ticks-settle-through-a-deterministic-event-producing-boundary-within-the-combat-round")
    def test_lethal_tick_emits_one_defeat_and_damage_entry(self):
        _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(self.monster)
        self.assertEqual(self.monster.traits.hp.current, 0)
        logs = self._logs(records)
        kinds = self._kinds(logs)
        self.assertEqual(kinds.count("target_defeated"), 1)
        self.assertEqual(kinds.count("damage"), 1)
        self.assertEqual(logs[0].actor, self.actor.key)
        self.assertEqual(logs[0].skill_key, UPKEEP_SKILL_KEY)

    @covers_requirement("combat-upkeep-settlement::damaging-rate-ticks-settle-through-a-deterministic-event-producing-boundary-within-the-combat-round")
    def test_damage_entry_reports_clamped_applied_amount(self):
        _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(self.monster)
        logs = self._logs(records)
        damage = next(
            entry
            for log in logs
            for entry in log.entries
            if entry.kind == "damage"
        )
        self.assertEqual(damage.data["amount"], 3)
        self.assertEqual(self.monster.traits.hp.current, 0)

    @covers_requirement("combat-upkeep-settlement::damaging-rate-ticks-settle-through-a-deterministic-event-producing-boundary-within-the-combat-round")
    def test_multiple_dots_in_one_tick_emit_one_defeat(self):
        _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
        _add_buff(self.monster, "fire_scorch", source_pk=int(self.actor.pk))
        records = _tick_records(self.monster)
        logs = self._logs(records)
        kinds = self._kinds(logs)
        self.assertEqual(kinds.count("target_defeated"), 1)
        defeated = next(
            entry
            for log in logs
            for entry in log.entries
            if entry.kind == "target_defeated"
        )
        self.assertEqual(defeated.data["target_id"], int(self.monster.pk))
        self.assertEqual(defeated.data["monster_tier"], "low")

    @covers_requirement("combat-upkeep-settlement::damaging-rate-ticks-settle-through-a-deterministic-event-producing-boundary-within-the-combat-round")
    def test_dead_target_records_never_settle_twice(self):
        # Upkeep skips non-living roster members, so a target the applying
        # action already killed never ticks again and can never double-settle.
        from world.rules.combat import _end_of_round_upkeep

        _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
        self.monster.traits.hp.current = 0
        field = _field(self.actor, self.monster)
        records_by_key = _end_of_round_upkeep(field)
        self.assertNotIn(self.monster.key, records_by_key)
        logs = settle_upkeep(field, records_by_key)
        self.assertEqual(logs, [])

    @covers_requirement("combat-upkeep-settlement::upkeep-kill-credit-requires-validated-resolvable-source-identity")
    def test_attributed_lethal_tick_awards_tiered_monster_xp_once(self):
        _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(self.monster)
        self._logs(records)
        self.assertEqual(
            self.actor.db.magic_xp,
            COMBAT_KILL_XP_TABLE["low"],
        )

    @covers_requirement("combat-upkeep-settlement::upkeep-kill-credit-requires-validated-resolvable-source-identity")
    def test_deleted_or_absent_source_grants_no_credit(self):
        _add_buff(self.monster, "poisoned")
        records = _tick_records(self.monster)
        self.assertEqual(self.monster.traits.hp.current, 0)
        logs = self._logs(records)
        self.assertEqual(logs, [])
        self.assertIsNone(self.actor.db.magic_xp)

    def test_source_outside_the_roster_resolves_from_the_database(self):
        bystander = _player("bystander")
        _add_buff(self.monster, "poisoned", source_pk=int(bystander.pk))
        records = _tick_records(self.monster)
        field = _field(self.actor, self.monster)
        logs = settle_upkeep(field, records)
        self.assertEqual(logs[0].actor, bystander.key)
        self.assertEqual(bystander.db.magic_xp, COMBAT_KILL_XP_TABLE["low"])

    @covers_requirement("combat-upkeep-settlement::upkeep-kill-credit-requires-validated-resolvable-source-identity")
    def test_same_key_sources_keep_distinct_credit(self):
        # Evennia keys are not unique: two casters sharing one display key
        # must keep separate logs, XP, and planner actors. The second caster
        # owns the lethal tick; the first must receive nothing.
        first = _player("twin caster")
        second = _player("twin caster")
        victim = _monster("same-key victim", hp=8)
        _add_buff(victim, "poisoned", source_pk=int(first.pk))
        _add_buff(victim, "fire_scorch", source_pk=int(second.pk))
        records = _tick_records(victim)
        field = _field(self.actor, victim)
        observed_actors = []

        def spy_planner(request, log):
            observed_actors.append(request.actor)
            return []

        with patch.dict(_EVENT_EFFECT_PLANNERS, {"spy": spy_planner}):
            logs = settle_upkeep(field, records)
        self.assertEqual(victim.traits.hp.current, 0)
        self.assertEqual(len(logs), 2)
        self.assertEqual(observed_actors, [second])
        self.assertIsNone(first.db.magic_xp)
        self.assertEqual(second.db.magic_xp, COMBAT_KILL_XP_TABLE["low"])

    @covers_requirement("combat-upkeep-settlement::upkeep-kill-credit-requires-validated-resolvable-source-identity")
    def test_non_monster_target_grants_no_xp(self):
        npc = _npc(hp=3)
        _add_buff(npc, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(npc)
        field = _field(self.actor, npc)
        logs = settle_upkeep(field, records)
        self.assertIn("target_defeated", self._kinds(logs))
        self.assertIsNone(self.actor.db.magic_xp)

    def test_untiered_monster_grants_no_xp(self):
        untiered = _monster(hp=3)
        untiered.threat_tier = "bogus"
        _add_buff(untiered, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(untiered)
        field = _field(self.actor, untiered)
        settle_upkeep(field, records)
        self.assertIsNone(self.actor.db.magic_xp)

    @covers_requirement("combat-upkeep-settlement::upkeep-settlement-honors-simulated-and-nonlethal-combat-policy")
    def test_simulated_tick_tags_defeat_and_grants_no_xp(self):
        _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(self.monster)
        logs = self._logs(records, simulated=True)
        defeated = next(
            entry
            for log in logs
            for entry in log.entries
            if entry.kind == "target_defeated"
        )
        self.assertTrue(defeated.data["simulated"])
        self.assertIsNone(self.actor.db.magic_xp)

    @covers_requirement("combat-upkeep-settlement::upkeep-settlement-honors-simulated-and-nonlethal-combat-policy")
    def test_nonlethal_companion_crossing_floors_and_marks_knocked_out(self):
        companion = _npc("upkeep companion", hp=3)
        _add_buff(companion, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(companion)
        field = _field(self.actor, companion)
        logs = settle_upkeep(
            field,
            records,
            nonlethal_keys=frozenset({companion.key}),
        )
        kinds = self._kinds(logs)
        self.assertIn("target_knocked_out", kinds)
        self.assertNotIn("target_defeated", kinds)
        self.assertEqual(companion.traits.hp.current, 1)
        self.assertIn(companion.key, field.knocked_out)
        self.assertIsNone(self.actor.db.magic_xp)

    @covers_requirement("combat-upkeep-settlement::upkeep-settlement-honors-simulated-and-nonlethal-combat-policy")
    def test_non_crossing_tick_on_protected_target_changes_nothing(self):
        companion = _npc("upkeep healthy companion", hp=100)
        _add_buff(companion, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(companion)
        field = _field(self.actor, companion)
        logs = settle_upkeep(
            field,
            records,
            nonlethal_keys=frozenset({companion.key}),
        )
        self.assertNotIn(companion.key, field.knocked_out)
        self.assertEqual(companion.traits.hp.current, 95)
        self.assertEqual(self._kinds(logs), ["damage"])

    @covers_requirement("combat-upkeep-settlement::upkeep-tick-damage-outside-combat-rounds-produces-no-events-or-credit")
    def test_clock_path_ignoring_records_changes_hp_only(self):
        entity = _player("clock entity")
        _add_buff(entity, "poisoned", source_pk=int(entity.pk))
        before = entity.traits.hp.current
        tick_buffs(entity, 10)
        self.assertEqual(entity.traits.hp.current, before - 5)


class UpkeepQuestPlannerTests(QuestRegistryIsolation, EvenniaTestCase):
    """Upkeep-settled defeats drive the quest planner like action defeats."""

    def setUp(self):
        super().setUp()
        register_event_effect_planner("quest", quest_event_effect_planner)
        self.actor = _player()
        self.monster = _monster(hp=3)
        self.quest_def = register(
            quest(
                "upkeep_hunt",
                stages=(QuestStage(0, defeat()),),
            )
        )
        accept_quest(self.actor, self.quest_def.key)

    def tearDown(self):
        _EVENT_EFFECT_PLANNERS.pop("quest", None)
        super().tearDown()

    def _records(self):
        return [to_storage(record) for record in read_records(self.actor)]

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_upkeep_defeat_advances_the_matching_objective(self):
        _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(self.monster)
        field = _field(self.actor, self.monster)
        settle_upkeep(field, records)
        stored = self._records()[0]
        self.assertEqual(stored["stage_progress"], 1)
        self.assertEqual(stored["state"], "completed")

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_simulated_upkeep_kill_grants_no_quest_progress(self):
        _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(self.monster)
        field = _field(self.actor, self.monster)
        settle_upkeep(field, records, simulated=True)
        stored = self._records()[0]
        self.assertEqual(stored["stage_progress"], 0)
        self.assertEqual(stored["state"], "in_progress")

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_unattributed_upkeep_kill_grants_no_quest_progress(self):
        _add_buff(self.monster, "poisoned")
        records = _tick_records(self.monster)
        field = _field(self.actor, self.monster)
        settle_upkeep(field, records)
        stored = self._records()[0]
        self.assertEqual(stored["stage_progress"], 0)

    def test_planner_runs_only_for_sources_with_defeat_entries(self):
        observed = []

        def spy_planner(request, log):
            observed.append(log)
            return []

        with patch.dict(_EVENT_EFFECT_PLANNERS, {"spy": spy_planner}):
            near_dead = _monster("near-dead", hp=100)
            _add_buff(near_dead, "poisoned", source_pk=int(self.actor.pk))
            records = _tick_records(near_dead)
            field = _field(self.actor, near_dead)
            settle_upkeep(field, records)
        self.assertEqual(observed, [])

    def test_planner_failure_propagates_and_commit_restores_staged_surfaces(self):
        def boom(request, log):
            raise RuntimeError("planner boom")

        with patch.dict(_EVENT_EFFECT_PLANNERS, {"boom": boom}):
            with self.assertRaises(RuntimeError):
                _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
                records = _tick_records(self.monster)
                field = _field(self.actor, self.monster)
                settle_upkeep(field, records)
        # The XP effect was staged but never committed: the round aborted.
        self.assertIsNone(self.actor.db.magic_xp)


class UpkeepKnockoutParityTests(QuestRegistryIsolation, EvenniaTestCase):
    """A knocked-out companion's tick mirrors the action path's credit rules."""

    def setUp(self):
        super().setUp()
        register_event_effect_planner("quest", quest_event_effect_planner)
        from evennia.utils.create import create_object

        from typeclasses.rooms import Room

        self.room = create_object(Room, key="upkeep room")
        self.owner = _player("upkeep owner")
        self.owner.location = self.room
        self.quest_def = register(
            quest(
                "upkeep_owner_hunt",
                stages=(QuestStage(0, defeat()),),
            )
        )
        accept_quest(self.owner, self.quest_def.key)
        self.companion = _npc("upkeep companion")
        self.companion.location = self.room
        join_party(self.companion, self.owner)
        self.monster = _monster(hp=3)

    def tearDown(self):
        _EVENT_EFFECT_PLANNERS.pop("quest", None)
        super().tearDown()

    @covers_requirement("quest-progress-tracking::defeat-progress-is-planned-automatically-from-committed-player-action-events")
    def test_knocked_out_companion_tick_earns_companion_xp_but_no_owner_credit(self):
        _add_buff(self.monster, "poisoned", source_pk=int(self.companion.pk))
        records = _tick_records(self.monster)
        field = Battlefield(
            {
                "party": frozenset({self.owner.key, self.companion.key}),
                "foes": frozenset({self.monster.key}),
            },
            {
                self.owner.key: self.owner,
                self.companion.key: self.companion,
                self.monster.key: self.monster,
            },
            knocked_out={self.companion.key},
        )
        settle_upkeep(field, records)
        self.assertEqual(
            self.companion.db.magic_xp,
            COMBAT_KILL_XP_TABLE["low"],
        )
        stored = [to_storage(record) for record in read_records(self.owner)][0]
        self.assertEqual(stored["stage_progress"], 0)


class UpkeepCommitFailureTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.actor = _player()
        self.monster = _monster(hp=3)

    def test_commit_failure_never_commits_staged_xp(self):
        _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(self.monster)
        field = _field(self.actor, self.monster)
        original_commit = _commit
        from world.rules import upkeep as upkeep_module

        def failing_commit(pending):
            for effect in pending:
                if effect.description.startswith("combat_kill_xp"):
                    raise RuntimeError("commit boom")
            return original_commit(pending)

        with patch.object(upkeep_module, "_commit", failing_commit):
            with self.assertRaises(RuntimeError):
                settle_upkeep(field, records)
        self.assertIsNone(self.actor.db.magic_xp)

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_partially_applied_commit_restores_every_staged_surface(self):
        # A genuine mid-commit failure: the XP effect applies first, then a
        # planner-shaped effect raises inside the real ``_commit``. The
        # commit's snapshot/restore must roll the already-applied XP back
        # with the failed effect (the session outer transaction covers the
        # tick HP separately).
        _add_buff(self.monster, "poisoned", source_pk=int(self.actor.pk))
        records = _tick_records(self.monster)
        field = _field(self.actor, self.monster)
        with patch.dict(
            _EVENT_EFFECT_PLANNERS,
            {
                "failing_planner": lambda request, log: [
                    PendingEffect(
                        entity=self.actor,
                        description="injected commit failure",
                        surfaces=frozenset({"progression"}),
                        apply=lambda: (_ for _ in ()).throw(
                            RuntimeError("injected apply failure")
                        ),
                    )
                ]
            },
        ):
            with self.assertRaises(Exception) as caught:
                settle_upkeep(field, records)
        self.assertEqual(caught.exception.reason, RejectReason.COMMIT_FAILED)
        # The XP staged by the earlier effect in the same commit rolled back
        # with the failing effect.
        self.assertIsNone(self.actor.db.magic_xp)
