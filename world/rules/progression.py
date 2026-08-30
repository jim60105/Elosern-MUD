"""Deterministic skill-practice progression and freeform scaling rules."""

from collections.abc import Sequence
from math import floor, isfinite
from pathlib import Path
from typing import Any

import yaml

from world.lore.elements import ELEMENT_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.skills.cost_tiers import is_freeform_eligible
from world.skills.effects import DamageEffect
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillPrerequisite,
    SkillDef,
    SkillKind,
    prerequisite_consumers,
)


PROGRESSION_YAML = yaml.safe_load(
    (Path(__file__).parent / "rulebook" / "progression.yaml").read_text(
        encoding="utf-8"
    )
)
SKILL_PROFICIENCY_XP_PER_LEVEL = float(
    PROGRESSION_YAML["skill_proficiency_xp_per_level"]
)
SKILL_PRACTICE_XP_PER_USE = float(PROGRESSION_YAML["skill_practice_xp_per_use"])
AFFINITY_ELEMENT_MULTIPLIER = float(
    PROGRESSION_YAML["affinity_element_multiplier"]
)
NON_AFFINITY_ELEMENT_MULTIPLIER = float(
    PROGRESSION_YAML["non_affinity_element_multiplier"]
)
PRACTICE_XP_PER_STUDY_HOUR = float(PROGRESSION_YAML["practice_xp_per_study_hour"])
if not isfinite(PRACTICE_XP_PER_STUDY_HOUR) or PRACTICE_XP_PER_STUDY_HOUR <= 0:
    raise ValueError("practice_xp_per_study_hour must be a positive finite number")


FREEFORM_CAST_SCALE_COUNT = 5

# The fixed canonical freeform scale table (freeform-casting spec): exact
# (scale, label) pairs in ascending order. A table that deviates in any value
# or label pairing fails closed at load — no consumer may ever run a different
# set.
FREEFORM_CANONICAL_SCALES: tuple[tuple[float, str], ...] = (
    (0.25, "1/4"),
    (0.5, "1/2"),
    (1.0, "1"),
    (2.0, "2"),
    (4.0, "4"),
)


def _load_freeform_cast_scales(
    raw: Any,
) -> tuple[tuple[float, str], ...]:
    """Load and fail-closed validate the closed freeform scale table.

    The table must carry exactly ``FREEFORM_CAST_SCALE_COUNT`` entries, each
    an object with a finite positive ``scale`` and a non-empty string
    ``label``; scales must be unique and strictly ascending, labels unique,
    and exactly one entry must carry ``scale == 1.0``. The parsed table must
    then equal the canonical ``FREEFORM_CANONICAL_SCALES`` set exactly — any
    deviation in a scale value or its label pairing raises a named
    ``ValueError`` before any consumer can read a partial or deviant set.
    """
    entries = raw.get("freeform_cast_scales")
    if not isinstance(entries, list) or len(entries) != FREEFORM_CAST_SCALE_COUNT:
        raise ValueError(
            "freeform_cast_scales must be a list of exactly "
            f"{FREEFORM_CAST_SCALE_COUNT} entries"
        )
    parsed: list[tuple[float, str]] = []
    seen_scales: set[float] = set()
    seen_labels: set[str] = set()
    has_one = False
    previous = 0.0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"scale", "label"}:
            raise ValueError(
                f"freeform_cast_scales entry {index} must be {{scale, label}}"
            )
        scale = entry["scale"]
        label = entry["label"]
        if isinstance(scale, bool) or not isinstance(scale, (int, float)):
            raise ValueError(
                f"freeform_cast_scales entry {index} scale must be numeric"
            )
        scale = float(scale)
        if not isfinite(scale) or scale <= 0:
            raise ValueError(
                f"freeform_cast_scales entry {index} scale must be finite and positive"
            )
        if scale in seen_scales:
            raise ValueError(
                f"freeform_cast_scales entry {index} duplicates scale {scale:g}"
            )
        if scale <= previous:
            raise ValueError(
                "freeform_cast_scales must be strictly ascending, entry "
                f"{index} has scale {scale:g}"
            )
        if not isinstance(label, str) or not label.strip():
            raise ValueError(
                f"freeform_cast_scales entry {index} label must be non-empty"
            )
        if label in seen_labels:
            raise ValueError(
                f"freeform_cast_scales entry {index} duplicates label {label!r}"
            )
        if scale == 1.0:
            has_one = True
        seen_scales.add(scale)
        seen_labels.add(label)
        parsed.append((scale, label))
        previous = scale
    if not has_one:
        raise ValueError("freeform_cast_scales must contain exactly one 1.0 entry")
    canonical = tuple(parsed)
    if canonical != FREEFORM_CANONICAL_SCALES:
        raise ValueError(
            "freeform_cast_scales must equal the canonical set "
            f"{FREEFORM_CANONICAL_SCALES!r}, got {canonical!r}"
        )
    return canonical


