"""Balance validation, tier labels, affinity math, and freeform scaling.

Runs immediately after the scale tables load (``_scales``), matching the
original single-module import order: the tip-cap check, the fail-closed
multiplier validation, the rank-title tier labels, then the affinity and
scale helpers. ``skill_proficiency_level`` and ``proficiency_cap`` live here
alongside their freeform-ladder consumers (pure defs — their textual move
changes no import-time behavior).
"""

from collections.abc import Sequence
from math import floor, isfinite
from typing import Any

from world.lore.elements import ELEMENT_REGISTRY
from world.skills.cost_tiers import is_freeform_eligible
from world.skills.registry import SkillDef

from ._constants import (
    AFFINITY_ELEMENT_MULTIPLIER,
    NON_AFFINITY_ELEMENT_MULTIPLIER,
)
from ._gates import proficiency_cap, skill_proficiency_level
from ._scales import FREEFORM_CAST_SCALES, FREEFORM_SCALE_LADDER


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
