"""Behavior tests for the monster-AI decision inputs (legal snapshots).

Two kinds of fixture, both synthetic: file-local probe participants whose
materializing handlers are booby-trapped and whose persisted attribute store
counts every read, and file-local ``t_``-named skill rows registered for one
test. No shipped key, display string or catalog symbol is named here.

The tests establish the slice's three contracts: a snapshot is read-only and
public (no handler, cache, gauge timestamp or state write; no queued request,
teammate choice or disguised stat can reach it), legality is the settlement
gates' own (the same ordered conditions and the same rejection the resolver
raises), and one decision reads its registry, owned metadata, costs, traits and
buff projections once and refreshes them for the next action.
"""

import unittest
from collections import defaultdict
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.monsters import Monster
from typeclasses.rooms import Room

from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.action_preview import preview_skill, revalidate_submission
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    active_buff_keys_from_storage,
    apply_buff,
    entity_active_buffs,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_session import engage, read_session, reconstruct_battlefield
from world.rules.monster_ai import (
    DecisionReads,
    DecisionScope,
    PlannedAction,
    PublicObservation,
    build_decision_snapshot,
    roster_index,
    stable_identity,
    validate_plan,
)
from world.skills.cast_conditions import CastCondition, CastConditionSubject
from world.skills.effects import InteractionPolicy
from world.skills.handler import SkillHandler
from world.skills.registry import SkillCategory, TargetSpec

from ._combat_session_helpers import (
    _monster,
    _player,
    open_synthetic_scope,
    synth_damage_skill,
    synth_innate_overlay,
)

# --- locally authored rows ---------------------------------------------------
#: The buff key one synthetic cast condition requires of its target.
SEAL = "t_snap_seal"
#: A second buff key no condition names, for the projection assertions.
WARD = "t_snap_ward"

SCOPE = "normal:11:0"
ROUND = 11

#: An ordinary SINGLE physical damage skill: the "old preview subset" fixture.
STRIKE = synth_damage_skill("t_snap_strike", "測試裂擊", cost={"mp": 8})
#: The same skill with a real per-target cast prerequisite the older preview
#: subset never evaluated.
SEALED_STRIKE = replace(
    STRIKE,
    key="t_snap_sealed_strike",
    cast_conditions=(
        CastCondition(CastConditionSubject.EACH_TARGET, {"buff_active": SEAL}),
    ),
)
#: A SELF-bound contact skill requiring distinct participants: the actor can
#: never satisfy it, which the older preview subset never noticed.
CONTACT_SELF = replace(
    synth_damage_skill("t_snap_contact_self", "測試獨契", effects=(), cost={}),
    target_spec=TargetSpec.SELF,
    interaction=InteractionPolicy(contact=True, distinct_participants=True),
)
#: The accepted pair: the same contact skill without the distinct-participant
#: requirement.
CONTACT_SELF_SOLO = replace(
    CONTACT_SELF,
    key="t_snap_contact_solo",
    interaction=InteractionPolicy(contact=True, distinct_participants=False),
)
#: A two-participant act: its requirement forbids the actor as its own target.
PAIRED_ACT = replace(
    synth_damage_skill("t_snap_paired_act", "測試雙人術", effects=(), cost={}),
    category=SkillCategory.SEXUAL_ACT,
)


def _skill_rows() -> dict[str, object]:
    """The file-local skill rows one test registers."""
    return {
        row.key: row
        for row in (
            STRIKE,
            SEALED_STRIKE,
            CONTACT_SELF,
            CONTACT_SELF_SOLO,
            PAIRED_ACT,
        )
    }


def _scope(test, *extra_logicals):
    """Enter the kit scope this module's fixtures need."""
    extra = synth_innate_overlay()
    extra["skills"].update(_skill_rows())
    return open_synthetic_scope(
        test,
        "monster_tiers",
        "races",
        "skills",
        "elements",
        *extra_logicals,
        extra=extra,
    )


