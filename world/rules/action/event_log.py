"""Event-log construction for a resolved action (step 7).

Maps staged ``PendingEffect`` descriptions to replayable ``EventEntry``
values, derives defeat/knock-out crossings over projected HP, and assembles
the final ``EventLog``.
"""

from dataclasses import replace
from typing import Any

from world.rules.event_log import EventEntry, EventLog
from world.skills.registry import SkillDef
from world.skills.narration import (
    FALLBACK_TEMPLATES,
    INTERNAL_KINDS,
    action_line,
    act_for_skill,
    compose_first_line,
    entry_line,
    family_key,
)

from world.rules.action.contracts import (
    _entity_key,
    _event_context,
    ActionRequest,
    PendingEffect,
    RejectedAction,
    RejectReason,
)
from world.rules.action.gates import _stored_trait_value


#: Numberless fallbacks: the template every entry starts from before the
#: narration pass selects its authored line. Internal-only kinds stay empty.
_FALLBACK_TEMPLATES = FALLBACK_TEMPLATES


def _entries_from_effect(
    actor_key: str,
    effect: PendingEffect,
) -> tuple[EventEntry, ...]:
    parts = effect.description.split("|")
    if len(parts) < 2 or parts[0] not in _FALLBACK_TEMPLATES:
        raise ValueError(f"malformed pending-effect description {effect.description!r}")
    kind, target, *values = parts
    if kind == "resource_spend":
        data = {
            "resource_key": values[0],
            "amount": int(values[1]),
        }
    elif kind == "skill_granted":
        data = {
            "skill_key": values[0],
            "scale": float(values[1]),
        }
    elif kind == "buff_applied":
        data = {"buff_key": values[0]}
    elif kind == "self_buff_applied":
        data = {"buff_key": values[0]}
    elif kind == "equipment_immune":
        if len(values) != 1:
            raise ValueError(
                f"malformed equipment_immune pending effect {effect.description!r}"
            )
        data = {"buff_key": values[0]}
    elif kind == "buffs_cleansed":
        if len(values) != 1:
            raise ValueError(
                f"malformed buffs_cleansed pending effect {effect.description!r}"
            )
        data = {"count": int(values[0])}
    elif kind == "sexual_transition":
        data = {"event": values[0]}
    elif kind == "pleasure_gain":
        if len(values) != 1:
            raise ValueError(
                f"malformed pleasure_gain pending effect {effect.description!r}"
            )
        data = {"amount": int(values[0])}
    elif kind == "sexual_counter":
        if len(values) != 1:
            raise ValueError(
                f"malformed sexual_counter pending effect {effect.description!r}"
            )
        data = {"counter": values[0]}
    elif kind == "sexual_resist":
        if len(values) != 3:
            raise ValueError(
                f"malformed sexual_resist pending effect {effect.description!r}"
            )
        data = {
            "resisted": bool(int(values[0])),
            "auto_comply": bool(int(values[1])),
            "roll": None if values[2] == "none" else int(values[2]),
        }
    elif kind == "damage":
        if len(values) != 3:
            raise ValueError(
                f"malformed damage pending effect {effect.description!r}"
            )
        raw_roll, hit_flag, amount = map(int, values)
        roll_entry = EventEntry(
            kind="roll",
            actor=actor_key,
            target=target,
            data={"raw_roll": raw_roll, "hit": bool(hit_flag)},
            text_template=_FALLBACK_TEMPLATES["roll"],
        )
        if not hit_flag:
            return (roll_entry,)
        return (
            roll_entry,
            EventEntry(
                kind="damage",
                actor=actor_key,
                target=target,
                data={"amount": amount},
                text_template=_FALLBACK_TEMPLATES["damage"],
            ),
        )
    elif kind == "disengage_attempt":
        if len(values) != 4:
            raise ValueError(
                f"malformed disengage pending effect {effect.description!r}"
            )
        success_flag, raw_roll, actor_agility, pursuer_agility = values
        data = {
            "success": bool(int(success_flag)),
            "roll": None if raw_roll == "none" else int(raw_roll),
            "actor_agility": float(actor_agility),
            "pursuer_agility": (
                None
                if pursuer_agility == "none"
                else float(pursuer_agility)
            ),
        }
    elif kind in ("heal", "self_heal"):
        if len(values) != 1:
            raise ValueError(
                f"malformed heal pending effect {effect.description!r}"
            )
        data = {"amount": int(values[0])}
    elif kind == "combat_kill_xp":
        return ()
    elif kind == "knocked_out_mark":
        return ()
    elif kind == "divine_drain_actor":
        # Internal actor-side drain effect: the resource gain is rolled back
        # with the cast, and the logged narration is the single target-side
        # divine_drain entry — an actor entry would misnarrate as the caster
        # draining themselves.
        return ()
    elif kind == "gauge_transfer_actor":
        return ()
    elif kind == "damage_divert":
        return ()
    elif kind == "gauge_transfer":
        data = {
            "gauge": values[0] if len(values) > 0 else "mp",
            "direction": values[1] if len(values) > 1 else "drain",
            "amount": int(values[2]) if len(values) > 2 else 0,
        }
    else:
        data = {}
    entry = EventEntry(
        kind=kind,
        actor=actor_key,
        target=target,
        data=data,
        text_template=_FALLBACK_TEMPLATES[kind],
    )
    if kind != "resource_spend":
        return (entry,)
    return (
        entry,
        EventEntry(
            kind="trait_delta",
            actor=actor_key,
            target=target,
            data={
                "trait_key": data["resource_key"],
                "delta": -data["amount"],
            },
            text_template=_FALLBACK_TEMPLATES["trait_delta"],
        ),
    )


