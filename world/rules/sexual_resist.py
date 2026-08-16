"""Deterministic sexual-act resist contest (sexual-resist-contest B6a).

``resist_verdict()`` decides whether a resisting participant successfully
refuses a bidirectional sexual act. It is a pure function: it reads only the
two participants' live combat state and affinity record, mutates nothing, and
consults no ``Battlefield``, so it can be built and tested in isolation from
the acts and turn-cost wiring that will later call it.

The ordinary contest reuses ``disengage.py::_attempt_flee``'s exact shape
(``roll_d100() + resister_score >= COMBAT_YAML["to_hit"]["defender_constant"]
+ actor_score``) rather than inventing a second idiom. Each participant's
score blends effective ``agility`` (the speed to break away) with effective
``atk_phys`` (the strength to physically break free), weighted by
``sexual_resist.yaml`` and read through the no-create combat-modifier query
(``evaluate_combat_modifiers_no_create``) with the same stat-specific
treatments the two shipped consumers use: ``agility`` as a percentage string
via ``combat._apply_percent_mod`` (as ``disengage._adjusted_agility`` does)
and ``atk_phys`` as a flat addend (as ``combat._adjusted_attack`` does).

Before any roll, ``resist_verdict()`` short-circuits to compliance when the
resister's affinity stage toward the actor carries ``auto_comply: true``
(``至愛``/``絕對羈絆``, only for an ``NPC`` resister facing a
``PlayerCharacter`` actor), when the resister's stored ``submission_marks``
names the actor (the 絕對從屬 mark, keyed by the actor's unique database id),
or when the resister is mid-climax within the
``climax_turn_auto_comply_limit`` (first five settlement points in 進行中).
Every read is no-create: the scores and both state short circuits read
persistent storage without ever materializing the ``sexual`` handler
(materializing it would create persistent traits on first access and break
the function's no-mutation contract). The rulebook is loaded and validated
exactly once through ``get_resist_config()``'s module-level singleton,
mirroring ``affinity_config.get_config()``'s lazy-cache pattern rather than
an import-time eager load: the loader validates the affinity table against
``get_config()``, whose own loader requires the quest definition registry,
which only server startup or test setup populates.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.rules import combat
from world.rules.affinity_config import get_config
from world.rules.combat_modifiers import (
    build_no_create_condition_context,
    evaluate_combat_modifiers_no_create,
)
from world.rules.dice import roll_d100

_SEXUAL_RESIST_RULEBOOK = Path(__file__).with_name("rulebook") / "sexual_resist.yaml"


class SexualResistConfigError(ValueError):
    """The sexual_resist.yaml rulebook violates the canonical contract."""


@dataclass(frozen=True)
class SexualResistConfig:
    """The validated sexual_resist.yaml balance table.

    ``resist_modifiers`` maps each numeric-modifier stage id to its flat
    resister-score bonus; ``auto_comply_stages`` names the stage ids whose
    entry is ``{auto_comply: true}`` instead of a number.
    """

    agility_weight: float
    atk_phys_weight: float
    climax_turn_auto_comply_limit: int
    resist_modifiers: Mapping[str, float]
    auto_comply_stages: frozenset[str]


def _error(message: str) -> SexualResistConfigError:
    return SexualResistConfigError(f"sexual_resist.yaml: {message}")


def _require_weight(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error(f"{field} must be a number")
    if not isfinite(value):
        raise _error(f"{field} must be finite")
    if value < 0:
        raise _error(f"{field} must be non-negative")
    return float(value)


def load_sexual_resist_config(path: Path | None = None) -> SexualResistConfig:
    """Load and validate the resist rulebook, failing closed on deviation.

    ``path`` overrides the canonical rulebook location so tests can exercise
    deviant tables through a temporary copy, keeping the shared source file
    untouched.
    """
    rulebook = _SEXUAL_RESIST_RULEBOOK if path is None else path
    raw = yaml.safe_load(rulebook.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise _error("rulebook must be a mapping")
    raw = dict(raw)
    known = {
        "agility_weight",
        "atk_phys_weight",
        "climax_turn_auto_comply_limit",
        "affinity_resist_modifier",
    }
    unknown = set(raw) - known
    if unknown:
        raise _error(f"unknown top-level fields {sorted(unknown)}")
    missing = known - set(raw)
    if missing:
        raise _error(f"missing top-level fields {sorted(missing)}")

    agility_weight = _require_weight(raw["agility_weight"], "agility_weight")
    atk_phys_weight = _require_weight(raw["atk_phys_weight"], "atk_phys_weight")
    weight_sum = agility_weight + atk_phys_weight
    if weight_sum != 1.0:
        raise _error(
            "agility_weight + atk_phys_weight must sum to exactly 1.0, "
            f"got {weight_sum}"
        )

    limit = raw["climax_turn_auto_comply_limit"]
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise _error("climax_turn_auto_comply_limit must be a positive integer")

    affinity_raw = raw["affinity_resist_modifier"]
    if not isinstance(affinity_raw, Mapping):
        raise _error("affinity_resist_modifier must be a mapping")
    affinity_raw = dict(affinity_raw)
    stage_ids = {stage.id for stage in get_config().stages}
    if set(affinity_raw) != stage_ids:
        raise _error(
            "affinity_resist_modifier must carry exactly the stage ids "
            f"{sorted(stage_ids)}, missing {sorted(stage_ids - set(affinity_raw))}, "
            f"extra {sorted(set(affinity_raw) - stage_ids)}"
        )
    modifiers: dict[str, float] = {}
    auto_comply: set[str] = set()
    for stage_id in sorted(stage_ids):
        entry = affinity_raw[stage_id]
        if (
            isinstance(entry, Mapping)
            and set(entry) == {"auto_comply"}
            and entry["auto_comply"] is True
        ):
            auto_comply.add(stage_id)
            continue
        if isinstance(entry, bool) or not isinstance(entry, (int, float)):
            raise _error(
                f"affinity_resist_modifier.{stage_id} must be a finite "
                "number or {auto_comply: true}"
            )
        if not isfinite(entry):
            raise _error(
                f"affinity_resist_modifier.{stage_id} must be a finite "
                "number or {auto_comply: true}"
            )
        modifiers[stage_id] = float(entry)
    return SexualResistConfig(
        agility_weight=agility_weight,
        atk_phys_weight=atk_phys_weight,
        climax_turn_auto_comply_limit=limit,
        resist_modifiers=modifiers,
        auto_comply_stages=frozenset(auto_comply),
    )


_RESIST_CONFIG: SexualResistConfig | None = None


def get_resist_config() -> SexualResistConfig:
    """Return the validated resist rulebook singleton, loaded on first access.

    Loaded and validated exactly once, never per call — the same lazy-cache
    pattern ``affinity_config.get_config()`` uses. An import-time eager load
    is impossible here: the loader validates against ``get_config()``, whose
    own loader requires the quest definition registry (``cap_breaks``
    validation), and that registry is only populated by server startup or
    test setup.
    """
    global _RESIST_CONFIG
    if _RESIST_CONFIG is None:
        _RESIST_CONFIG = load_sexual_resist_config()
    return _RESIST_CONFIG


@dataclass(frozen=True)
class ResistVerdict:
    """The structured outcome of one resist contest.

    ``auto_comply`` is ``True`` exactly when no roll occurred; ``roll`` is
    then ``None``. The two scores are the participants' final contest scores
    (the resister's includes any affinity modifier), so a caller can build
    an EventLog description without recomputing anything.
    """

    resisted: bool
    auto_comply: bool
    roll: int | None
    actor_score: float
    resister_score: float


def _blended_score(entity: Any) -> float:
    """Return the weighted agility/atk_phys contest score for one participant.

    ``agility`` is adjusted via ``combat._apply_percent_mod`` against the
    no-create modifier bundle's ``"agility"`` key (a percentage string,
    mirroring ``disengage._adjusted_agility`` exactly); ``atk_phys`` is added
    as a flat addend (mirroring ``combat._adjusted_attack`` exactly). Neither
    stat's adjustment is routed through the other stat's treatment: feeding a
    flat integer through ``_apply_percent_mod`` would raise ``TypeError``.
    The no-create query is load-bearing: the live variant materializes the
    ``sexual`` handler, which persists traits on first access and would break
    ``resist_verdict()``'s no-mutation contract.
    """
    modifiers = evaluate_combat_modifiers_no_create(entity)
    config = get_resist_config()
    agility_component = combat._apply_percent_mod(
        float(entity.skills.effective_value("agility")),
        modifiers.get("agility"),
    )
    atk_phys_component = (
        float(entity.skills.effective_value("atk_phys"))
        + modifiers.get("atk_phys", 0)
    )
    return (
        agility_component * config.agility_weight
        + atk_phys_component * config.atk_phys_weight
    )


def _affinity_term(actor: Any, resister: Any) -> tuple[float, bool]:
    """Return the resister's affinity contribution and its auto-comply flag.

    Only an ``NPC`` resister facing a ``PlayerCharacter`` actor has an
    affinity term: the resister's stored stage toward the actor is read
    through ``resister.relations.stage_for(actor)`` and mapped to either a
    flat modifier or ``auto_comply``. Every other shape — a ``Monster``
    resister (whose ``relations`` handler is never populated), an ``NPC``
    resister paired with a non-player actor, or any other pair — contributes
    ``(0.0, False)`` without reading ``.relations`` at all. The explicit
    ``isinstance`` gate is load-bearing: every ``LivingEntity`` mounts a
    ``relations`` handler, so a ``hasattr`` check would silently grant a
    monster the 初識 bonus.
    """
    if not isinstance(resister, NPC) or not isinstance(actor, PlayerCharacter):
        return (0.0, False)
    config = get_resist_config()
    stage_id = resister.relations.stage_for(actor).id
    if stage_id in config.auto_comply_stages:
        return (0.0, True)
    return (config.resist_modifiers.get(stage_id, 0.0), False)


def _climax_turn_short_circuit(resister: Any) -> bool:
    """Whether a mid-climax resister auto-complies on this settlement point.

    ``True`` when the resister's stored ``climax_phase`` level is 進行中 and
    its stored ``climax_turns`` has not yet exceeded
    ``climax_turn_auto_comply_limit`` (the first five settlement points).
    From the sixth settlement point the ordinary contest applies.

    Both facts are read from persistent storage without materializing the
    ``sexual`` handler — materializing it would create persistent traits on
    first access, breaking ``resist_verdict()``'s no-mutation contract — using
    the same stored-state context ``build_no_create_condition_context``
    supplies to the preview and no-create paths. An entity whose sexual state
    has never been touched reads as not-in-進行中 and falls through to the
    ordinary contest.
    """
    context = build_no_create_condition_context(resister)
    if context.get("climax_phase") != "進行中":
        return False
    turns = resister.attributes.get(
        "climax_turns", default=0, category="sexual_state"
    )
    return turns <= get_resist_config().climax_turn_auto_comply_limit


def _submission_term(actor: Any, resister: Any) -> bool:
    """Whether the resister is permanently marked submissive to this actor.

    ``True`` when the resister's stored ``submission_marks`` set contains
    ``str(actor.id)`` — the guaranteed-unique per-instance database key, never
    ``actor.key``/``_entity_key(actor)``, which is shared across same-species
    ``Monster`` spawns and would misattribute the permanent, unremovable mark
    (divine-sexual-arts-mutators D-5).

    The read goes through ``resister.attributes.get(...)`` directly, never
    ``resister.sexual`` — materializing the ``sexual`` handler persists traits
    on first access and would break ``resist_verdict()``'s no-create contract,
    exactly like ``_climax_turn_short_circuit``'s ``climax_turns`` read.
    """
    marks = resister.attributes.get(
        "submission_marks", default=frozenset(), category="sexual_state"
    )
    return str(actor.id) in marks


def resist_verdict(
    actor: Any,
    resister: Any,
    *,
    rng: Callable[[], int] = roll_d100,
) -> ResistVerdict:
    """Resolve one two-party resist contest without mutating any state.

    ``actor`` is the participant casting the act; ``resister`` is the
    participant deciding whether to refuse it. The contest is strictly
    two-party, so no ``Battlefield`` is consulted. ``rng`` is injectable for
    determinism; the default is the shipped ``world.rules.dice.roll_d100``.

    Auto-comply short circuits (affinity stage ``auto_comply``, a
    ``submission_marks`` entry naming the actor, or the climax-turn limit)
    return before ``rng()`` is ever called; otherwise the ordinary contest
    formula applies with both scores read from the no-create stored-state
    bundle.
    """
    actor_score = _blended_score(actor)
    resister_score = _blended_score(resister)
    affinity_modifier, affinity_auto_comply = _affinity_term(actor, resister)
    resister_score += affinity_modifier
    if (
        affinity_auto_comply
        or _submission_term(actor, resister)
        or _climax_turn_short_circuit(resister)
    ):
        return ResistVerdict(
            resisted=False,
            auto_comply=True,
            roll=None,
            actor_score=actor_score,
            resister_score=resister_score,
        )
    raw_roll = rng()
    resisted = (
        raw_roll + resister_score
        >= combat.COMBAT_YAML["to_hit"]["defender_constant"] + actor_score
    )
    return ResistVerdict(
        resisted=resisted,
        auto_comply=False,
        roll=raw_roll,
        actor_score=actor_score,
        resister_score=resister_score,
    )


__all__ = ["ResistVerdict", "get_resist_config", "resist_verdict"]