# The closed freeform-casting scale set: ascending ``(scale, label)`` pairs
# shared by the resolver gate, the preview, the wire validator, and the text
# command. Never hard-code the set anywhere else.
FREEFORM_CAST_SCALES: tuple[tuple[float, str], ...] = _load_freeform_cast_scales(
    PROGRESSION_YAML
)
# Canonical table membership (the closed wire-level scale set). NOT the
# actor's entitlement: which rungs one may actually cast derives from
# :func:`freeform_scales_for` (the ladder).
FREEFORM_SCALE_VALUES = tuple(scale for scale, _ in FREEFORM_CAST_SCALES)
FREEFORM_SCALE_LABELS = frozenset(label for _, label in FREEFORM_CAST_SCALES)


def _load_freeform_scale_ladder(
    raw: Any, canonical: tuple[tuple[float, str], ...]
) -> tuple[tuple[float, int], ...]:
    """Load and fail-closed validate the proficiency-anchored scale ladder.

    Each rung is ``{scale, min_level}``: the scale must be a canonical table
    member, ``min_level`` an int >= 0, and both sequences strictly ascending
    starting at level 0 (the entry rung is unconditional for an entitled
    actor). A ladder deviating in any way fails at import.
    """
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise ValueError("freeform_scale_ladder must be a non-empty sequence")
    canonical_values = {scale for scale, _ in canonical}
    parsed: list[tuple[float, int]] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict) or set(entry) != {"scale", "min_level"}:
            raise ValueError(
                "freeform_scale_ladder entries must name exactly scale and "
                f"min_level, got {entry!r} at index {index}"
            )
        scale, min_level = entry["scale"], entry["min_level"]
        if (
            isinstance(scale, bool)
            or not isinstance(scale, (int, float))
            or not isfinite(scale)
            or scale <= 0
            or float(scale) not in canonical_values
        ):
            raise ValueError(
                f"freeform_scale_ladder scale {scale!r} is not a canonical "
                "positive finite scale at index "
                f"{index}"
            )
        if isinstance(min_level, bool) or not isinstance(min_level, int) or min_level < 0:
            raise ValueError(
                f"freeform_scale_ladder min_level must be an int >= 0, got "
                f"{min_level!r} at index {index}"
            )
        if parsed:
            if float(scale) <= parsed[-1][0]:
                raise ValueError("freeform_scale_ladder scales must ascend")
            if min_level <= parsed[-1][1]:
                raise ValueError("freeform_scale_ladder levels must ascend")
        parsed.append((float(scale), min_level))
    if parsed[0][1] != 0:
        raise ValueError("freeform_scale_ladder must start at min_level 0")
    return tuple(parsed)


# The proficiency ladder (use-driven-progression D5): ascending
# ``(scale, min_level)`` rungs an entitled actor unlocks through the CAST
# SKILL's own proficiency. Never hard-coded anywhere else.
FREEFORM_SCALE_LADDER: tuple[tuple[float, int], ...] = _load_freeform_scale_ladder(
    PROGRESSION_YAML["freeform_scale_ladder"], FREEFORM_CAST_SCALES
)

# D6 canopy default: the tip cap of a skill nobody consumes in the
# prerequisite graph.
PROFICIENCY_TIP_CAP = int(PROGRESSION_YAML["proficiency_tip_cap"])
if PROFICIENCY_TIP_CAP < 1:
    raise ValueError("proficiency_tip_cap must be >= 1")


def _validate_nonnegative_multiplier(value: float, name: str) -> None:
    """Fail closed on a non-finite or negative balance constant (design D5)."""
    if not isfinite(value) or value < 0:
        raise ValueError(
            f"progression constant {name} must be finite and non-negative"
        )


_validate_nonnegative_multiplier(AFFINITY_ELEMENT_MULTIPLIER, "affinity_element_multiplier")
_validate_nonnegative_multiplier(
    NON_AFFINITY_ELEMENT_MULTIPLIER, "non_affinity_element_multiplier"
)