def _defeated_entry(
    actor_key: str,
    entity: Any,
    amount: int,
    projected: dict[int, float],
    defeated_ids: set[int],
    nonlethal: bool = False,
    simulated: bool = False,
) -> EventEntry | None:
    """Emit one ``target_defeated`` or ``target_knocked_out`` crossing entry.

    Pending damage is applied in order over shared projected HP, so two damage
    effects against one target neither use stale HP nor duplicate the defeat.
    Under a nonlethal policy a positive-to-non-positive crossing emits a
    ``target_knocked_out`` identity instead of ``target_defeated``, giving
    kill-credit/quest/loot consumers no defeat entry to observe. A simulated
    battle (guild examination) keeps the ordinary lethal ``target_defeated``
    entry but tags it ``simulated``, so kill-credit consumers can skip the
    defeat without hiding that the HP really crossed zero
    (exam-simulated-battle-redesign D4).

    A species-backed monster additionally carries its registered
    ``species_key``/``variant_key`` (never inferred from a display key or a
    tier); a tier-only target keeps exactly the fields it always had, so every
    existing consumer stays byte-compatible.
    """
    if amount <= 0:
        return None
    trait = getattr(entity, "traits", None)
    hp = getattr(trait, "hp", None)
    if hp is None:
        return None
    dbref = getattr(entity, "pk", None)
    if dbref is None:
        return None
    identity = id(entity)
    current = projected.get(identity, _stored_trait_value(hp))
    projected[identity] = current - amount
    if not (current > 0 and projected[identity] <= 0):
        return None
    if dbref in defeated_ids:
        return None
    defeated_ids.add(dbref)
    kind = "target_knocked_out" if nonlethal else "target_defeated"
    data: dict[str, Any] = {"target_id": int(dbref)}
    if not nonlethal:
        data["monster_tier"] = getattr(entity, "threat_tier", None)
        species_key = getattr(entity, "species_key", None)
        if species_key is not None:
            data["species_key"] = species_key
            data["variant_key"] = getattr(entity, "variant_key", None)
    if simulated:
        data["simulated"] = True
    return EventEntry(
        kind=kind,
        actor=actor_key,
        target=str(entity.key),
        data=data,
        text_template=(
            _FALLBACK_TEMPLATES["target_knocked_out"]
            if nonlethal
            else _FALLBACK_TEMPLATES["target_defeated"]
        ),
    )


def _max_hp_value(entity: Any) -> float | None:
    """Read one entity's stored maximum HP without advancing a gauge."""
    trait = getattr(getattr(entity, "traits", None), "hp", None)
    if trait is None:
        return None
    maximum = getattr(trait, "max", None)
    if maximum is None:
        maximum = getattr(trait, "max_value", None)
    if maximum is None:
        data = getattr(trait, "_data", None)
        if isinstance(data, dict):
            maximum = (
                data.get("base", 0) + data.get("mod", 0)
            ) * data.get("mult", 1)
    if maximum is None:
        return None
    try:
        return float(maximum)
    except (TypeError, ValueError):
        return None


def _max_hp_by_key(pending: list[PendingEffect]) -> dict[str, float]:
    """Map participant keys to their stored maximum HP for band selection."""
    maximums: dict[str, float] = {}
    for effect in pending:
        entity = effect.entity
        key = getattr(entity, "key", None)
        if key is None:
            continue
        key = str(key)
        if key in maximums:
            continue
        maximum = _max_hp_value(entity)
        if maximum is not None:
            maximums[key] = maximum
    return maximums