class _ProbeAttributes:
    """A persisted-attribute store that counts every read it answers."""

    def __init__(self, values: dict | None = None):
        self.values = dict(values or {})
        self.calls: dict[str, int] = defaultdict(int)

    def get(self, name, default=None, category=None):
        self.calls[name] += 1
        return self.values.get(name, default)

    def has(self, name, category=None):
        self.calls[name] += 1
        return name in self.values


class _ProbeTrait:
    """One live trait value the shared settlement gates may read."""

    def __init__(self, current: int, maximum: int, *, gauge: bool = True):
        self.trait_type = "gauge" if gauge else "static"
        self._data = {
            "base": maximum,
            "mod": 0,
            "mult": 1,
            "current": current,
        }
        if not gauge:
            self._data["value"] = current

    @property
    def max(self) -> int:
        return self._data["base"]


def _trait_record(base: int, *, current: int | None = None) -> dict:
    """One persisted trait record in the shape the trait handler writes."""
    record = {"base": base, "mod": 0, "mult": 1}
    if current is not None:
        record["current"] = current
    return record


def _buff_record(definition_key: str) -> dict:
    """One persisted buff-cache entry in the shape the buff handler writes."""
    return {
        "definition_key": definition_key,
        "paused": False,
        "stacks": 1,
        "remaining_seconds": None,
    }


class _ProbeSkills(SkillHandler):
    """The real skill handler, counting the owned-key reads a decision makes."""

    def __init__(self, entity):
        super().__init__(entity)
        self.owned_key_calls = 0

    def owned_keys(self):
        self.owned_key_calls += 1
        return super().owned_keys()


class _ProbeParticipant:
    """A participant double whose materializing handlers are booby-trapped.

    Reading ``buffs``, ``sexual`` or ``equipment`` raises, so a snapshot path
    that materialized one of those lazy handlers fails loudly instead of
    silently attaching it. The persisted attribute store, the live trait
    values a shared settlement gate may read, and the skill handler the
    decision genuinely reads through stay real reads, counted for the
    read-once assertions.
    """

    def __init__(
        self,
        key: str,
        *,
        skills: tuple[str, ...] = (),
        hp: int = 30,
        mp: int = 20,
        buffs: dict | None = None,
        pk: int | None = None,
    ):
        self.key = key
        if pk is not None:
            self.pk = pk
        self.db = SimpleNamespace(
            skills={"active": list(skills), "passive": []},
            skill_grants=[],
            equipment=None,
            disguised_stats=None,
        )
        self.attributes = _ProbeAttributes(
            {
                "traits": {
                    "hp": _trait_record(hp, current=hp),
                    "mp": _trait_record(mp, current=mp),
                    "sp": _trait_record(mp, current=mp),
                    "atk_phys": _trait_record(12),
                    "agility": _trait_record(9),
                    "defense": _trait_record(4),
                    "magic_power": _trait_record(11),
                    "guild_merit": {"value": 0},
                },
                "buffs": dict(buffs or {}),
            }
        )
        self.skills = _ProbeSkills(self)
        self.pending_choice = None
        self.trait_reads = 0

    @property
    def identity(self) -> str:
        """The stable identity this participant's plans are written in."""
        return stable_identity(self)

    @property
    def traits(self):
        """The live trait values, counted (never a materialized handler)."""
        self.trait_reads += 1
        records = self.attributes.values["traits"]
        return SimpleNamespace(
            **{
                name: _ProbeTrait(
                    int(record.get("current", record.get("base", 0)) or 0),
                    int(record.get("base", 0) or 0),
                    gauge="current" in record,
                )
                for name, record in records.items()
            }
        )

    @property
    def buffs(self):
        raise AssertionError("the buff handler must not be materialized")

    @property
    def sexual(self):
        raise AssertionError("the sexual handler must not be materialized")

    @property
    def equipment(self):
        raise AssertionError("the equipment handler must not be materialized")


