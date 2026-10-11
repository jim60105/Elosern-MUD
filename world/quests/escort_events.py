"""Settled escort observations and winner-before-payment arbitration.

An observation is issued by the originating deterministic transaction, not by
parsing a caller's strings, tick or prose. Role reverse references live in the
existing scene store and group store, so reload needs no global player scan.
"""

from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from typing import Any
from uuid import uuid4

from django.db import transaction
from evennia.objects.models import ObjectDB

from world.observability import log_info
from world.rules.party import bound_owner_of

from . import outcome_store, scene_store
from .definitions import EscortCompletion, ObjectiveKind, QUEST_DEFINITION_REGISTRY, QuestStage
from .escort import authoritative_position, destination_satisfied, rendezvous_satisfied, resolve_protected_actors
from .escort_lifecycle import EscortOperationError, escort_compensation
from .runtime import (
    QuestState, definition_for, fulfill_record_for, invalidate_record, read_records,
)
from .transitions import apply_quest_log_replacement, release_stage_binding


@dataclass(eq=False)
class EscortSource:
    """Owner-issued transaction receipt; only the current receipt is executable."""

    key: str = field(default_factory=lambda: f"escort:{uuid4().hex}")
    actor_ids: set[int] = field(default_factory=set)
    records: dict[tuple[int, str], tuple[Any, ...]] = field(default_factory=dict)
    scopes: dict[tuple[int, str], Any] = field(default_factory=dict)
    stack: ExitStack = field(default_factory=ExitStack)


_CURRENT_SOURCE: ContextVar[EscortSource | None] = ContextVar("escort_source", default=None)


def _actors(package_id: str, roles: tuple[str, ...]) -> tuple[Any, ...]:
    result = []
    for role in roles:
        binding = scene_store.get_role_binding(package_id, role)
        if binding is None or binding.availability != scene_store.AVAILABILITY_BOUND:
            return ()
        actor = ObjectDB.objects.filter(pk=binding.npc_id).first()
        if actor is None:
            return ()
        result.append(actor)
    return tuple(result)


def enlist_escort_scope(owner: Any, package_id: str) -> None:
    """Snapshot a newly encountered scope before its first transactional write."""
    source = _CURRENT_SOURCE.get()
    if source is None:
        raise EscortOperationError("invalid_source")
    identity = (owner.pk, package_id)
    if identity in source.scopes:
        return
    records = tuple(read_records(owner))
    actors = tuple({entity.pk: entity for record in records
                    for _, entity in resolve_protected_actors(record)}.values())
    source.stack.enter_context(escort_compensation(owner, actors))
    source.scopes[identity] = owner
    source.records[identity] = records


def collect_escort_actors(actors: tuple[Any, ...], *, affected: bool = True) -> None:
    """Collect actual moved/bound actors without consuming stage eligibility."""
    source = _CURRENT_SOURCE.get()
    if source is None:
        return
    actor_ids = tuple(actor.pk for actor in actors if actor is not None and actor.pk)
    if affected:
        source.actor_ids.update(actor_ids)
    packages = scene_store.packages_for_actors(actor_ids)
    owners = {owner.pk: owner for actor in actors if (owner := bound_owner_of(actor)) is not None}
    for package_id in packages:
        owner_ids = set(scene_store.encounter_player_ids(package_id))
        owner_ids.update(outcome_store.package_owner_ids(package_id))
        owner_ids.update(owners)
        for owner_id in sorted(owner_ids):
            owner = owners.get(owner_id) or ObjectDB.objects.filter(pk=owner_id).first()
            if owner is not None:
                enlist_escort_scope(owner, package_id)


@contextmanager
def escort_event_boundary(actors: tuple[Any, ...] = ()):
    """Share one receipt through movement/activation/follow, then settle once."""
    current = _CURRENT_SOURCE.get()
    if current is not None:
        collect_escort_actors(actors, affected=False)
        yield current
        return
    source = EscortSource()
    origins = {actor.pk: authoritative_position(actor) for actor in actors}
    token = _CURRENT_SOURCE.set(source)
    try:
        with source.stack:
            with transaction.atomic():
                collect_escort_actors(actors, affected=False)
                yield source
                collect_escort_actors(tuple(
                    actor for actor in actors
                    if authoritative_position(actor) != origins[actor.pk]
                ))
                for (owner_id, package_id), owner in tuple(source.scopes.items()):
                    evaluate_escort_event(owner, package_id, source=source)
    finally:
        _CURRENT_SOURCE.reset(token)