def _narrate_entries(
    entries: list[EventEntry],
    skill: SkillDef,
    scope: str,
    max_hp_by_key: dict[str, float],
) -> list[EventEntry]:
    """Return the entries with their authored narration templates selected.

    A lookup or rendering fault leaves that entry's numberless fallback in
    place: presentation must never reject a legal action (design D11).
    """
    family = family_key(skill)
    act = act_for_skill(skill.key)
    narrated: list[EventEntry] = []
    for ordinal, entry in enumerate(entries):
        if entry.kind in INTERNAL_KINDS:
            narrated.append(entry)
            continue
        target = entry.target or ""
        try:
            if entry.kind == "action_narration":
                template = action_line(
                    skill.key,
                    family,
                    scope=scope,
                    target_key=target,
                    actor=entry.actor,
                )
            else:
                template = entry_line(
                    entry.kind,
                    entry.data,
                    skill_key=skill.key,
                    family=family,
                    scope=scope,
                    ordinal=ordinal,
                    actor_key=entry.actor,
                    target_key=target,
                    actor=entry.actor,
                    target=target,
                    act=act,
                    max_hp=max_hp_by_key.get(
                        target
                    ) or max_hp_by_key.get(entry.actor),
                )
                if ordinal == 0:
                    template = compose_first_line(
                        skill.key,
                        family,
                        template,
                        scope=scope,
                        target_key=target,
                        actor=entry.actor,
                        target=target,
                    )
        except Exception:  # observability: ignore R2: narration is presentation and degrades rather than reject a legal action (design D11)
            narrated.append(entry)
            continue
        narrated.append(replace(entry, text_template=template))
    return narrated


def _step7_build_event_log(
    request: ActionRequest,
    skill: SkillDef,
    pending: list[PendingEffect],
    *,
    narration_scope: str = "",
) -> EventLog:
    try:
        entries: list[EventEntry] = []
        projected: dict[int, float] = {}
        defeated_ids: set[int] = set()
        event_context = _event_context(request)
        nonlethal = bool(event_context.get("nonlethal", False))
        nonlethal_keys = frozenset(event_context.get("nonlethal_keys", ()))
        simulated = bool(event_context.get("simulated", False))
        for effect in pending:
            entries.extend(
                _entries_from_effect(
                    _entity_key(request.actor),
                    effect,
                )
            )
            if effect.description.startswith("damage|"):
                parts = effect.description.split("|")
                amount = int(parts[4])
            elif effect.description.startswith("gauge_transfer|"):
                parts = effect.description.split("|")
                if len(parts) >= 5 and parts[2] == "hp" and parts[3] == "drain":
                    amount = int(parts[4])
                else:
                    continue
            else:
                continue
            defeated = _defeated_entry(
                _entity_key(request.actor),
                effect.entity,
                amount,
                projected,
                defeated_ids,
                nonlethal=nonlethal or str(effect.entity.key) in nonlethal_keys,
                simulated=simulated,
            )
            if defeated is not None:
                entries.append(defeated)
        if not entries:
            # A successful action whose effects staged nothing still tells the
            # player which skill they used. This is the single entry narration
            # may add (design D4).
            entries.append(
                EventEntry(
                    kind="action_narration",
                    actor=_entity_key(request.actor),
                    target=None,
                    data={},
                    text_template="",
                )
            )
        scope = narration_scope or str(
            event_context.get("narration_scope", "") or ""
        )
        try:
            entries = _narrate_entries(
                entries, skill, scope, _max_hp_by_key(pending)
            )
        except Exception:  # observability: ignore R2: narration is presentation and degrades rather than reject a legal action (design D11)
            pass
    except Exception as error:
        raise RejectedAction(
            RejectReason.EVENT_LOG_CONSTRUCTION_FAILED,
            str(error),
        ) from error
    return EventLog(
        actor=_entity_key(request.actor),
        skill_key=skill.key,
        targets=_logged_targets(pending),
        entries=tuple(entries),
        time_cost_seconds=0,
    )


def _logged_targets(pending: list[PendingEffect]) -> tuple[str, ...]:
    targets: list[str] = []
    for effect in pending:
        if effect.description.startswith(
            (
                "resource_spend|",
                "combat_kill_xp|",
                "knocked_out_mark|",
                "self_return_clear|",  # Design D4: actor clearing own marker must not appear as target
            )
        ):
            continue
        key = effect.description.split("|", 2)[1]
        if key not in targets:
            targets.append(key)
    return tuple(targets)