# Rank-title data labels shared with the MP cost bands (skill-registry spec):
# the five tiers group spells by cost and display only. 主宰 is 91 to mirror
# ``MP_COST_TIERS``. The numeric cast gate that once consumed these thresholds
# was retired by ``magic-xp-engine-retirement``; nothing may reintroduce a
# tier-based cast gate.
MAGIC_TIER_THRESHOLDS: dict[str, int] = {
    "學徒": 0,
    "術師": 16,
    "大師": 31,
    "賢者": 71,
    "主宰": 91,
}


def _affinity_elements(entity: Any) -> list[str]:
    """Return the validated lowercase affinity-element keys or an empty list.

    Reads ``entity.db.affinity_elements`` when the Evennia attribute handler
    exists (real characters, monsters, and NPCs), and falls back to a plain
    ``affinity_elements`` attribute so pure in-memory test entities stay
    supported. Evennia returns ``_SaverList`` wrappers (not ``list``), so the
    check accepts any non-string sequence. An absent or empty collection reads
    as neutral.
    """
    db = getattr(entity, "db", None)
    value = None
    if db is not None:
        value = getattr(db, "affinity_elements", None)
    if value is None:
        value = getattr(entity, "affinity_elements", None)
    if not value:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("affinity_elements must be a sequence of element keys")
    return [str(entry) for entry in value]


def element_affinity_multiplier(entity: Any, element: str) -> float:
    """Return the finite per-element affinity multiplier (element-affinity D2).

    Pure read-only query over ``entity.db.affinity_elements``: exactly ``1.1``
    when ``element`` is a declared affinity, ``0.9`` when the entity declares
    affinities and ``element`` is not among them, and exactly ``1.0`` for an
    entity with no declared affinities (the current-behavior-preserving
    default). An unrecognized element key raises ``ValueError``. Never writes
    any entity attribute.
    """
    if element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown element {element!r}")
    affinities = _affinity_elements(entity)
    if not affinities:
        return 1.0
    if element in affinities:
        return AFFINITY_ELEMENT_MULTIPLIER
    return NON_AFFINITY_ELEMENT_MULTIPLIER


def _validate_scale_inputs(base: int, scale: float, name: str) -> None:
    """Fail closed on a non-positive base or a non-finite/non-positive scale."""
    if isinstance(base, bool) or not isinstance(base, int) or base <= 0:
        raise ValueError(f"{name} base must be a positive integer, got {base!r}")
    if (
        isinstance(scale, bool)
        or not isinstance(scale, (int, float))
        or not isfinite(scale)
        or scale <= 0
    ):
        raise ValueError(f"{name} scale must be finite and positive, got {scale!r}")


def scaled_magnitude(base: int, scale: float) -> int:
    """Return ``floor(base * scale + 0.5)`` — deterministic round-half-away.

    The single magnitude-scaling helper shared by the damage, heal, and
    self-heal handlers so cost and magnitude scale identically everywhere.
    """
    _validate_scale_inputs(base, scale, "scaled_magnitude")
    return int(floor(float(base) * float(scale) + 0.5))


def scaled_mp_cost(base: int, scale: float) -> int:
    """Return the scaled MP cost, never below one.

    The same deterministic rounding as :func:`scaled_magnitude`, clamped to a
    minimum of ``1``: a scaled cost can never be zero, so no scale combination
    can ever produce a free cast.
    """
    _validate_scale_inputs(base, scale, "scaled_mp_cost")
    return max(1, scaled_magnitude(base, scale))


def freeform_mastery_entitled(entity: Any, element: str) -> bool:
    """Return whether the entity directly owns the element's mastery passive.

    Pure side-effect-free entitlement query: ``element`` is validated against
    ``ELEMENT_REGISTRY`` first (an unrecognized element raises ``ValueError``
    even when the entity owns a fabricated ``<element>_mastery``), then
    ``True`` when ``f"{element}_mastery"`` appears in
    ``entity.skills.owned_keys()`` (direct ownership only, never
    ``conferred_grants()``). It grants NO scale by itself; the unlocked set is
    the skill-anchored :func:`freeform_scales_for`. Never writes entity state.
    """
    if element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown element {element!r}")
    return f"{element}_mastery" in entity.skills.owned_keys()