def _require_source(source: EscortSource) -> None:
    if not isinstance(source, EscortSource) or _CURRENT_SOURCE.get() is not source:
        raise EscortOperationError("invalid_source")


def _satisfied(record, definition, package_id):
    objective = definition.stages[record.stage_index].objective
    if objective.kind is not ObjectiveKind.ESCORT:
        return False
    if objective.completion is EscortCompletion.DESTINATION:
        protected = resolve_protected_actors(record)
        return bool(protected) and destination_satisfied(record, definition, protected[0][1].location)
    return rendezvous_satisfied(record, definition, _actors(package_id, objective.meeting_role_refs))


def _attributable(record, definition, package_id, source):
    objective = definition.stages[record.stage_index].objective
    participants = {actor_id for _, actor_id in record.protected_roles}
    participants.update(actor.pk for actor in _actors(package_id, objective.meeting_role_refs))
    return bool(participants & source.actor_ids)


def _group_definition(package_id, group_id):
    from .scene_package import _validate_outcome_groups

    package = scene_store.read_package(package_id)
    if package is None or package.status != scene_store.PACKAGE_STATUS_PUBLISHED:
        raise EscortOperationError("unknown_group")
    entries = package.payload.get("outcome_groups", [])
    entry = next((item for item in entries if item["group_id"] == group_id), None)
    if entry is None:
        raise EscortOperationError("unknown_group")
    definition = QUEST_DEFINITION_REGISTRY.get(entry["alternatives"][0])
    if definition is None:
        raise EscortOperationError("unknown_group")
    roles = {item["role_id"] for item in package.payload["roles"]}
    return _validate_outcome_groups([entry], roles, definition)[0], definition


def exclusive_outcome_status(owner: Any, package_id: str, group_id: str):
    """Read resolution without creating a group, record, entitlement or memory."""
    _group_definition(package_id, group_id)
    return outcome_store.read_group(owner_id=owner.pk, package_id=package_id, group_id=group_id)


def reward_entitled(owner: Any, record: Any) -> bool:
    """Both payment modes consult the chosen winner before planning any effect."""
    if record.group_id is None:
        return True
    group = outcome_store.read_group(
        owner_id=owner.pk, package_id=record.package_id, group_id=record.group_id,
    )
    return bool(group and group.resolved and not group.no_commission
                and group.winner_quest_id == record.quest_id)