def _probe_field(actor: _ProbeParticipant, *others):
    """A two-team battlefield over probe participants."""
    roster = {actor.key: actor}
    enemies = frozenset({other.key for other in others})
    if not enemies:
        raise ValueError("a probe field needs at least one opponent")
    for other in others:
        roster[other.key] = other
    return Battlefield(
        {"monsters": frozenset({actor.key}), "party": enemies}, roster
    )


def _entry(actor, context, participants, *, reads=None):
    """One decision's snapshot, reads and reconstruction index."""
    reader = DecisionReads() if reads is None else reads
    pool = tuple(participants)
    snapshot = build_decision_snapshot(
        actor,
        context,
        scope=DecisionScope(SCOPE, ROUND, 0),
        participants=pool,
        observations=(
            PublicObservation(
                round_index=ROUND,
                sequence=1,
                source_id=stable_identity(pool[0]),
                action_key=STRIKE.key,
                recipient_ids=(stable_identity(actor),),
                statuses=("resolved",),
            ),
        ),
        context_mode="normal",
        reads=reader,
    )
    return snapshot, reader, roster_index((actor, *pool)), context


def _probe_decision(actor, *others, reads=None):
    """One decision over probes, with its context and reconstruction index."""
    return _entry(actor, BattlefieldActionContext(_probe_field(actor, *others)), others, reads=reads)


def _read_counters(probe: _ProbeParticipant) -> dict[str, int]:
    """Every counted read one probe participant answered, flattened."""
    counters = {f"attr:{name}": count for name, count in probe.attributes.calls.items()}
    counters["owned_keys"] = probe.skills.owned_key_calls
    counters["trait_reads"] = probe.trait_reads
    return counters


def _counter_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, tuple]:
    """The counters that moved, as ``name -> (before, after)``."""
    return {
        name: (before.get(name, 0), after.get(name, 0))
        for name in set(before) | set(after)
        if before.get(name, 0) != after.get(name, 0)
    }


