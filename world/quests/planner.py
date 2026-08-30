"""Automatic quest progress from committed action events (D-4).

The quest event-effect planner derives quest-log and instance-pin mutations from
the immutable ``EventLog`` of a successful action and returns them as action
``PendingEffect`` values, so ``ActionResolver`` commits them in the same
transaction as damage, resource cost, and progression. It never writes while
planning.
"""

from dataclasses import replace
from typing import Any

from typeclasses.characters import PlayerCharacter

from .definitions import ObjectiveKind
from .runtime import (
    QuestState,
    definition_for,
    fail_record,
    fulfill_record_for,
    read_records,
)
from .transitions import pending_effects_for_transition, release_stage_binding


def _defeated_targets(event_log: Any) -> tuple[tuple[int, str | None], ...]:
    """Return ``(target_id, monster_tier)`` from ``target_defeated`` entries.

    Simulated defeats (guild examinations) are excluded: the battle is a
    simulation, so a lethal crossing there grants no DEFEAT progress and
    cannot fail a protected entity (exam-simulated-battle-redesign D4).
    """
    defeated = []
    for entry in event_log.entries:
        if entry.kind != "target_defeated":
            continue
        if entry.data.get("simulated"):
            continue
        target_id = entry.data.get("target_id")
        tier = entry.data.get("monster_tier")
        if isinstance(target_id, int) and not isinstance(target_id, bool):
            defeated.append((target_id, tier if tier is None or isinstance(tier, str) else None))
    return tuple(defeated)


def _distinct_target_ids(defeated: tuple[tuple[int, str | None], ...]) -> tuple[int, ...]:
    return tuple(dict.fromkeys(target_id for target_id, _ in defeated))


def _matching_defeats(
    record: Any,
    objective: Any,
    defeated: tuple[tuple[int, str | None], ...],
) -> int:
    """Count distinct matching kills under this DEFEAT objective's selector."""
    seen: set[int] = set()
    matches = 0
    if objective.requires_bound_targets:
        bound = set(record.objective_target_ids)
        for target_id, _ in defeated:
            if target_id in bound and target_id not in seen:
                seen.add(target_id)
                matches += 1
    else:
        tier = objective.monster_tier
        for target_id, defeated_tier in defeated:
            if defeated_tier == tier and target_id not in seen:
                seen.add(target_id)
                matches += 1
    return matches


def _defeat_progress_changes(
    owner: Any,
    records: list[Any],
    defeated: tuple[tuple[int, str | None], ...],
) -> tuple[dict[str, Any], list[tuple[Any, tuple[str, ...], tuple[str, ...]]]]:
    """Compute per-quest DEFEAT advances for one quest owner."""
    replacements: dict[str, Any] = {}
    pin_operations: list[tuple[Any, tuple[str, ...], tuple[str, ...]]] = []
    for record in records:
        if record.state is not QuestState.IN_PROGRESS:
            continue
        definition = definition_for(record)
        objective = definition.stages[record.stage_index].objective
        if objective.kind is not ObjectiveKind.DEFEAT:
            continue
        matches = _matching_defeats(record, objective, defeated)
        if matches == 0:
            continue
        gained = min(matches, objective.quantity - record.stage_progress)
        new_progress = record.stage_progress + gained
        if new_progress >= objective.quantity:
            replacements[record.quest_id] = fulfill_record_for(
                owner, record, definition
            )
            pin_operations.extend(release_stage_binding(owner, record))
        else:
            replacements[record.quest_id] = replace(record, stage_progress=new_progress)
    return replacements, pin_operations


def _protected_failure_changes(
    owner: Any,
    records: list[Any],
    defeated_ids: tuple[int, ...],
) -> tuple[dict[str, Any], list[tuple[Any, tuple[str, ...], tuple[str, ...]]]]:
    """Compute exact protected-entity failures for one player's active quests."""
    if not defeated_ids:
        return {}, []
    defeated_set = set(defeated_ids)
    replacements: dict[str, Any] = {}
    pin_operations: list[tuple[Any, tuple[str, ...], tuple[str, ...]]] = []
    for record in records:
        if record.state is not QuestState.IN_PROGRESS:
            continue
        if not (set(record.protected_entity_ids) & defeated_set):
            continue
        replacements[record.quest_id] = fail_record(record, "protected_entity_defeated")
        pin_operations.extend(release_stage_binding(owner, record))
    return replacements, pin_operations


