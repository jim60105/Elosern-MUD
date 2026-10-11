"""Atomic escort acceptance and exact-source release through quest owners."""

from contextlib import contextmanager
from copy import deepcopy
from typing import Any

from django.db import transaction
from evennia.objects.models import ObjectDB

from world.observability import log_info, log_warn
from world.rules.party import (
    add_temporary_source, party_ids, release_record_reasons,
    restore_membership_surfaces,
)
from world.rules.possession import restore_party_control, snapshot_party_control
from world.rules.surfaces import restore_attributes, snapshot_attributes

from . import scene_store
from .definitions import ObjectiveKind, QUEST_DEFINITION_REGISTRY
from .escort import authoritative_position, is_living
from .outcome_store import allocate_acceptance_sequence, read_group
from .runtime import (
    QuestAlreadyActive, QuestNotFound, QuestRecord, QuestState, QuestTransitionError,
    _current_tick, read_records,
)
from .transitions import apply_quest_log_replacement


class EscortOperationError(QuestTransitionError):
    """A deterministic refusal with a stable machine-readable reason."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@contextmanager
def escort_transaction(owner: Any, actors: tuple[Any, ...]):
    """Enlist durable writes and compensate live control on an outer failure."""
    roster = party_ids(owner)
    metadata = deepcopy(owner.db.party_meta)
    members = {actor.pk: actor.db.party_member for actor in actors}
    controls = [(actor, snapshot_party_control(owner, actor)) for actor in actors]
    attrs = snapshot_attributes(owner, (
        "quest_log", "wallet", "inventory", "guild_reward_claims", "dialogue_session",
    ))
    try:
        with transaction.atomic():
            list(ObjectDB.objects.select_for_update().filter(
                id__in=sorted({owner.pk, *members})
            ))
            yield
    except Exception:
        restore_attributes(owner, attrs)
        restore_membership_surfaces(owner, roster, members, metadata)
        for actor, control in controls:
            restore_party_control(owner, actor, control)
        raise


def _offer_context(owner, definition_key, issuer_key, actual_actor, expected_revision):
    from world.rules.quest_issuance import resolve_issuance, resolve_issuer_key
    from .encounters import lookup_story_role

    grants = [grant for grant in scene_store.list_commission_grants()
              if grant.definition_key == definition_key and grant.issuer_key == issuer_key
              and grant.registered and grant.npc_id > 0]
    if len(grants) != 1 or resolve_issuance(definition_key, issuer_key) is None:
        raise EscortOperationError("issuer_unauthorized")
    grant = grants[0]
    package = scene_store.read_package(grant.package.package_id)
    issuer = ObjectDB.objects.filter(pk=grant.npc_id).first()
    if package is None or package.status != scene_store.PACKAGE_STATUS_PUBLISHED:
        raise EscortOperationError("offer_stale")
    if issuer is None or resolve_issuer_key(issuer) != issuer_key:
        raise EscortOperationError("issuer_unauthorized")
    if authoritative_position(actual_actor) is None or (
        authoritative_position(issuer) != authoritative_position(actual_actor)
    ):
        raise EscortOperationError("role_not_co_located")
    phase = scene_store.get_dialogue_phase(package.package_id, grant.role_id)
    if phase is None or (expected_revision is not None and phase.revision != expected_revision):
        raise EscortOperationError("offer_stale")
    dialogue = next((item for item in package.payload["dialogue"]
                     if item["role_id"] == grant.role_id), None)
    selected = next((item for item in (dialogue or {}).get("phases", [])
                     if item["phase_id"] == phase.selected_phase), None)
    if selected is None or not any(
        topic.get("effect_verb") == "offer_commission"
        and topic.get("effect_reference") == definition_key
        for topic in selected.get("topics", [])
    ):
        raise EscortOperationError("offer_stale")
    definition = QUEST_DEFINITION_REGISTRY[definition_key]
    protected_refs = tuple(dict.fromkeys(
        role for stage in definition.stages if stage.objective.kind is ObjectiveKind.ESCORT
        for role in stage.objective.protected_role_refs
    ))
    actors = []
    for role in protected_refs:
        lookup = lookup_story_role(package.package_id, role)
        actor = ObjectDB.objects.filter(pk=lookup.npc_id).first() if lookup.bound else None
        if lookup.availability != "bound" or actor is None or not is_living(actor):
            raise EscortOperationError("role_unavailable")
        if authoritative_position(actor) != authoritative_position(actual_actor):
            raise EscortOperationError("role_not_co_located")
        if actor.db.party_member is not None and actor.db.party_member != owner.pk:
            raise EscortOperationError("membership_owned_elsewhere")
        actors.append((role, actor))
    groups = [item for item in package.payload.get("outcome_groups", [])
              if definition_key in item["alternatives"]]
    if len(groups) > 1:
        raise EscortOperationError("offer_stale")
    group_id = groups[0]["group_id"] if groups else None
    group = read_group(owner_id=owner.pk, package_id=package.package_id, group_id=group_id) if group_id else None
    if group is not None and group.resolved:
        raise EscortOperationError("outcome_resolved")
    return package, group_id, tuple(actors)


def accept_escort_commission(
    owner: Any, definition_key: str, issuer_key: str, *,
    actual_actor: Any = None, expected_revision: int | None = None,
) -> QuestRecord:
    """Authorize the current physical offer and commit its exact protected sources."""
    from world.rules.clock import CLOCK_YAML

    definition = QUEST_DEFINITION_REGISTRY.get(definition_key)
    if definition is None:
        raise QuestNotFound(definition_key)
    actual_actor = owner if actual_actor is None else actual_actor
    if actual_actor is not owner:
        from world.rules.possession import current_possession
        control = current_possession(owner)
        if control is None or control["npc_dbid"] != actual_actor.pk or actual_actor.db.possessed_by != owner.pk:
            raise EscortOperationError("issuer_unauthorized")
    package, group_id, protected = _offer_context(
        owner, definition_key, issuer_key, actual_actor, expected_revision,
    )
    try:
        with escort_transaction(owner, tuple(actor for _, actor in protected)):
            # Revalidate after acquiring all deterministic entity locks.
            package, group_id, protected = _offer_context(
                owner, definition_key, issuer_key, actual_actor, expected_revision,
            )
            current = read_records(owner)
            if any(record.definition_key == definition_key and record.state is QuestState.IN_PROGRESS
                   for record in current):
                raise QuestAlreadyActive(definition_key)
            tick = _current_tick()
            sequence = allocate_acceptance_sequence(
                owner_id=owner.pk, package_id=package.package_id, group_id=group_id, tick=tick,
            ) if group_id else None
            number = sum(record.definition_key == definition_key for record in current) + 1
            record = QuestRecord(
                quest_id=f"{definition_key}:{number}", definition_key=definition_key,
                issuer_key=issuer_key, state=QuestState.IN_PROGRESS, stage_index=0,
                stage_progress=0, accepted_tick=tick,
                deadline_tick=None if definition.deadline_hours is None else (
                    tick + definition.deadline_hours * CLOCK_YAML["seconds_per_hour"]
                ), stage_room_id=None, objective_target_ids=(),
                protected_entity_ids=tuple(actor.pk for _, actor in protected),
                failure_reason=None, package_id=package.package_id, group_id=group_id,
                acceptance_sequence=sequence,
                protected_roles=tuple((role, actor.pk) for role, actor in protected),
            )
            apply_quest_log_replacement(owner, [*current, record])
            for role, actor in protected:
                add_temporary_source(actor, owner, record.quest_id, role)
            transaction.on_commit(lambda: log_info("escort_commission_accepted", context={
                "char": owner.pk, "quest": record.quest_id, "package": package.package_id,
                "group": group_id, "issuer": issuer_key, "sequence": sequence,
            }))
            return record
    except (EscortOperationError, QuestAlreadyActive):
        raise
    except Exception as error:
        log_warn("escort_acceptance_write_failed", exc=error, context={
            "char": owner.pk, "definition": definition_key, "issuer": issuer_key,
        })
        raise EscortOperationError("acceptance_write_failed") from error


def release_escort_bindings(owner: Any, record_id: str) -> QuestRecord:
    """Release exactly a terminal record's sources without deleting its actors."""
    record = next((item for item in read_records(owner) if item.quest_id == record_id), None)
    if record is None:
        raise QuestNotFound(record_id)
    if record.state is QuestState.IN_PROGRESS:
        raise EscortOperationError("transition_write_failed")
    from .escort import resolve_protected_actors

    with escort_transaction(owner, tuple(actor for _, actor in resolve_protected_actors(record))):
        release_record_reasons(owner, record_id)
    transaction.on_commit(lambda: log_info("escort_bindings_released", context={
        "char": owner.pk, "quest": record_id, "state": record.state.value,
        "package": record.package_id, "group": record.group_id,
    }))
    return record