class DecisionSnapshotReadTests(unittest.TestCase):
    """The snapshot and its reads are no-create, public and decision-local."""

    def setUp(self):
        self.actor = _ProbeParticipant("t_snap_actor", skills=(SEALED_STRIKE.key,))
        self.target = _ProbeParticipant("t_snap_target")
        self.registry = patch.dict(
            "world.skills.registry.SKILL_REGISTRY", _skill_rows(), clear=True
        )
        self.registry.start()
        self.addCleanup(self.registry.stop)

    def test_the_snapshot_reads_storage_without_touching_a_handler(self):
        snapshot, reads, _roster, _context = _probe_decision(
            self.actor, self.target
        )
        self.assertEqual(snapshot.actor.traits["atk_phys"], 12.0)
        self.assertEqual(snapshot.actor.resources["mp"], (20, 20))
        self.assertEqual(snapshot.actor.identity, "key:t_snap_actor")
        self.assertEqual(snapshot.participants[0].identity, self.target.identity)
        self.assertFalse(snapshot.actor.capability.blocked_by_buff)
        self.assertEqual(
            dict(reads.buff_projections(self.target)), {}
        )
        self.assertGreater(self.actor.attributes.calls["traits"], 0)
        self.assertEqual(
            [skill.key for skill in snapshot.owned_skills],
            [SEALED_STRIKE.key],
            "only the row this decision's registry carries is projected",
        )

    def test_building_a_snapshot_reads_each_input_once_per_participant(self):
        reads = DecisionReads()
        context = BattlefieldActionContext(_probe_field(self.actor, self.target))
        snapshot = build_decision_snapshot(
            self.actor,
            context,
            scope=DecisionScope(SCOPE, ROUND, 0),
            participants=(self.target,),
            reads=reads,
        )
        self.assertEqual(dict(snapshot.actor.traits)["hp"], 30.0)
        # A fixed number of storage reads per participant: the trait map is one
        # read and the effective fold reads the same attribute once per static
        # key. Neither depends on how many plans are later validated.
        self.assertEqual(
            self.actor.attributes.calls["traits"],
            self.target.attributes.calls["traits"],
        )
        reads_before = self.actor.skills.owned_key_calls
        self.assertIs(reads.owned_keys(self.actor), reads.owned_keys(self.actor))
        self.assertEqual(
            self.actor.skills.owned_key_calls,
            reads_before,
            "the decision's owned-skill metadata is read once and reused",
        )
        self.assertEqual(self.actor.trait_reads, 0, "storage first, handler never")

    def test_validation_reuses_one_read_set_across_every_plan(self):
        participants = tuple(
            _ProbeParticipant(f"t_snap_rival_{index}") for index in range(4)
        )
        self.actor.db.skills = {"active": [STRIKE.key], "passive": []}
        context = BattlefieldActionContext(
            _probe_field(self.actor, *participants)
        )
        reads = DecisionReads()
        snapshot, reads, roster, context = _entry(
            self.actor, context, participants, reads=reads
        )
        before = {
            **_read_counters(self.actor),
            **_read_counters(participants[0]),
        }
        for participant in participants:
            verdict = validate_plan(
                snapshot,
                PlannedAction(STRIKE.key, target_ids=(participant.identity,)),
                actor=self.actor,
                context=context,
                roster=roster,
                reads=reads,
            )
            self.assertTrue(verdict.legal, verdict.detail)
        after = {
            **_read_counters(self.actor),
            **_read_counters(participants[0]),
        }
        self.assertEqual(
            _counter_delta(before, after),
            {},
            "enumerating more plans must not re-read the decision's inputs",
        )

    def test_the_next_decision_sees_intervening_state_and_the_old_one_does_not(self):
        snapshot, _reads, _roster, _context = _probe_decision(
            self.actor, self.target
        )
        self.assertTrue(snapshot.participants[0].alive)
        self.assertEqual(snapshot.actor.resources["mp"], (20, 20))
        records = self.actor.attributes.values["traits"]
        records["mp"]["current"] = 3
        self.target.attributes.values["traits"]["hp"]["current"] = 0
        self.target.attributes.values["buffs"] = {SEAL: _buff_record(SEAL)}
        later, _reads, _roster, _context = _probe_decision(
            self.actor, self.target
        )
        self.assertEqual(later.actor.resources["mp"], (3, 20))
        self.assertFalse(later.participants[0].alive)
        self.assertEqual(
            [buff.key for buff in later.participants[0].buffs], [SEAL]
        )
        self.assertEqual(snapshot.actor.resources["mp"], (20, 20))
        self.assertTrue(snapshot.participants[0].alive)
        self.assertNotEqual(snapshot.fingerprint, later.fingerprint)

    def test_queued_intent_and_disguised_stats_cannot_reach_the_snapshot(self):
        teammate = _ProbeParticipant("t_snap_teammate", skills=(STRIKE.key,))
        first, _reads, _roster, _context = _probe_decision(
            self.actor, self.target, teammate
        )
        self.actor.pending_choice = "t_snap_sealed_strike"
        self.actor.db.disguised_stats = {"atk_phys": 999}
        teammate.pending_choice = "t_snap_strike"
        teammate.db.pending_intent = {"target": self.actor.key}
        second, _reads, _roster, _context = _probe_decision(
            self.actor, self.target, teammate
        )
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(dict(second.actor.traits), dict(first.actor.traits))
        self.assertEqual(
            [item.identity for item in second.participants],
            [item.identity for item in first.participants],
        )

    def test_the_fingerprint_is_the_snapshot_and_is_read_only(self):
        snapshot, _reads, _roster, _context = _probe_decision(
            self.actor, self.target
        )
        with self.assertRaises(FrozenInstanceError):
            snapshot.fingerprint = "tampered"
        identical, _reads, _roster, _context = _probe_decision(
            self.actor, self.target
        )
        self.assertEqual(snapshot.fingerprint, identical.fingerprint)
        self.assertEqual(len(snapshot.fingerprint), 64)
        self.assertEqual(
            [observation.sequence for observation in snapshot.observations], [1]
        )