def freeform_scales_for(entity: Any, skill: SkillDef) -> tuple[float, ...]:
    """Return the freeform scales one SKILL's own proficiency unlocks.

    The single ladder authority (use-driven-skill-lineage DC5): empty for a
    non-elemental skill or a non-entitled actor, else the ascending ladder
    rungs whose ``min_level`` the entity's OWN proficiency in ``skill``
    reaches AND which sit at or below the skill's derived tip cap — a rung
    gated above ``proficiency_cap(skill.key)`` could never be practised to,
    so it never unlocks (a Lv.3-capped mid-tree spell tops out at the 1.0
    rung). Skill-anchored on purpose: a mastery holder with a level-10 canopy
    spell cannot scale a cap-5 mid-tree spell past its own rung, so no caller
    can ever advertise a scale the resolver would reject. Never writes entity
    state.
    """
    if skill.element is None:
        return ()
    if not freeform_mastery_entitled(entity, skill.element.key):
        return ()
    level = skill_proficiency_level(entity, skill.key)
    cap = proficiency_cap(skill.key)
    return tuple(
        scale
        for scale, min_level in FREEFORM_SCALE_LADDER
        if level >= min_level and min_level <= cap
    )


def freeform_scale_entries_for(actor: Any, skill: Any) -> tuple[tuple[float, str, int], ...]:
    """Return the actor's allowed scale entries for one eligible skill.

    Entries are strictly ascending ``(scale, label, mp_cost)`` where
    ``mp_cost`` is computed server-side with the shared rounding helper, so
    the browser never re-implements cost scaling. An ineligible skill or an
    actor without direct mastery ownership of the skill's element yields an
    empty tuple, so the panel can omit the field entirely (the freeform
    feature is invisible to non-masters). The rungs come from the
    skill-anchored ladder, so the advertised set and the resolver gate can
    never diverge.
    """
    if not is_freeform_eligible(skill) or skill.element is None:
        return ()
    allowed = frozenset(freeform_scales_for(actor, skill))
    if not allowed:
        return ()
    base_mp = int(skill.cost["mp"])
    return tuple(
        (scale, label, scaled_mp_cost(base_mp, scale))
        for scale, label in FREEFORM_CAST_SCALES
        if scale in allowed
    )


def scale_label_for(scale: float) -> str | None:
    """Return the canonical table label for one scale, or ``None``.

    The label is display-only (e.g. ``"1/4"``); ``None`` means the value is
    not a member of the closed set.
    """
    for member, label in FREEFORM_CAST_SCALES:
        if scale == member:
            return label
    return None


def scale_for_label(label: str) -> float | None:
    """Return the scale for one canonical table label, or ``None``."""
    for member, canonical in FREEFORM_CAST_SCALES:
        if label == canonical:
            return member
    return None


def _race_learning_multiplier(entity: Any) -> float:
    race_key = getattr(entity, "race", None)
    race = RACE_REGISTRY.get(race_key) if race_key else None
    return float(race.learning_multiplier) if race is not None else 1.0