def resolve_exclusive_outcome(owner: Any, package_id: str, group_id: str, *, source: EscortSource):
    """Arbitrate terminally eligible attributable records, never a thread heuristic."""
    _require_source(source)
    group_definition, definition = _group_definition(package_id, group_id)
    row = outcome_store.get_or_create_group(
        owner_id=owner.pk, package_id=package_id, group_id=group_id,
    )
    if row.resolved:
        return row
    before = source.records.get((owner.pk, package_id), ())
    active = [record for record in before if record.state is QuestState.IN_PROGRESS
              and record.package_id == package_id and record.group_id == group_id
              and record.definition_key in group_definition.alternative_definition_keys]
    current = {record.quest_id: record for record in read_records(owner)}
    eligible = []
    for record in active:
        own_definition = definition_for(record)
        if (record.stage_index == len(own_definition.stages) - 1
                and current.get(record.quest_id) == record
                and not outcome_store.transition_consumed(
                    owner_id=owner.pk, record_id=record.quest_id, source_key=source.key,
                ) and _attributable(record, own_definition, package_id, source)
                and _satisfied(record, own_definition, package_id)):
            eligible.append(record)
    if active and not eligible:
        return None
    # A satisfying commission alone cannot invent the group's concrete result.
    result = group_definition.result
    protected = _actors(package_id, result.protected_role_refs)
    meeting = _actors(package_id, result.meeting_role_refs)
    if len(protected) != len(result.protected_role_refs):
        return None
    prototype = definition.stages[-1].objective
    objective = replace(prototype, completion=result.completion,
                        protected_role_refs=result.protected_role_refs,
                        meeting_role_refs=result.meeting_role_refs, relation=result.relation)
    physical_definition = replace(definition, stages=(QuestStage(0, objective),))
    from types import SimpleNamespace
    physical_record = SimpleNamespace(
        stage_index=0, stage_room_id=None,
        protected_roles=tuple((role, actor.pk) for role, actor in zip(result.protected_role_refs, protected)),
    )
    if not (set(actor.pk for actor in (*protected, *meeting)) & source.actor_ids):
        return None
    if not _satisfied(physical_record, physical_definition, package_id):
        return None
    winner = min(eligible, key=lambda record: (record.acceptance_sequence, record.quest_id)) if eligible else None
    row = outcome_store.mark_group_resolved(
        owner_id=owner.pk, package_id=package_id, group_id=group_id,
        resolution_source=source.key, winner_quest_id=winner.quest_id if winner else "",
        no_commission=winner is None,
    )
    replacements = {}
    pins = []
    for record in active:
        # An active alternative may already have consumed this source when it
        # advanced an intermediate stage earlier in the same settled pass; the
        # final arbitration must treat that as already-observed rather than a
        # forged source, and still invalidate the record as a losing
        # alternative (escort-rendezvous §7).
        if not outcome_store.transition_consumed(
            owner_id=owner.pk, record_id=record.quest_id, source_key=source.key,
        ) and not outcome_store.consume_transition(
            owner_id=owner.pk, record_id=record.quest_id, source_key=source.key,
        ):
            raise EscortOperationError("invalid_source")
        replacements[record.quest_id] = (
            fulfill_record_for(owner, record, definition_for(record))
            if winner is not None and record.quest_id == winner.quest_id else invalidate_record(record)
        )
        if record.quest_id != winner.quest_id:
            transaction.on_commit(
                lambda record=record: log_info(
                    "escort_quest_invalidated",
                    context={
                        "char": owner.pk,
                        "quest": record.quest_id,
                        "package": package_id,
                        "group": group_id,
                        "source": source.key,
                    },
                )
            )
        pins.extend(release_stage_binding(owner, record))
    if replacements:
        apply_quest_log_replacement(owner, [replacements.get(record.quest_id, record)
                                          for record in current.values()], pins)
    return row


def evaluate_escort_event(owner: Any, package_id: str, *, source: EscortSource) -> str:
    """Evaluate final settled facts once for each pre-event eligible record."""
    _require_source(source)
    before = source.records.get((owner.pk, package_id))
    if before is None:
        raise EscortOperationError("invalid_source")
    current = {record.quest_id: record for record in read_records(owner)}
    replacements = {}
    pins = []
    observed = False
    for record in before:
        if record.state is not QuestState.IN_PROGRESS or record.package_id != package_id:
            continue
        if outcome_store.transition_consumed(owner_id=owner.pk, record_id=record.quest_id, source_key=source.key):
            observed = True
            continue
        definition = definition_for(record)
        if current.get(record.quest_id) != record or not _attributable(record, definition, package_id, source):
            continue
        if not _satisfied(record, definition, package_id):
            continue
        if record.group_id is not None and record.stage_index == len(definition.stages) - 1:
            continue
        if not outcome_store.consume_transition(owner_id=owner.pk, record_id=record.quest_id, source_key=source.key):
            continue
        replacements[record.quest_id] = fulfill_record_for(owner, record, definition)
        pins.extend(release_stage_binding(owner, record))
    if replacements:
        apply_quest_log_replacement(owner, [replacements.get(record.quest_id, record)
                                          for record in current.values()], pins)
    package = scene_store.read_package(package_id)
    resolved = False
    for group in package.payload.get("outcome_groups", []):
        result = resolve_exclusive_outcome(owner, package_id, group["group_id"], source=source)
        resolved = resolved or bool(result and result.resolved)
    outcome = "resolved" if resolved else "stage_advanced" if replacements else "already_observed" if observed else "unsatisfied"
    transaction.on_commit(lambda: log_info("escort_event_evaluated", context={
        "char": owner.pk, "package": package_id, "source": source.key,
        "outcome": outcome, "actors": sorted(source.actor_ids),
    }))
    return outcome