class DecisionPlanLegalityTests(unittest.TestCase):
    """Complete settlement legality, shared plan by plan."""

    def setUp(self):
        self.actor = _ProbeParticipant("t_snap_actor", skills=(SEALED_STRIKE.key,))
        self.target = _ProbeParticipant("t_snap_target")
        self.registry = patch.dict(
            "world.skills.registry.SKILL_REGISTRY", _skill_rows(), clear=True
        )
        self.registry.start()
        self.addCleanup(self.registry.stop)

    def _own(self, *skill_keys):
        self.actor.db.skills = {"active": list(skill_keys), "passive": []}

    def _verdict(self, skill_key, *, target_ids=None, reads=None):
        snapshot, reader, roster, context = _probe_decision(
            self.actor, self.target, reads=reads
        )
        return validate_plan(
            snapshot,
            PlannedAction(
                skill_key,
                target_ids=(
                    (stable_identity(self.target),) if target_ids is None else target_ids
                ),
            ),
            actor=self.actor,
            context=context,
            roster=roster,
            reads=reader,
        )

    def test_a_cast_prerequisite_rejects_before_scoring_with_settlement_reason(self):
        self._own(SEALED_STRIKE.key)
        rejected = self._verdict(SEALED_STRIKE.key)
        self.assertFalse(rejected.legal)
        self.assertIs(rejected.reason, RejectReason.CAST_CONDITION_UNMET)
        self.target.attributes.values["buffs"] = {SEAL: _buff_record(SEAL)}
        accepted = self._verdict(SEALED_STRIKE.key)
        self.assertTrue(accepted.legal, accepted.detail)
        self.assertIsNone(accepted.reason)

    def test_a_contact_prerequisite_rejects_the_self_plan_and_accepts_the_solo_one(self):
        self._own(CONTACT_SELF.key, CONTACT_SELF_SOLO.key)
        rejected = self._verdict(CONTACT_SELF.key, target_ids=())
        self.assertFalse(rejected.legal)
        self.assertIs(rejected.reason, RejectReason.CAST_CONDITION_UNMET)
        accepted = self._verdict(CONTACT_SELF_SOLO.key, target_ids=())
        self.assertTrue(accepted.legal, accepted.detail)

    def test_a_forbidden_self_target_is_a_shape_mismatch(self):
        self._own(PAIRED_ACT.key)
        verdict = self._verdict(PAIRED_ACT.key, target_ids=(stable_identity(self.actor),))
        self.assertFalse(verdict.legal)
        self.assertIs(verdict.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_a_plan_outside_the_decision_scope_is_rejected(self):
        self._own(STRIKE.key)
        outsider = _ProbeParticipant("t_snap_outsider")
        verdict = self._verdict(STRIKE.key, target_ids=(outsider.identity,))
        self.assertFalse(verdict.legal)
        self.assertIs(verdict.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_a_drained_resource_rejects_the_next_decision(self):
        self._own(STRIKE.key)
        self.assertTrue(self._verdict(STRIKE.key).legal)
        self.actor.attributes.values["traits"]["mp"]["current"] = 1
        verdict = self._verdict(STRIKE.key)
        self.assertFalse(verdict.legal)
        self.assertIs(verdict.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(verdict.detail, "mp")

    def test_lost_capability_rejects_the_plan(self):
        self._own(STRIKE.key)
        with (
            patch(
                "world.rules.monster_ai.snapshot.evaluate_combat_modifiers_no_create",
                return_value={"actions_per_turn": 0},
            ),
            patch(
                "world.rules.action.gates.evaluate_combat_modifiers_no_create",
                return_value={"actions_per_turn": 0},
            ),
        ):
            verdict = self._verdict(STRIKE.key)
        self.assertFalse(verdict.legal)
        self.assertIs(verdict.reason, RejectReason.ACTION_FORBIDDEN)

    def test_a_dead_target_rejects_the_plan_before_scoring(self):
        self._own(STRIKE.key)
        self.target.attributes.values["traits"]["hp"]["current"] = 0
        verdict = self._verdict(STRIKE.key)
        self.assertFalse(verdict.legal)
        self.assertIs(verdict.reason, RejectReason.TARGET_DEAD)

    def test_a_vanished_participant_is_reported_missing(self):
        self._own(STRIKE.key)
        snapshot, reads, _roster, context = _probe_decision(
            self.actor, self.target
        )
        verdict = validate_plan(
            snapshot,
            PlannedAction(STRIKE.key, target_ids=(stable_identity(self.target),)),
            actor=self.actor,
            context=context,
            roster={stable_identity(self.actor): self.actor},
            reads=reads,
        )
        self.assertFalse(verdict.legal)
        self.assertIs(verdict.reason, RejectReason.TARGET_NOT_PRESENT)
        self.assertEqual(verdict.detail, self.target.identity)


class MonsterAIDecisionBoundaryTests(EvenniaTestCase):
    """The decision boundary on real entities writes nothing and attaches none."""

    def setUp(self):
        _scope(self)
        super().setUp()
        self.room = create_object(Room, key="snapshot arena")
        self.player = _player("t_snap_player")
        self.player.location = self.room
        self.player.traits.hp.base = 60
        self.player.traits.hp.current = 60
        self.actor = _monster("t_snap_monster")
        self.actor.location = self.room
        self.actor.db.skills = {"active": [SEALED_STRIKE.key], "passive": []}
        self.actor.traits.mp.base = 40
        self.actor.traits.mp.current = 40
        self.target = self.player
        engage(self.player, self.actor)

    def _context(self):
        battlefield = reconstruct_battlefield(
            self.player, read_session(self.player)
        )
        return BattlefieldActionContext(battlefield)

    def _stored_traits(self, entity):
        return dict(entity.attributes.get("traits", default={}, category="traits"))

    def _stored_hp(self, entity) -> int:
        return int(self._stored_traits(entity)["hp"]["current"])

    def _decision(self, *, participants=None, reads=None):
        """One decision's snapshot, reads, roster and resolved context."""
        reader = DecisionReads() if reads is None else reads
        context = self._context()
        pool = tuple(
            (self.target,) if participants is None else participants
        )
        snapshot = build_decision_snapshot(
            self.actor,
            context,
            scope=DecisionScope(SCOPE, ROUND, 0),
            participants=pool,
            reads=reader,
        )
        return snapshot, reader, roster_index((self.actor, *pool)), context

    def test_the_snapshot_writes_nothing_and_attaches_no_handler(self):
        # The spec's own premise: an entity whose handlers were never
        # materialized. A persisted ``sexual_traits`` record only exists once
        # the sexual handler ran, so removing it (and any mounted handler)
        # models exactly that state.
        context = self._context()
        for entity in (self.actor, self.target):
            entity.attributes.remove("sexual_traits", category="traits")
            for handler in ("traits", "buffs", "sexual", "equipment"):
                entity.__dict__.pop(handler, None)
        before = {
            "attributes": {
                str(row.key): row.value for row in self.actor.attributes.all()
            },
            "target_attributes": {
                str(row.key): row.value for row in self.target.attributes.all()
            },
            "rows": ObjectDB.objects.count(),
        }
        reads = DecisionReads()
        snapshot = build_decision_snapshot(
            self.actor,
            context,
            scope=DecisionScope(SCOPE, ROUND, 0),
            participants=(self.target,),
            reads=reads,
        )
        roster = roster_index((self.actor, self.target))
        for entity in (self.actor, self.target):
            for handler in ("traits", "buffs", "sexual", "equipment"):
                self.assertNotIn(
                    handler,
                    entity.__dict__,
                    "building a snapshot must not attach a lazy handler",
                )
        verdict = validate_plan(
            snapshot,
            PlannedAction(SEALED_STRIKE.key, target_ids=(stable_identity(self.target),)),
            actor=self.actor,
            context=context,
            roster=roster,
            reads=reads,
        )
        self.assertFalse(verdict.legal)
        self.assertIs(verdict.reason, RejectReason.CAST_CONDITION_UNMET)
        self.assertEqual(
            {str(row.key): row.value for row in self.actor.attributes.all()},
            before["attributes"],
        )
        self.assertEqual(
            {str(row.key): row.value for row in self.target.attributes.all()},
            before["target_attributes"],
        )
        self.assertEqual(ObjectDB.objects.count(), before["rows"])
        for entity in (self.actor, self.target):
            for handler in ("traits", "buffs", "sexual", "equipment"):
                self.assertNotIn(handler, entity.__dict__)

    def test_a_materialized_entity_gains_no_persistent_state(self):
        # A decision about an entity that already carries persisted sexual
        # traits may re-mount the handler the ownership authority reads its
        # live unlocked-act counters through; that re-attach derives nothing
        # new. What must never change is persistent state.
        for entity in (self.actor, self.target):
            for handler in ("buffs", "equipment"):
                entity.__dict__.pop(handler, None)
        before = {
            "attributes": {
                str(row.key): row.value for row in self.actor.attributes.all()
            },
            "stored_hp": self._stored_hp(self.target),
            "rows": ObjectDB.objects.count(),
        }
        snapshot, reads, roster, context = self._decision()
        validate_plan(
            snapshot,
            PlannedAction(SEALED_STRIKE.key, target_ids=(stable_identity(self.target),)),
            actor=self.actor,
            context=context,
            roster=roster,
            reads=reads,
        )
        self.assertEqual(
            {str(row.key): row.value for row in self.actor.attributes.all()},
            before["attributes"],
        )
        self.assertEqual(self._stored_hp(self.target), before["stored_hp"])
        self.assertEqual(ObjectDB.objects.count(), before["rows"])
        for entity in (self.actor, self.target):
            for handler in ("buffs", "equipment"):
                self.assertNotIn(handler, entity.__dict__)

    def test_a_stale_gauge_timestamp_is_never_regenerated(self):
        records = self._stored_traits(self.actor)
        records["hp"] = {
            **records["hp"],
            "current": records["hp"]["base"] - 7,
            "last_update": "2001-01-01T00:00:00",
        }
        self.actor.attributes.add("traits", records, category="traits")
        self.actor.__dict__.pop("traits", None)
        snapshot, _reads, _roster, _context = self._decision()
        after = self._stored_traits(self.actor)["hp"]
        self.assertEqual(after["last_update"], "2001-01-01T00:00:00")
        self.assertEqual(after["current"], records["hp"]["current"])
        self.assertEqual(snapshot.actor.resources["hp"][0], records["hp"]["current"])
        self.assertNotIn("traits", self.actor.__dict__)

    def test_a_persisted_buff_projects_without_mounting_the_handler(self):
        self.target.attributes.add("buffs", {WARD: _buff_record(WARD)})
        self.target.__dict__.pop("buffs", None)
        snapshot, _reads, _roster, _context = self._decision()
        projected = snapshot.participants[0].buffs
        self.assertEqual([buff.key for buff in projected], [WARD])
        self.assertEqual(projected[0].stacks, 1)
        self.assertNotIn("buffs", self.target.__dict__)

    def test_the_projection_agrees_with_the_settled_buff_reader(self):
        key = next(iter(BUFF_DEFINITIONS))
        apply_buff(self.target, key)
        snapshot, _reads, _roster, _context = self._decision()
        from_storage = active_buff_keys_from_storage(self.target)
        self.assertEqual(from_storage, entity_active_buffs(self.target))
        self.assertEqual(
            {buff.key for buff in snapshot.participants[0].buffs}, from_storage
        )

    def test_two_participants_sharing_a_display_key_keep_distinct_identities(self):
        twin = _monster(self.actor.key, hp=25)
        twin.location = self.room
        snapshot, _reads, _roster, _context = self._decision(participants=(self.target, twin))
        identities = [item.identity for item in snapshot.participants]
        self.assertEqual(len(set(identities)), 2)
        self.assertEqual(
            {item.resources["hp"][0] for item in snapshot.participants}, {60, 25}
        )

    def test_preview_submission_and_preflight_reject_the_same_cast(self):
        context = self._context()
        preview = preview_skill(
            self.actor, SEALED_STRIKE.key, context, [self.target]
        )
        submission = revalidate_submission(
            self.actor, SEALED_STRIKE.key, context, [self.target]
        )
        preflight = ActionResolver.preflight(
            ActionRequest(self.actor, SEALED_STRIKE.key, [self.target], context)
        )
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.CAST_CONDITION_UNMET)
        self.assertFalse(submission.enabled)
        self.assertIs(submission.reason, RejectReason.CAST_CONDITION_UNMET)
        self.assertEqual(preflight.outcome, "rejected")
        self.assertIs(preflight.reason, RejectReason.CAST_CONDITION_UNMET)
        self.target.attributes.add("buffs", {SEAL: _buff_record(SEAL)})
        accepted = preview_skill(
            self.actor, SEALED_STRIKE.key, context, [self.target]
        )
        self.assertTrue(accepted.enabled, accepted.detail)
        self.assertEqual(
            ActionResolver.preflight(
                ActionRequest(
                    self.actor, SEALED_STRIKE.key, [self.target], context
                )
            ).outcome,
            "success",
        )

    def test_a_contact_prerequisite_rejects_the_self_cast_for_every_surface(self):
        self.actor.db.skills = {
            "active": [CONTACT_SELF.key],
            "passive": [],
        }
        context = self._context()
        preview = preview_skill(self.actor, CONTACT_SELF.key, context, [])
        submission = revalidate_submission(
            self.actor, CONTACT_SELF.key, context, []
        )
        preflight = ActionResolver.preflight(
            ActionRequest(self.actor, CONTACT_SELF.key, [], context)
        )
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.CAST_CONDITION_UNMET)
        self.assertIs(submission.reason, RejectReason.CAST_CONDITION_UNMET)
        self.assertIs(preflight.reason, RejectReason.CAST_CONDITION_UNMET)

    def test_a_stale_plan_is_refused_by_the_resolver_without_payment(self):
        self.target.attributes.add("buffs", {SEAL: _buff_record(SEAL)})
        snapshot, reads, roster, context = self._decision()
        verdict = validate_plan(
            snapshot,
            PlannedAction(SEALED_STRIKE.key, target_ids=(stable_identity(self.target),)),
            actor=self.actor,
            context=context,
            roster=roster,
            reads=reads,
        )
        self.assertTrue(verdict.legal, verdict.detail)
        self.target.traits.hp.base = 0
        self.target.traits.hp.current = 0
        before = self._stored_traits(self.actor)["mp"]["current"]
        result = ActionResolver.resolve(
            ActionRequest(self.actor, SEALED_STRIKE.key, [self.target], context)
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.TARGET_DEAD)
        self.assertEqual(self._stored_traits(self.actor)["mp"]["current"], before)
        self.assertIs(
            revalidate_submission(
                self.actor, SEALED_STRIKE.key, context, [self.target]
            ).reason,
            RejectReason.TARGET_DEAD,
        )

    def test_a_legal_plan_settles_through_the_resolver(self):
        self.actor.db.skills = {"active": [STRIKE.key], "passive": []}
        plan = PlannedAction(STRIKE.key, target_ids=(stable_identity(self.target),))
        snapshot, reads, roster, context = self._decision()
        verdict = validate_plan(
            snapshot, plan, actor=self.actor, context=context, roster=roster, reads=reads
        )
        self.assertTrue(verdict.legal, verdict.detail)
        before = self._stored_traits(self.actor)["mp"]["current"]
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                ActionRequest(self.actor, STRIKE.key, [self.target], context)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self._stored_traits(self.actor)["mp"]["current"], before - 8
        )
        self.assertLess(self._stored_hp(self.target), 60)