def _compute_owner_changes(
    defeat_credit: bool,
    owner: Any,
    records: list[Any],
    defeated: tuple[tuple[int, str | None], ...],
    defeated_ids: tuple[int, ...],
) -> tuple[list[Any], list[tuple[Any, tuple[str, ...], tuple[str, ...]]]] | None:
    replacements: dict[str, Any] = {}
    pin_operations: list[tuple[Any, tuple[str, ...], tuple[str, ...]]] = []
    if defeat_credit:
        defeat_changes, defeat_pins = _defeat_progress_changes(owner, records, defeated)
        replacements.update(defeat_changes)
        pin_operations.extend(defeat_pins)
    failure_changes, failure_pins = _protected_failure_changes(owner, records, defeated_ids)
    replacements.update(failure_changes)
    pin_operations.extend(failure_pins)
    if not replacements:
        return None
    # Protected-entity defeat failure takes precedence over DEFEAT progress when
    # one event both advances and kills a bound identity: the failed record
    # replaces the advanced one. Duplicate pin releases are idempotent removals.
    new_records = [
        replacements.get(record.quest_id, record)
        for record in records
    ]
    return new_records, pin_operations


def _bound_defeat_owner(actor: Any, battlefield: Any) -> Any | None:
    """Resolve the player whose active quests a companion actor's kills credit.

    The credit decision fails closed: the actor must be a bound companion of
    the candidate owner (validated bidirectionally through the party module's
    safe resolver), an active battlefield must be present in the request
    context, and the actor must not be knocked out on it (party-quest D-1).
    """
    from world.rules.party import bound_owner_of

    owner = bound_owner_of(actor)
    if owner is None:
        return None
    # The shared knockout predicate is read duck-typed so a battlefield-shaped
    # context without the predicate still fails closed instead of raising.
    predicate = getattr(battlefield, "is_knocked_out", None)
    if predicate is None or predicate(str(actor.key)):
        return None
    return owner


def quest_event_effect_planner(request: Any, event_log: Any) -> list[Any]:
    """Derive quest-log and instance-pin pending effects from one successful action.

    DEFEAT progress advances the acting ``PlayerCharacter``'s active quests
    and, additionally, the quest owner's active quests when the actor is that
    owner's bound companion (bidirectional binding and not knocked out, both
    failing closed). Exact protected-entity defeat failure scans every player
    character because a hostile actor can kill a bound escort (D-4).
    """
    defeated = _defeated_targets(event_log)
    if not defeated:
        return []
    defeated_ids = _distinct_target_ids(defeated)

    actor = request.actor
    companion_owner = _bound_defeat_owner(
        actor, getattr(request.context, "battlefield", None)
    )
    owners: dict[int, Any] = {}
    if isinstance(actor, PlayerCharacter):
        owners[actor.pk] = actor
    if companion_owner is not None:
        owners.setdefault(companion_owner.pk, companion_owner)
    for player in PlayerCharacter.objects.all_family():
        if player.db.quest_log:
            owners.setdefault(player.pk, player)

    effects: list[Any] = []
    for owner in owners.values():
        records = read_records(owner)
        changes = _compute_owner_changes(
            defeat_credit=(
                (isinstance(actor, PlayerCharacter) and owner.pk == actor.pk)
                or (companion_owner is not None and owner.pk == companion_owner.pk)
            ),
            owner=owner,
            records=records,
            defeated=defeated,
            defeated_ids=defeated_ids,
        )
        if changes is None:
            continue
        new_records, pin_operations = changes
        effects.extend(
            pending_effects_for_transition(owner, new_records, pin_operations)
        )
    return effects