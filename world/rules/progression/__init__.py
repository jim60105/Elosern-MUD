"""Deterministic skill-practice progression and freeform scaling rules.

The single-module surface, split into cohesive modules of one package
(the registry-package precedent applies here):
:mod:`~world.rules.progression._constants` loads ``PROGRESSION_YAML`` and its
derived scalars, :mod:`~world.rules.progression._scales` loads the closed
freeform scale tables, :mod:`~world.rules.progression._gates` owns the ONE use
gate and the tip-cap/proficiency derivation,
:mod:`~world.rules.progression._scaling` owns the affinity and freeform scale
math, :mod:`~world.rules.progression._practice` owns the shared growth-factor
composite, and :mod:`~world.rules.progression._lineage` owns the auto-seed
family.

This package namespace owns the per-tick dedupe state, the digestion-cadence
day claims, and the two practice-grant entry points, so the transient state and
the seams tests patch (``_current_tick``, ``_current_practice_day``) stay in the
one module whose globals the award path actually resolves them through.

Every name resolves through this package's namespace exactly as the single
``world/rules/progression.py`` module exported it: consumers keep importing
``world.rules.progression``. ``PROGRESSION_YAML`` and the derived tables load at
this package's import time, in the original order.
"""

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any

from world.rules.progression._constants import (  # noqa: F401
    AFFINITY_ELEMENT_MULTIPLIER,
    FREEFORM_CAST_SCALE_COUNT,
    NON_AFFINITY_ELEMENT_MULTIPLIER,
    PRACTICE_XP_PER_STUDY_HOUR,
    PROFICIENCY_TIP_CAP,
    PROGRESSION_YAML,
    SKILL_PRACTICE_XP_PER_USE,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
)
from world.rules.progression._gates import (  # noqa: F401
    _race_learning_multiplier,
    award_practice_xp,
    can_use_skill,
    missing_prerequisite,
    proficiency_cap,
    skill_proficiency_level,
    unlock_candidates_for,
    unlock_line,
)
from world.rules.progression._lineage import (  # noqa: F401
    apply_lineage_auto_seed,
    lineage_ownership_closure,
    normalize_lineage_record,
    seed_lineage_proficiency,
)
from world.rules.progression._practice import (  # noqa: F401
    _is_elemental_magic,
    _owned_growth_factor,
    _practice_growth_factors,
    practice_xp_amount,
)
from world.rules.progression._scales import (  # noqa: F401
    FREEFORM_CANONICAL_SCALES,
    FREEFORM_CAST_SCALES,
    FREEFORM_SCALE_LADDER,
    FREEFORM_SCALE_LABELS,
    FREEFORM_SCALE_VALUES,
    _load_freeform_cast_scales,
    _load_freeform_scale_ladder,
)
from world.rules.progression._scaling import (  # noqa: F401
    MAGIC_TIER_THRESHOLDS,
    _affinity_elements,
    _validate_nonnegative_multiplier,
    _validate_scale_inputs,
    element_affinity_multiplier,
    freeform_mastery_entitled,
    freeform_scale_entries_for,
    freeform_scales_for,
    scale_for_label,
    scale_label_for,
    scaled_magnitude,
    scaled_mp_cost,
)

# Byte-identical old-module namespace parity: the single-module history's
# top-level imports are part of its observable surface.
from math import floor  # noqa: F401
from pathlib import Path  # noqa: F401