def skill_proficiency_level(entity: Any, skill_key: str) -> int:
    """Return the whole proficiency level derived from stored practice XP."""
    proficiency = entity.db.skill_proficiency or {}
    return int(float(proficiency.get(skill_key, 0.0)) // SKILL_PROFICIENCY_XP_PER_LEVEL)


def can_use_skill(entity: Any, skill: SkillDef) -> bool:
    """Return whether the entity may USE one skill right now (the ONE gate).

    Pure, side-effect-free predicate (DC2): ownership of the skill, then every
    declared prerequisite edge — the prereq key must also be owned and its
    derived proficiency level must reach the threshold. School-agnostic: a
    weapon skill and a spell traverse this identical path, so 主宰-tier entry
    is simply every edge on the path into that node (AND semantics). MP
    affordability and every other check stay in the resolver; this answers
    lineage eligibility only.
    """
    owned = entity.skills.owned_keys()
    if skill.key not in owned:
        return False
    for prereq in skill.prerequisites:
        if prereq.skill_key not in owned:
            return False
        if skill_proficiency_level(entity, prereq.skill_key) < prereq.min_proficiency:
            return False
    return True


def missing_prerequisite(entity: Any, skill: SkillDef) -> SkillPrerequisite | None:
    """Return the first unmet prerequisite edge of ``skill``, or ``None``.

    Reports in declared edge order so rejection text is deterministic. The
    caller owns the ownership check for the skill itself; this only walks the
    prerequisite list (an already-usable skill yields ``None``).
    """
    owned = entity.skills.owned_keys()
    for prereq in skill.prerequisites:
        if prereq.skill_key not in owned:
            return prereq
        if skill_proficiency_level(entity, prereq.skill_key) < prereq.min_proficiency:
            return prereq
    return None


def proficiency_cap(skill_key: str) -> int:
    """Return the derived tip cap for one skill (D6, rule 1).

    ``cap(S)`` is the maximum ``min_proficiency`` over every edge consuming
    ``S`` — read from the registry's load-time reverse-edge map, so branching
    and merging topologies need no special case — or ``PROFICIENCY_TIP_CAP``
    when nobody consumes it. A ceiling is therefore never below any single
    consuming edge, so a saturated prerequisite never blocks its child.
    """
    consumers = prerequisite_consumers(skill_key)
    if not consumers:
        return PROFICIENCY_TIP_CAP
    return max(min_proficiency for _, min_proficiency in consumers)


def award_practice_xp(entity: Any, skill_key: str, xp: float) -> None:
    """THE accrual writer for ``db.skill_proficiency``; saturating at the cap.

    Every practice entry point (the per-use grant and the booked-practice
    settlement) routes through this one primitive, so the two can never
    diverge at a cap boundary: once
    ``skill_proficiency_level(entity, skill_key)`` reaches
    :func:`proficiency_cap`, further XP is dropped and the stored value never
    exceeds ``cap * SKILL_PROFICIENCY_XP_PER_LEVEL``. Fails closed on a
    non-finite or negative amount before any write.
    """
    if isinstance(xp, bool) or not isinstance(xp, (int, float)) or not isfinite(xp):
        raise ValueError(f"practice XP must be a finite number, got {xp!r}")
    if xp < 0:
        raise ValueError(f"practice XP must be non-negative, got {xp!r}")
    if xp == 0:
        return
    cap = proficiency_cap(skill_key)
    stored = dict(entity.db.skill_proficiency or {})
    current = float(stored.get(skill_key, 0.0))
    if current // SKILL_PROFICIENCY_XP_PER_LEVEL >= cap:
        return
    stored[skill_key] = min(
        current + float(xp), cap * SKILL_PROFICIENCY_XP_PER_LEVEL
    )
    entity.db.skill_proficiency = stored


def _is_elemental_magic(skill: SkillDef) -> bool:
    """Return whether element affinity may ever scale this skill's practice.

    ``basic_attack`` carries ``element == fire`` with a PHYSICAL damage
    school, so the element field alone cannot decide affinity eligibility:
    only a skill whose parsed effects include a magic-school damage of its own
    element is elemental magic. Physical and non-elemental skills take the
    neutral ``1.0`` (design §8: the accrual formula reads no school bias, but
    affinity is a magic-affinity concept by definition).
    """
    if skill.element is None:
        return False
    return any(
        isinstance(effect, DamageEffect)
        and effect.school == "magic"
        and effect.element == skill.element.key
        for effect in skill.parsed_effects
    )


# Per-tick practice dedupe (D6, rule 2). Transient by contract: a module-level
# dict keyed by the current world-clock tick plus the claimed
# ``(actor, skill_key, target)`` triples. Never persisted, never snapshotted,
# never restored — a rollback releases its claims explicitly instead.
_dedupe_tick: int | None = None
_dedupe_seen: set[tuple[Any, str, Any]] = set()


def _dedupe_key(entity: Any) -> Any:
    """Return a stable identity for one entity inside this process."""
    pk = getattr(entity, "pk", None)
    return pk if pk is not None else id(entity)


def _current_tick() -> int:
    """Return the current world-clock tick, or 0 when no clock exists yet.

    Read through ``read_world_clock()`` so a pure/unit context (no persisted
    singleton) still gets a usable, monotonic-enough bucket without creating
    one. Import is deferred: ``world.rules.clock`` imports the rules layer
    broadly, and the dedupe path must never create an import cycle.
    """
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return int(clock.tick) if clock is not None else 0


def _claim_practice(actor: Any, skill_key: str, target: Any) -> bool:
    """Claim ``(actor, skill, target)`` for this tick; ``False`` if taken.

    The first claim of a tick clears the previous tick's set, so the state is
    bounded by one tick's distinct triples. Claims are released on a rolled
    back commit via :func:`release_practice_claims`.
    """
    global _dedupe_tick
    tick = _current_tick()
    if _dedupe_tick != tick:
        _dedupe_tick = tick
        _dedupe_seen.clear()
    key = (_dedupe_key(actor), skill_key, None if target is None else _dedupe_key(target))
    if key in _dedupe_seen:
        return False
    _dedupe_seen.add(key)
    return True


def practice_claim_key(actor: Any, skill_key: str, target: Any) -> tuple[Any, str, Any]:
    """Return the dedupe key one practice award occupies.

    Computed exactly as :func:`_claim_practice` computes it, so the action
    pipeline can record which claims a staged batch took and release precisely
    those on a rolled-back commit.
    """
    return (
        _dedupe_key(actor),
        skill_key,
        None if target is None else _dedupe_key(target),
    )


def release_practice_claims(claims: Sequence[tuple[Any, str, Any]]) -> None:
    """Release dedupe claims made by a commit that was rolled back.

    A rolled-back action restored the proficiency surface without a
    successful accrual, so its dedupe claims must not suppress the XP a
    legitimate same-tick retry would earn.
    """
    for actor_key, skill_key, target_key in claims:
        _dedupe_seen.discard((actor_key, skill_key, target_key))


def practice_claims_for(actor: Any, skill_key: str) -> set[tuple[Any, str, Any]]:
    """Return the claims this actor currently holds for one skill (tests/diag)."""
    actor_key = _dedupe_key(actor)
    return {key for key in _dedupe_seen if key[0] == actor_key and key[1] == skill_key}


def reset_practice_dedupe() -> None:
    """Clear the transient dedupe state (test isolation only)."""
    global _dedupe_tick
    _dedupe_tick = None
    _dedupe_seen.clear()


def snapshot_practice_dedupe() -> tuple[int | None, frozenset]:
    """Return the whole transient dedupe state for an outer owner to restore.

    Outer transaction owners (cast settlement, combat-session rounds) wrap
    ``resolve()`` in their own ``transaction.atomic()``: when that OUTER
    transaction rolls back, the resolve-level ``release_practice_claims``
    never runs (the inner commit succeeded), yet the practice XP the claims
    recorded is gone with the rollback. Such owners snapshot the state before
    opening their transaction and restore it in their compensation path —
    the transient analogue of the attribute-surface snapshots they already
    take.
    """
    return _dedupe_tick, frozenset(_dedupe_seen)


def restore_practice_dedupe(
    snapshot: tuple[int | None, frozenset]
) -> None:
    """Reinstall a :func:`snapshot_practice_dedupe` snapshot verbatim."""
    global _dedupe_tick
    _dedupe_tick, seen = snapshot
    _dedupe_seen.clear()
    _dedupe_seen.update(seen)


def _practice_growth_factors(entity: Any, skill: SkillDef) -> float:
    """Return the shared growth-factor composite for one skill's practice.

    Race ``learning_multiplier`` x element-affinity multiplier (``1.0`` for a
    physical or non-elemental skill) x ``growth_rate_multiplier(entity)``
    (the conferred-buff pull path). One formula, two entry points: the
    per-use grant and the booked-hourly settlement both scale their base
    amount by this composite, so learning, affinity, and buff growth can
    never diverge between them. Every factor is a finite, non-negative
    query; the composite is validated before any caller writes it.
    """
    from world.rules.buffs import growth_rate_multiplier

    element_factor = (
        element_affinity_multiplier(entity, skill.element.key)
        if _is_elemental_magic(skill)
        else 1.0
    )
    factors = (
        _race_learning_multiplier(entity)
        * element_factor
        * growth_rate_multiplier(entity)
    )
    if not isfinite(factors) or factors < 0:
        raise ValueError(f"practice factors produced an invalid {factors!r}")
    return float(factors)


def practice_xp_amount(entity: Any, skill: SkillDef) -> float:
    """Return the closed-form practice XP one use of ``skill`` is worth.

    ``SKILL_PRACTICE_XP_PER_USE`` scaled by the shared
    :func:`_practice_growth_factors` composite. Reads no school and no magic
    stat.
    """
    amount = SKILL_PRACTICE_XP_PER_USE * _practice_growth_factors(entity, skill)
    if not isfinite(amount) or amount < 0:
        raise ValueError(f"practice XP formula produced an invalid {amount!r}")
    return float(amount)


def unlock_candidates_for(skill_key: str) -> tuple[SkillDef, ...]:
    """Registry definitions of every skill whose edge consumes ``skill_key``.

    The reverse-edge consumers are exactly the skills whose ``can_use_skill``
    verdict a grant to ``skill_key`` could flip; derivation order follows the
    cached consumer tuple, which is deterministic.
    """
    return tuple(
        SKILL_REGISTRY[key]
        for key, _ in prerequisite_consumers(skill_key)
        if key in SKILL_REGISTRY
    )


def unlock_line(skill: SkillDef) -> str:
    """The one Traditional-Chinese line announcing one newly usable skill."""
    prefix = "新法術可用" if skill.category is SkillCategory.ELEMENTAL_MAGIC else "新技能可用"
    return f"{prefix}：{skill.label}"


def grant_skill_practice_xp(
    entity: Any,
    skill_key: str,
    target: Any = None,
    nonlethal: bool = False,
    unlocks_out: list[str] | None = None,
) -> bool:
    """Accrue one use of practice XP; return whether XP was actually claimed.

    The use-driven accrual entry point (DC3). Skips silently — returning
    ``False`` — for an unregistered or PASSIVE skill (nothing uses a passive,
    so it has no practice), for a ``nonlethal``/simulated context (a guild
    examination is a simulation and grants no growth of any kind), and when
    the per-tick dedupe already holds this ``(actor, skill, target)`` triple.
    Otherwise the closed-form amount flows through
    :func:`award_practice_xp`, the only writer, which clamps at the derived
    cap. Reads no school and no magic stat.

    ``unlocks_out`` is an optional caller-owned list sink: when the award
    flips ``can_use_skill`` from false to true for a skill whose prerequisite
    edges consume ``skill_key``, exactly one unlock line (``新法術可用`` /
    ``新技能可用``) is appended per newly usable skill. Detection is derived
    (before/after snapshot of the shared gate, never persisted), happens only
    alongside a live award, and the SINK ITSELF is not a notification — the
    caller owns delivery and must stage the lines only after its transaction
    commits.
    """
    if nonlethal:
        return False
    skill = SKILL_REGISTRY.get(skill_key)
    if skill is None or skill.kind is not SkillKind.ACTIVE:
        return False
    amount = practice_xp_amount(entity, skill)
    if not _claim_practice(entity, skill_key, target):
        return False
    candidates = unlock_candidates_for(skill_key) if unlocks_out is not None else ()
    was_usable = (
        {candidate.key: can_use_skill(entity, candidate) for candidate in candidates}
        if unlocks_out is not None
        else {}
    )
    award_practice_xp(entity, skill_key, amount)
    if unlocks_out is not None:
        for candidate in candidates:
            if not was_usable[candidate.key] and can_use_skill(entity, candidate):
                unlocks_out.append(unlock_line(candidate))
    return True


def grant_study_practice_xp(entity: Any, skill_key: str, hours: int) -> bool:
    """Accrue the closed-form booked-study grant for ``hours`` whole hours.

    The declared-practice settlement entry point (D7):
    ``hours x PRACTICE_XP_PER_STUDY_HOUR x _practice_growth_factors`` — the
    same composite the per-use path scales, one formula, two entry points.
    Returns ``False`` and writes nothing for a non-positive or non-integer
    hour count, or an unregistered/PASSIVE skill (booked practice follows the
    per-use eligibility rule: nothing practises a passive). Storage routes
    ONLY through :func:`award_practice_xp`, so a booked award crossing the
    derived tip cap saturates byte-identically to a per-use award.
    """
    if isinstance(hours, bool) or not isinstance(hours, int):
        raise ValueError(f"study hours must be an int, got {hours!r}")
    if hours <= 0:
        return False
    skill = SKILL_REGISTRY.get(skill_key)
    if skill is None or skill.kind is not SkillKind.ACTIVE:
        return False
    amount = hours * PRACTICE_XP_PER_STUDY_HOUR * _practice_growth_factors(
        entity, skill
    )
    if not isfinite(amount) or amount < 0:
        raise ValueError(f"study XP formula produced an invalid {amount!r}")
    award_practice_xp(entity, skill_key, amount)
    return True


def seed_lineage_proficiency(
    owned_keys: Sequence[str], explicit: dict[str, float] | None = None
) -> dict[str, float]:
    """Return the proficiency map satisfying every edge of the owned skills.

    The import/scene-build auto-seed (DC6): for each owned skill, every
    prerequisite edge whose derived level falls short is seeded to EXACTLY
    ``min_proficiency * SKILL_PROFICIENCY_XP_PER_LEVEL`` — the minimal value
    meeting the threshold, never above. An explicit entry always wins, even
    when it leaves an edge unmet (the record author said what they meant).
    Resolution runs to a fixed point in registry-key order, so a chain of
    owned skills seeds every unsatisfied edge in one pass and the result is
    order-independent and deterministic. Ownership is never invented: an
    unowned prerequisite stays unowned (the use gate still denies it); this
    only writes XP for keys the entity could already have practised.
    """
    explicit_entries = {
        key: float(value)
        for key, value in (explicit or {}).items()
        if key in SKILL_REGISTRY
    }
    stored = dict(explicit_entries)
    explicit_keys = set(explicit_entries)
    owned = set(owned_keys)
    for _ in range(len(owned) + 1):
        changed = False
        for skill_key in sorted(owned):
            skill = SKILL_REGISTRY.get(skill_key)
            if skill is None:
                continue
            for prereq in skill.prerequisites:
                required = prereq.min_proficiency * SKILL_PROFICIENCY_XP_PER_LEVEL
                current = float(stored.get(prereq.skill_key, 0.0))
                if current >= required:
                    continue
                if prereq.skill_key in explicit_keys:
                    # Explicit and below the edge: the record wins; no override.
                    continue
                # A previously seeded value may be RAISED to a tighter edge
                # (max over edges), but only to that edge's exact value.
                stored[prereq.skill_key] = max(current, required)
                changed = True
        if not changed:
            break
    return stored


def lineage_ownership_closure(
    declared_keys: Sequence[str],
) -> tuple[list[str], list[str]]:
    """Return ``(active_additions, passive_additions)`` closing the lineage.

    A record or NPC that owns a deep skill but not its prerequisite chain is
    unusable under the single gate (the gate requires prerequisite
    OWNERSHIP), so import auto-seed also extends ownership transitively:
    every prerequisite of every owned skill (walking its own prerequisites)
    joins the entity's skill lists. Returned in sorted registry-key order for
    deterministic storage; only keys absent from ``declared_keys`` are
    returned, split by each skill's declared kind.
    """
    declared = set(declared_keys)
    frontier = list(declared)
    seen = set(declared)
    additions: set[str] = set()
    while frontier:
        skill_key = frontier.pop()
        skill = SKILL_REGISTRY.get(skill_key)
        if skill is None:
            continue
        for prereq in skill.prerequisites:
            if prereq.skill_key in seen:
                continue
            seen.add(prereq.skill_key)
            additions.add(prereq.skill_key)
            frontier.append(prereq.skill_key)
    active = sorted(
        key
        for key in additions
        if SKILL_REGISTRY[key].kind is SkillKind.ACTIVE
    )
    passive = sorted(key for key in additions if key not in set(active))
    return active, passive


def apply_lineage_auto_seed(entity: Any) -> None:
    """Seed one freshly-built entity's lineage (ownership + exact XP).

    The ONE auto-seed writer shared by the import loader and the scene
    builder: extends ``db.skills`` with the prerequisite-ownership closure,
    then stores the fixed-point seeded proficiency map (explicit stored
    entries win). Called inside the caller's all-or-nothing transaction, so
    a rejected import leaves nothing behind, seed included.
    """
    raw = entity.db.skills or {}
    active = list(raw.get("active", []))
    passive = list(raw.get("passive", []))
    add_active, add_passive = lineage_ownership_closure([*active, *passive])
    if add_active or add_passive:
        entity.db.skills = {
            "active": [*active, *add_active],
            "passive": [*passive, *add_passive],
        }
    entity.db.skill_proficiency = seed_lineage_proficiency(
        [*active, *add_active, *passive, *add_passive],
        entity.db.skill_proficiency,
    )


def normalize_lineage_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return one import record with its lineage auto-seed applied.

    The shared normalization the validator and the loader BOTH apply before
    any range validation: a copy whose ``skills``/``passives`` close over the
    prerequisite chain and whose ``skill_proficiency`` carries the exact
    seeded values (explicit entries win, merged records are order-independent
    and idempotent). Validating the NORMALIZED record is what makes a deep
    import provably usable while a malformed sibling field still rejects the
    whole record. Unknown skill keys pass through untouched so the existing
    semantic check keeps naming them.
    """
    normalized = dict(record)
    active = list(record.get("skills") or [])
    passive = list(record.get("passives") or [])
    add_active, add_passive = lineage_ownership_closure([*active, *passive])
    merged = seed_lineage_proficiency(
        [*active, *add_active, *passive, *add_passive],
        record.get("skill_proficiency") or {},
    )
    normalized["skills"] = [*active, *add_active]
    normalized["passives"] = [*passive, *add_passive]
    if merged:
        normalized["skill_proficiency"] = merged
    return normalized
