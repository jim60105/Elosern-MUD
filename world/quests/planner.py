"""Automatic quest progress from committed action events (D-4).

The quest event-effect planner derives quest-log and instance-pin mutations from
the immutable ``EventLog`` of a successful action and returns them as action
``PendingEffect`` values, so ``ActionResolver`` commits them in the same
transaction as damage, resource cost, and progression. It never writes while
planning.

DEFEAT progress counts the defeated individual's persistent identity (its
database row), never a display key or a tier: each record keeps the identities
it has already credited for its current objective, so a duplicate or redelivered
``target_defeated`` entry can never advance the same objective twice.

A regional species-hunt objective matches on the entry's registered species and
variant keys plus the defeated individual's location resolved inside the
objective's declared region at defeat time; a tier-only individual carries no
species identity, so it can never satisfy a hunt.
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


def _defeat_identities(event_log: Any) -> dict[int, tuple[str | None, str | None]]:
    """Return ``target_id -> (species_key, variant_key)`` from defeat entries.

    A species-backed individual's identity rides its own committed defeat entry
    (the construction owner writes the pair onto the individual, and the defeat
    entry carries it verbatim). A tier-only individual's entry has neither key,
    which is exactly why it can never satisfy a species hunt. Display names,
    tiers, guild rank, and single stats are never identity.
    """
    identities: dict[int, tuple[str | None, str | None]] = {}
    for entry in event_log.entries:
        if entry.kind != "target_defeated":
            continue
        data = entry.data
        if data.get("simulated"):
            continue
        target_id = data.get("target_id")
        if not isinstance(target_id, int) or isinstance(target_id, bool):
            continue
        if target_id in identities:
            continue
        species_key = data.get("species_key")
        variant_key = data.get("variant_key")
        identities[target_id] = (
            species_key if isinstance(species_key, str) else None,
            variant_key if isinstance(variant_key, str) else None,
        )
    return identities


def _defeat_region(target_id: int, cache: dict[int, str | None]) -> str | None:
    """The wilderness region the defeated individual's location resolved to.

    Region scoping reads the individual's location at defeat time (design
    D-Q4): the entry carries the persistent dbref, and its row is still present
    inside the same commit, so the read stays deterministic. An individual with
    no location, or a location outside the wilderness, resolves to ``None`` and
    therefore never satisfies a hunt. The per-computation cache keeps the read
    bounded to one lookup per defeated identity.
    """
    if target_id in cache:
        return cache[target_id]
    from evennia.objects.models import ObjectDB

    from .room_observation import resolve_room_region

    entity = ObjectDB.objects.filter(id=target_id).first()
    region_key = (
        None
        if entity is None
        else resolve_room_region(getattr(entity, "location", None))
    )
    cache[target_id] = region_key
    return region_key


def _distinct_target_ids(defeated: tuple[tuple[int, str | None], ...]) -> tuple[int, ...]:
    return tuple(dict.fromkeys(target_id for target_id, _ in defeated))


def _matching_defeats(
    record: Any,
    objective: Any,
    defeated: tuple[tuple[int, str | None], ...],
    identities: dict[int, tuple[str | None, str | None]],
    region_cache: dict[int, str | None],
) -> tuple[int, ...]:
    """Return the identities this objective still has to credit, in event order.

    A bound objective matches the record's ``objective_target_ids``; an unbound
    tier objective matches its declared ``monster_tier``; a regional species
    hunt matches the entry's species key, a variant key among the objective's
    countable variants, and the defeated individual's location resolved inside
    the declared region. An identity the record already counted for its current
    objective is always skipped, so re-presenting an already-credited defeat
    entry grants nothing.
    """
    counted = set(record.counted_defeat_ids)
    seen: set[int] = set()
    matches: list[int] = []
    if objective.requires_bound_targets:
        bound = set(record.objective_target_ids)
        for target_id, _ in defeated:
            if target_id in bound and target_id not in seen and target_id not in counted:
                seen.add(target_id)
                matches.append(target_id)
    elif objective.region_key is not None:
        countable = frozenset(objective.countable_variant_keys)
        for target_id, _ in defeated:
            if target_id in seen or target_id in counted:
                continue
            identity = identities.get(target_id)
            if identity is None:
                continue
            species_key, variant_key = identity
            if species_key != objective.species_key or variant_key not in countable:
                continue
            if _defeat_region(target_id, region_cache) != objective.region_key:
                continue
            seen.add(target_id)
            matches.append(target_id)
    else:
        tier = objective.monster_tier
        for target_id, defeated_tier in defeated:
            if (
                defeated_tier == tier
                and target_id not in seen
                and target_id not in counted
            ):
                seen.add(target_id)
                matches.append(target_id)
    return tuple(matches)


def _defeat_progress_changes(
    owner: Any,
    records: list[Any],
    defeated: tuple[tuple[int, str | None], ...],
    identities: dict[int, tuple[str | None, str | None]],
) -> tuple[dict[str, Any], list[tuple[Any, tuple[str, ...], tuple[str, ...]]]]:
    """Compute per-quest DEFEAT advances for one quest owner."""
    replacements: dict[str, Any] = {}
    pin_operations: list[tuple[Any, tuple[str, ...], tuple[str, ...]]] = []
    # Region resolution is the one defeat-time read a hunt adds; it stays lazy
    # (inside ``_matching_defeats``) so a tier or bound objective performs no
    # extra lookup at all.
    region_cache: dict[int, str | None] = {}
    for record in records:
        if record.state is not QuestState.IN_PROGRESS:
            continue
        definition = definition_for(record)
        objective = definition.stages[record.stage_index].objective
        if objective.kind is not ObjectiveKind.DEFEAT:
            continue
        new_ids = _matching_defeats(record, objective, defeated, identities, region_cache)
        if not new_ids:
            # Every matching identity was already credited by this record: a
            # redelivered event plans no write at all.
            continue
        gained = min(len(new_ids), objective.quantity - record.stage_progress)
        new_progress = record.stage_progress + gained
        if new_progress >= objective.quantity:
            # Fulfilment clears the counted set with the other runtime bindings,
            # so surplus kills are discarded rather than applied to the next
            # stage (a new objective counts its own identities from empty).
            replacements[record.quest_id] = fulfill_record_for(
                owner, record, definition
            )
            pin_operations.extend(release_stage_binding(owner, record))
        else:
            replacements[record.quest_id] = replace(
                record,
                stage_progress=new_progress,
                counted_defeat_ids=record.counted_defeat_ids + new_ids,
            )
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
    identities: dict[int, tuple[str | None, str | None]],
    defeated_ids: tuple[int, ...],
) -> tuple[list[Any], list[tuple[Any, tuple[str, ...], tuple[str, ...]]]] | None:
    replacements: dict[str, Any] = {}
    pin_operations: list[tuple[Any, tuple[str, ...], tuple[str, ...]]] = []
    if defeat_credit:
        defeat_changes, defeat_pins = _defeat_progress_changes(
            owner, records, defeated, identities
        )
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


def _make_defeat_lore_apply(character: Any, tier: str) -> Any:
    from world.rules.lore_knowledge import schedule_lore_reveal_best_effort

    return lambda: schedule_lore_reveal_best_effort(character, "monster", tier)


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
    identities = _defeat_identities(event_log)

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
    crediting_player = (
        actor if isinstance(actor, PlayerCharacter) else companion_owner
    )
    if crediting_player is not None:
        from world.lore.monsters import MONSTER_TIER_REGISTRY
        from world.rules.action import PendingEffect

        registered_tiers = tuple(
            dict.fromkeys(
                tier
                for _, tier in defeated
                if isinstance(tier, str) and tier in MONSTER_TIER_REGISTRY
            )
        )
        for tier in registered_tiers:
            effects.append(
                PendingEffect(
                    entity=crediting_player,
                    description=f"lore codex reveal monster tier {tier}",
                    surfaces=frozenset(),
                    apply=_make_defeat_lore_apply(crediting_player, tier),
                )
            )
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
            identities=identities,
            defeated_ids=defeated_ids,
        )
        if changes is None:
            continue
        new_records, pin_operations = changes
        effects.extend(
            pending_effects_for_transition(owner, new_records, pin_operations)
        )
    return effects