import yaml  # noqa: F401
from world.lore.elements import ELEMENT_REGISTRY  # noqa: F401
from world.lore.races import RACE_REGISTRY  # noqa: F401
from world.skills.cost_tiers import is_freeform_eligible  # noqa: F401
from world.skills.effects import DamageEffect, GrowthRateEffect  # noqa: F401
from world.skills.registry import (  # noqa: F401
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    prerequisite_consumers,
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


# Digestion-cadence day claims (divine-mystery design §3): for ACTIVE skills
# in ``SkillCategory.DIVINE_MYSTERY`` one practice accrual per actor per skill
# per world-calendar day. The day identity is a monotonic absolute ordinal
# derived from the world clock's own calendar, persisted on the actor as
# ``entity.db.skill_practice_day`` ({skill_key: day_ordinal}) so a reload does
# not reset the brake and a rolled-back commit restores it with the
# proficiency it guards.


def practice_day_ordinal(calendar: "WorldDateTime") -> int:
    """Return the absolute world-calendar day ordinal of one calendar instant.

    The digestion-cadence day identity (divine-mystery §3): strictly
    monotonic over ``WorldDateTime``'s calendar fields, with the ring size
    taken from the world clock's own ``clock.yaml`` constants
    (``days_per_season`` x ``seasons_per_year``) — the derivation reads the
    rulebook, never a literal and never wall-clock time. Two instants share
    an ordinal exactly when they fall on the same world-calendar day, so the
    ordinal stays correct if tick length is ever retuned.
    """
    from world.rules.clock import CLOCK_YAML

    days_per_year = (
        CLOCK_YAML["days_per_season"] * CLOCK_YAML["seasons_per_year"]
    )
    return (
        calendar.year * days_per_year
        + calendar.season_index * CLOCK_YAML["days_per_season"]
        + calendar.day_in_season
        - 1
    )


def _current_practice_day() -> int:
    """Return the current world-calendar day ordinal, or 0 with no clock yet.

    Read through ``read_world_clock()`` with a deferred import, the same
    discipline as :func:`_current_tick`: a pure/unit context (no persisted
    singleton) still gets the zero-day bucket without creating one.
    """
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return practice_day_ordinal(clock.calendar) if clock is not None else 0


def _practice_day_claims(entity: Any) -> dict[str, int]:
    """Return the actor's persisted ``{skill_key: day_ordinal}`` claim map.

    Read pair of the digestion-cadence store: a missing or empty
    ``entity.db.skill_practice_day`` reads as an empty map, so any actor that
    never accrued a divine-mystery skill (or a stub without the attribute)
    is unclaimed.
    """
    raw = getattr(entity.db, "skill_practice_day", None)
    return dict(raw) if isinstance(raw, Mapping) else {}


def _mark_practice_day(entity: Any, skill_key: str, day: int) -> None:
    """Persist today's claim for one skill (write pair of the store).

    Called only on the award path of a use that passes the claim gates: a
    refused award (day-blocked or tick-blocked) never consumes the day. The
    accepted D5 saturation case still claims, since a cancelled-by-cap award
    is indistinguishable from an award at the cap (the call is made, nothing
    accrues either way). Copy-on-write keeps the stored mapping free of
    aliasing with any reader's copy.
    """
    claims = _practice_day_claims(entity)
    claims[skill_key] = day
    entity.db.skill_practice_day = claims


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
    An ACTIVE skill in ``SkillCategory.DIVINE_MYSTERY`` additionally passes
    the digestion-cadence claim (divine-mystery §3): at most one use-driven
    accrual per actor per skill per world-calendar day. The day gate is
    evaluated BEFORE the per-tick claim, so a day-blocked use occupies no
    tick claim it could not turn into an award, and the day is recorded only
    on the path that actually awards, so a refused award never consumes it.
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

    After the award (and the newly-usable-skill lines), the cross-lineage
    rulebook is evaluated for this ``skill_key``: any rule whose clauses just
    became satisfiable grants its keys immediately, and one announcement line
    per newly granted skill is appended to the same caller-owned sink. The
    grant itself is unconditional — it lands whether or not a sink exists.
    """
    if nonlethal:
        return False
    skill = SKILL_REGISTRY.get(skill_key)
    if skill is None or skill.kind is not SkillKind.ACTIVE:
        return False
    day: int | None = None
    if skill.category is SkillCategory.DIVINE_MYSTERY:
        day = _current_practice_day()
        if _practice_day_claims(entity).get(skill_key) == day:
            return False
    amount = practice_xp_amount(entity, skill)
    if not _claim_practice(entity, skill_key, target):
        return False
    if skill.category is SkillCategory.DIVINE_MYSTERY:
        _mark_practice_day(entity, skill_key, day)
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
    _run_cross_lineage_eval(entity, skill_key, unlocks_out)
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

    The cross-lineage rulebook is evaluated right after the award, exactly as
    on the per-use path, so the two practice entry points cannot diverge at a
    grant boundary. This path carries no announcement sink (the clock
    settlement has none); the grant itself is unconditional.
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
    _run_cross_lineage_eval(entity, skill_key, None)
    return True


def _run_cross_lineage_eval(
    entity: Any, skill_key: str, unlocks_out: list[str] | None
) -> None:
    """Evaluate the cross-lineage rulebook after one practice award (D3).

    Called immediately after :func:`award_practice_xp` on BOTH practice entry
    points, because practice XP is the only quantity any clause reads and
    therefore the only moment a rule can newly become satisfiable. Newly
    granted keys are appended to the entity's stored owned set; when the
    caller supplied the same sink that carries newly-usable-skill lines, one
    announcement line per grant is appended there too (the caller owns
    delivery after its transaction commits).

    Imported lazily so importing ``world.rules.progression`` never pulls in
    the rulebook module: cross_lineage_unlock imports progression at its top,
    so a top-level import here would be a cycle. The module is imported by
    the time the first award runs in any real boot or test collection.
    """
    import world.rules.cross_lineage_unlock as _cross_lineage

    rulebook = _cross_lineage.RULEBOOK
    newly_granted = _cross_lineage.evaluate_cross_lineage_unlocks(
        entity, skill_key, rulebook
    )
    if unlocks_out is not None:
        for grant_key in newly_granted:
            unlocks_out.append(
                _cross_lineage.unlock_line_for_grant(grant_key, rulebook.registry)
            )
