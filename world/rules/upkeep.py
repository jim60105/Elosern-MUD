"""Upkeep tick settlement: attributed rate ticks become round events.

One deterministic boundary (fix-dot-kill-credit D3) turns the damaging tick
records ``tick_buffs`` returns into ``damage``/``target_defeated`` EventLog
entries, nonlethal floors and knockout marks, and quest
planner effects -- all staged as ``PendingEffect`` values committed through
``_commit`` inside the session's combat-round transaction. The HP damage of
each tick was already applied by ``tick_buffs`` itself; this module never
re-applies it.
"""

from types import SimpleNamespace
from typing import Any

from world.rules.action import (
    PendingEffect,
    _ENTRY_TEMPLATES,
    _EVENT_EFFECT_PLANNERS,
    _commit,
    _defeated_entry,
    _stored_trait_value,
)
from world.rules.buffs import TickRecord
from world.rules.event_log import EventEntry, EventLog

UPKEEP_SKILL_KEY = "combat_upkeep"


def _resolve_source(battlefield: Any, source_pk: int | None) -> Any | None:
    """Resolve a tick's cached source dbref to a live entity, or ``None``.

    The roster is consulted first (in-battle identity, which also survives
    the session), then the object database for entities outside the fight
    (deleted or absent entities resolve to ``None``).
    """
    if source_pk is None:
        return None
    for entity in battlefield.roster.values():
        pk = getattr(entity, "pk", None)
        if isinstance(pk, int) and pk == source_pk:
            return entity
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(id=source_pk).first()


def _floor_hp(entity: Any) -> None:
    """Floor a protected target's HP to 1 inside the settlement commit."""
    trait = entity.traits.hp
    if _stored_trait_value(trait) <= 0:
        if hasattr(trait, "current"):
            trait.current = 1
        else:
            trait.value = 1


def settle_upkeep(
    battlefield: Any,
    records_by_key: dict[str, tuple[TickRecord, ...]],
    *,
    simulated: bool = False,
    nonlethal_keys: frozenset[str] = frozenset(),
) -> list[EventLog]:
    """Settle the round's damaging tick records into events and staged effects.

    Processes records in application order, per roster key. For each
    attributed record it emits a ``damage`` entry reporting the actually
    applied amount (``min(-delta, hp_before)``) and, on a lethal crossing,
    exactly one ``target_defeated`` entry per target (dbref-deduplicated,
    same shape as the action pipeline's). Protected (``nonlethal_keys``)
    crossings floor HP at 1 and mark the target knocked out instead;
    simulated rounds tag defeat entries ``simulated`` and stage no credit.
    Unattributed ticks (absent or unresolvable ``source_pk``) cross HP
    silently with no entries or quest effects. Every staged mutation commits
    through one ``_commit`` call; a planner or commit failure aborts the
    round and the session restore rolls back every surface.
    """
    pending: list[PendingEffect] = []
    logs: list[EventLog] = []
    defeated_ids: set[int] = set()
    projected: dict[int, float] = {}
    per_source: dict[int, list[EventEntry]] = {}
    per_source_targets: dict[int, list[str]] = {}
    per_source_key: dict[int, str] = {}
    per_source_entity: dict[int, Any] = {}
    for key, records in records_by_key.items():
        entity = battlefield.roster.get(key)
        if entity is None:
            continue
        for record in records:
            source = _resolve_source(battlefield, record.source_pk)
            if source is None:
                continue
            # Group by the validated source dbref, never the display key:
            # Evennia keys are not unique, so same-named casters must keep
            # distinct logs, credit, and planner actors (fix-dot-kill-credit
            # D1; the quest planner already keys on dbrefs).
            source_pk = int(source.pk)
            per_source_entity.setdefault(source_pk, source)
            per_source_key.setdefault(source_pk, str(source.key))
            applied = min(-record.delta, record.hp_before)
            damage_entry = EventEntry(
                kind="damage",
                actor=per_source_key[source_pk],
                target=key,
                data={"amount": int(applied)},
                text_template=_ENTRY_TEMPLATES["damage"],
            )
            per_source.setdefault(source_pk, []).append(damage_entry)
            if key not in per_source_targets.setdefault(source_pk, []):
                per_source_targets[source_pk].append(key)
            protected = key in nonlethal_keys
            if applied <= 0:
                continue
            projected[id(entity)] = record.hp_before
            defeated = _defeated_entry(
                per_source_key[source_pk],
                entity,
                int(applied),
                projected,
                defeated_ids,
                nonlethal=protected,
                simulated=simulated,
            )
            if defeated is not None:
                per_source[source_pk].append(defeated)
            if defeated is not None and protected:
                # The tick already crossed HP; floor it back and mark the
                # battlefield knockout in the same commit (mirrors the
                # action pipeline's nonlethal crossing). A non-crossing
                # tick on a protected target changes nothing.
                pending.append(
                    PendingEffect(
                        entity=entity,
                        description=f"upkeep_hp_floor|{key}",
                        surfaces=frozenset({"traits"}),
                        apply=lambda entity=entity: _floor_hp(entity),
                    )
                )
                pending.append(
                    PendingEffect(
                        entity=battlefield,
                        description=f"knocked_out_mark|{key}",
                        surfaces=frozenset(),
                        apply=lambda battlefield=battlefield, key=key: (
                            battlefield.knocked_out.update({key})
                        ),
                    )
                )
                continue
    for source_pk, entries in per_source.items():
        if not entries:
            continue
        log = EventLog(
            actor=per_source_key[source_pk],
            skill_key=UPKEEP_SKILL_KEY,
            targets=tuple(per_source_targets[source_pk]),
            entries=tuple(entries),
            time_cost_seconds=0,
        )
        logs.append(log)
        if not any(entry.kind == "target_defeated" for entry in entries):
            continue
        request = SimpleNamespace(
            actor=per_source_entity[source_pk],
            context=SimpleNamespace(battlefield=battlefield),
        )
        for planner in _EVENT_EFFECT_PLANNERS.values():
            for effect in planner(request, log):
                if not isinstance(effect, PendingEffect):
                    raise TypeError(
                        "event-effect planner returned a non-PendingEffect value"
                    )
                pending.append(effect)
    if pending:
        _commit(pending)
    return logs
