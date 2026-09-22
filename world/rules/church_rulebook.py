"""Light Church rulebook slice loader and its two load gates.

``world/rules/rulebook/church.yaml`` is a sectioned rule table parsed through
the shared loader family seam (``rulebook/schema.py::load_sectioned_rules``)
— the same ID-discipline and one-row-one-test correspondence contract as
``combat_modifiers.yaml``, with a ``section`` discriminator instead of a
``when``/``then`` pair. This module validates each section's shape, applies
the two owner-mandated gates at load, and exposes the parsed tuning as an
immutable :class:`ChurchRules` snapshot:

- the **acceptance-curve monotonicity gate**: the NPC-arousal acceptance
  curve must be strictly monotonic from ordinal 0 (owner-pinned 50%) to 100%
  at the top ordinal; any retune that breaks the invariant fails load naming
  the row;
- the **passive-no-negativity polarity gate** (owner's iron rule): no
  PASSIVE redemption-catalogue row may carry any effect negative relative to
  baseline — every trade-off lives in the redemption price, never in the
  effect. The gate also enforces the one-to-one association between each
  PASSIVE catalogue row and its keyed ``passive_effects`` rulebook row, so a
  row appended by a later change (Series A/B/D, order-catalogue's Series C)
  cannot escape classification. Mitigation of an EXISTING penalty counts
  positive (``temple_endurance``-shaped rows reference the closed
  :data:`MITIGATION_TARGETS` set).

No gameplay mechanic consumes these numbers here: the accrual and redemption
changes read this snapshot through the same import.
"""

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from world.lore.church import REDEEM_CATALOG
from world.lore.sexual_vocab import AROUSAL_LEVELS
from world.rules.rulebook.schema import SectionedRule, load_sectioned_rules

_RULEBOOK_PATH = Path(__file__).parent / "rulebook" / "church.yaml"

SECTION_ACCEPTANCE = "acceptance"
SECTION_PRAY = "pray"
SECTION_ACCRUAL = "accrual"
SECTION_OFFERING = "offering"
SECTION_PASSIVE_EFFECTS = "passive_effects"

_SECTIONS = {
    SECTION_ACCEPTANCE,
    SECTION_PRAY,
    SECTION_ACCRUAL,
    SECTION_OFFERING,
    SECTION_PASSIVE_EFFECTS,
}

#: Top acceptance ordinal = the last arousal vocabulary level (高度/極限).
TOP_ORDINAL = len(AROUSAL_LEVELS) - 1
#: Owner-pinned acceptance baseline at ordinal 0 and the top ordinal 100%.
ACCEPT_ORDINAL_0_PERCENT = 50
ACCEPT_TOP_ORDINAL_PERCENT = 100

#: Closed vocabulary of PASSIVE effect fields with a declared positive-only
#: direction. Any effect under any other name is unclassified and rejected —
#: a future passive row must declare its effect in this vocabulary, never in
#: an ad-hoc key that could smuggle a downside (the iron rule is a load
#: contract, not a convention).
_POSITIVE_EFFECT_KEYS = frozenset(
    {"merit_percent", "copper_percent", "multiplier", "mitigation"}
)

#: Closed set of EXISTING rulebook penalties a church PASSIVE may mitigate.
#: The shipped church defence penalty is ``high_exposure_defense_penalty``
#: (``combat_modifiers.yaml``, ``defense: -15``); the design doc's
#: "high-arousal defense penalty" wording refers to this shipped row, whose
#: trigger is exposure-based. A mitigation targeting anything else is
#: unverifiable and rejected — "mitigation of an EXISTING penalty counts
#: positive" means the target must exist.
MITIGATION_TARGETS = frozenset({"high_exposure_defense_penalty"})

_PERCENT_RE = re.compile(r"\+?(\d+)%")


class ChurchRulebookError(ValueError):
    """The church rulebook slice violates a load rule."""


def _error(row_id: str | None, message: str) -> ChurchRulebookError:
    where = f"row {row_id!r}" if row_id else "church.yaml"
    return ChurchRulebookError(f"{where}: {message}")


def _require_int(row_id: str, data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(row_id, f"{key} must be an integer")
    return value


def _require_bool(row_id: str, data: Mapping[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise _error(row_id, f"{key} must be a boolean")
    return value


# --------------------------------------------------------------------------- acceptance


def validate_acceptance_curve(
    rows: Iterable[tuple[int, int, str]],
) -> tuple[tuple[int, int], ...]:
    """Validate one acceptance-curve row set, rejecting it by row id.

    The curve must cover every ordinal ``0..TOP_ORDINAL`` exactly once with
    ordinal 0 pinned at 50% and the top ordinal pinned at 100%, strictly
    monotonic in between (a higher ordinal may never accept less than a
    lower one).
    """
    by_ordinal: dict[int, tuple[int, str]] = {}
    for ordinal, percent, row_id in rows:
        if isinstance(ordinal, bool) or not isinstance(ordinal, int):
            raise _error(row_id, "ordinal must be an integer")
        if isinstance(percent, bool) or not isinstance(percent, int):
            raise _error(row_id, "accept_percent must be an integer")
        if ordinal in by_ordinal:
            raise _error(
                row_id, f"ordinal {ordinal} is authored on more than one row"
            )
        by_ordinal[ordinal] = (percent, row_id)
    expected = set(range(TOP_ORDINAL + 1))
    missing = sorted(expected - set(by_ordinal))
    if missing:
        raise ChurchRulebookError(
            f"acceptance curve is missing the row for ordinal {missing[0]}"
        )
    extra = sorted(set(by_ordinal) - expected)
    if extra:
        raise ChurchRulebookError(
            f"acceptance curve names unknown ordinal {extra[0]} "
            f"(top ordinal is {TOP_ORDINAL})"
        )
    percent_0, row_0 = by_ordinal[0]
    if percent_0 != ACCEPT_ORDINAL_0_PERCENT:
        raise _error(
            row_0,
            f"ordinal 0 must accept {ACCEPT_ORDINAL_0_PERCENT}% "
            f"(a player-facing baseline), got {percent_0}%",
        )
    percent_top, row_top = by_ordinal[TOP_ORDINAL]
    if percent_top != ACCEPT_TOP_ORDINAL_PERCENT:
        raise _error(
            row_top,
            f"top ordinal must accept {ACCEPT_TOP_ORDINAL_PERCENT}%, "
            f"got {percent_top}%",
        )
    previous_percent = percent_0
    for ordinal in range(1, TOP_ORDINAL + 1):
        percent, row_id = by_ordinal[ordinal]
        if percent <= previous_percent:
            raise _error(
                row_id,
                f"acceptance curve is not strictly monotonic: ordinal "
                f"{ordinal} accepts {percent}% but ordinal {ordinal - 1} "
                f"accepts {previous_percent}%",
            )
        previous_percent = percent
    return tuple((ordinal, by_ordinal[ordinal][0]) for ordinal in range(TOP_ORDINAL + 1))


# --------------------------------------------------------------------------- polarity


@dataclass(frozen=True)
class PassiveEffectRow:
    """One keyed PASSIVE effect row of the rulebook slice."""

    row_id: str
    skill_key: str
    effects: dict[str, Any]


def _parse_nonnegative_addition(row_id: str, effect_key: str, value: Any) -> int:
    """Parse an additive effect value: a non-negative int or ``"+N%"`` string."""
    if isinstance(value, bool):
        raise _error(row_id, f"passive effect {effect_key} must be numeric")
    if isinstance(value, int):
        if value < 0:
            raise _error(row_id, f"passive effect {effect_key} is negative")
        return value
    if isinstance(value, str) and (match := _PERCENT_RE.fullmatch(value)):
        parsed = int(match.group(1))
        if parsed < 0:
            raise _error(
                row_id, f"passive effect {effect_key} is negative ({value!r})"
            )
        return parsed
    raise _error(
        row_id,
        f"passive effect {effect_key} must be a non-negative integer or a "
        f'"+N%" percent string, got {value!r}',
    )


def _classify_passive_effects(
    row_id: str, skill_key: str, effects: Mapping[str, Any]
) -> None:
    """Reject any effect negative relative to baseline, naming both keys.

    Recognised fields and their direction:
    - ``merit_percent`` / ``copper_percent``: non-negative additive values.
    - ``multiplier``: a finite number >= 1.0 — a multiplier below 1 (e.g.
      ``0``) removes existing benefit and is a downside by any reading.
    - ``mitigation``: ``{target: <non-negative int | "+N%">}`` where the
      target names an existing rulebook penalty (:data:`MITIGATION_TARGETS`);
      mitigating an EXISTING penalty counts positive. An empty or
      unknown-target mitigation is malformed, not positive.
    Any other effect name is unclassified and rejected: the iron rule is
    fail-closed — an author declaring a new effect surface must extend this
    vocabulary, never slip an effect past it.
    """
    if not isinstance(effects, Mapping) or not effects:
        raise _error(
            row_id,
            f"passive row {skill_key!r} must carry a non-empty effects mapping",
        )
    for effect_key, value in effects.items():
        if effect_key not in _POSITIVE_EFFECT_KEYS:
            raise _error(
                row_id,
                f"passive row {skill_key!r}: effect {effect_key!r} is "
                "unclassified; every church passive effect must be declared "
                f"in {sorted(_POSITIVE_EFFECT_KEYS)}",
            )
        if effect_key in ("merit_percent", "copper_percent"):
            _parse_nonnegative_addition(row_id, f"passive row {skill_key!r} effect {effect_key}", value)
        elif effect_key == "multiplier":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise _error(
                    row_id,
                    f"passive row {skill_key!r}: multiplier must be a number",
                )
            if not math.isfinite(value) or value < 1.0:
                raise _error(
                    row_id,
                    f"passive row {skill_key!r}: multiplier {value} must be "
                    "finite and at least 1.0",
                )
        elif effect_key == "mitigation":
            _validate_mitigation(row_id, skill_key, value)


def _validate_mitigation(row_id: str, skill_key: str, value: Any) -> None:
    if not isinstance(value, Mapping) or not value:
        raise _error(
            row_id,
            f"passive row {skill_key!r}: mitigation must be a "
            "non-empty {target: reduction} mapping",
        )
    for target, reduction in value.items():
        if target not in MITIGATION_TARGETS:
            raise _error(
                row_id,
                f"passive row {skill_key!r}: mitigation target {target!r} "
                "is not an existing penalty in "
                f"{sorted(MITIGATION_TARGETS)}",
            )
        _parse_nonnegative_addition(
            row_id,
            f"passive row {skill_key!r} mitigation",
            reduction,
        )


def validate_passive_polarity(
    catalogue_rows: Iterable[Any],
    effect_rows: Iterable[PassiveEffectRow],
) -> None:
    """Enforce the PASSIVE one-to-one association and the no-negativity gate.

    ``catalogue_rows`` are the shipped ``REDEEM_CATALOG`` rows; ``effect_rows``
    the rulebook's keyed ``passive_effects`` rows. Every PASSIVE catalogue row
    must have exactly one effect row keyed by its skill_key, and every effect
    row must key a PASSIVE catalogue row — an association enforced in both
    directions so an appended Series A/B/D/C row either lands complete or
    fails load. Each PASSIVE effect is then classified; any negative,
    sub-multiplying, unclassified, or non-mitigating effect rejects by name.
    """
    catalogue = list(catalogue_rows)
    effects = list(effect_rows)
    passive_skills = {
        row.skill_key for row in catalogue if getattr(row, "polarity", None) == "passive"
    }
    by_skill: dict[str, list[PassiveEffectRow]] = {}
    for effect in effects:
        by_skill.setdefault(effect.skill_key, []).append(effect)
    duplicate = sorted(
        skill for skill, rows in by_skill.items() if len(rows) > 1
    )
    if duplicate:
        raise ChurchRulebookError(
            f"passive_effects key {duplicate[0]!r} is authored on more than "
            "one row; exactly one keyed effect row per catalogue skill"
        )
    for skill in sorted(by_skill):
        if skill not in passive_skills:
            raise ChurchRulebookError(
                f"passive_effects row {by_skill[skill][0].row_id!r} keys "
                f"{skill!r}, which is not a PASSIVE redemption-catalogue row"
            )
    for skill in sorted(passive_skills):
        if skill not in by_skill:
            raise ChurchRulebookError(
                f"PASSIVE catalogue row {skill!r} has no keyed rulebook "
                "effect row; every PASSIVE effect must be declared in "
                "church.yaml passive_effects"
            )
    for effect in effects:
        _classify_passive_effects(effect.row_id, effect.skill_key, effect.effects)


# --------------------------------------------------------------------------- sections


@dataclass(frozen=True)
class PrayConfig:
    """The pray tuning block (design §4.3 ``pray`` rows)."""

    duration_seconds: int
    merit_per_pray: int
    daily_cap: int


@dataclass(frozen=True)
class OfferingConfig:
    """The offering payout band plus per-row overrides and the enrollment gate."""

    copper_lo: int
    copper_hi: int
    overrides: dict[str, dict[str, int]]
    enrollment_required: bool


@dataclass(frozen=True)
class ChurchRules:
    """The fully validated, immutable church rulebook slice."""

    acceptance: tuple[tuple[int, int], ...]
    pray: PrayConfig
    accrual: dict[str, dict[str, Any]]
    offering: OfferingConfig
    passive_effects: tuple[PassiveEffectRow, ...]


def _validate_pray(rows: list[SectionedRule]) -> PrayConfig:
    if len(rows) != 1 or rows[0].id != "pray":
        raise ChurchRulebookError(
            "church.yaml must author exactly one 'pray' row (id 'pray')"
        )
    row = rows[0]
    duration = _require_int(row.id, row.data, "duration_seconds")
    merit = _require_int(row.id, row.data, "merit_per_pray")
    cap = _require_int(row.id, row.data, "daily_cap")
    if duration < 1:
        raise _error(row.id, "pray duration_seconds must be positive")
    if merit < 1:
        raise _error(row.id, "pray merit_per_pray must be positive")
    if cap < 1:
        raise _error(row.id, "pray daily_cap must be positive")
    return PrayConfig(duration_seconds=duration, merit_per_pray=merit, daily_cap=cap)


_ACCRUAL_FIELDS = frozenset({"merit", "daily_cap", "per_row"})


def _validate_accrual(rows: list[SectionedRule]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        unknown = set(row.data) - _ACCRUAL_FIELDS
        if unknown:
            raise _error(
                row.id, f"accrual row has unknown fields {sorted(unknown)}"
            )
        if not row.data:
            raise _error(row.id, "accrual row must declare merit or per_row")
        entry: dict[str, Any] = {}
        if "merit" in row.data:
            merit = _require_int(row.id, row.data, "merit")
            if merit < 1:
                raise _error(row.id, "accrual merit must be positive")
            entry["merit"] = merit
            if "daily_cap" in row.data:
                cap = _require_int(row.id, row.data, "daily_cap")
                if cap < 1:
                    raise _error(row.id, "accrual daily_cap must be positive")
                entry["daily_cap"] = cap
        if "per_row" in row.data:
            entry["per_row"] = _require_bool(row.id, row.data, "per_row")
        result[row.id] = entry
    return result


def _validate_offering(rows: list[SectionedRule]) -> OfferingConfig:
    by_id = {row.id: row for row in rows}
    missing = {"offering_payout_band", "offering_enrollment_required"} - set(by_id)
    if missing:
        raise ChurchRulebookError(
            f"church.yaml is missing offering rows {sorted(missing)}"
        )
    band = by_id["offering_payout_band"]
    lo = _require_int(band.id, band.data, "copper_lo")
    hi = _require_int(band.id, band.data, "copper_hi")
    if not 0 <= lo <= hi:
        raise _error(
            band.id, "offering payout band must satisfy 0 <= copper_lo <= copper_hi"
        )
    overrides_raw = band.data.get("overrides", {})
    if not isinstance(overrides_raw, Mapping):
        raise _error(band.id, "offering overrides must be a mapping")
    overrides: dict[str, dict[str, int]] = {}
    for key, entry in overrides_raw.items():
        if not isinstance(key, str) or not key:
            raise _error(band.id, "offering override keys must be non-empty strings")
        if not isinstance(entry, Mapping):
            raise _error(band.id, f"offering override {key!r} must be a mapping")
        if set(entry) != {"copper"}:
            raise _error(
                band.id,
                f"offering override {key!r} must declare exactly 'copper'",
            )
        copper = entry["copper"]
        if isinstance(copper, bool) or not isinstance(copper, int) or copper < 0:
            raise _error(
                band.id, f"offering override {key!r} copper must be non-negative int"
            )
        overrides[key] = {"copper": copper}
    gate = by_id["offering_enrollment_required"]
    enrollment_required = _require_bool(
        gate.id, gate.data, "enrollment_required"
    )
    return OfferingConfig(
        copper_lo=lo,
        copper_hi=hi,
        overrides=overrides,
        enrollment_required=enrollment_required,
    )


def _validate_passive_section(rows: list[SectionedRule]) -> tuple[PassiveEffectRow, ...]:
    result: list[PassiveEffectRow] = []
    for row in rows:
        skill_key = row.data.get("skill_key")
        if not isinstance(skill_key, str) or not skill_key:
            raise _error(row.id, "passive_effects row requires a non-empty skill_key")
        effects = row.data.get("effects")
        result.append(PassiveEffectRow(row_id=row.id, skill_key=skill_key, effects=effects))
    return tuple(result)


def load_church_rules(path: Path | None = None) -> ChurchRules:
    """Load, shape-validate, and gate the complete church rulebook slice.

    Any malformed row, unknown section, violated gate, or PASSIVE association
    gap raises :class:`ChurchRulebookError` naming the offending row; nothing
    partial is returned. The polarity gate runs over the shipped
    ``REDEEM_CATALOG`` plus this slice's ``passive_effects`` rows, so the
    shipped (empty) shell passes while every future appended row is bound.
    """
    rulebook_path = _RULEBOOK_PATH if path is None else path
    rows = load_sectioned_rules(rulebook_path)
    by_section: dict[str, list[SectionedRule]] = {}
    for row in rows:
        if row.section not in _SECTIONS:
            raise _error(
                row.id,
                f"unknown section {row.section!r} (expected one of "
                f"{sorted(_SECTIONS)})",
            )
        by_section.setdefault(row.section, []).append(row)

    acceptance_rows: list[tuple[int, int, str]] = []
    for row in by_section.get(SECTION_ACCEPTANCE, []):
        ordinal = _require_int(row.id, row.data, "ordinal")
        percent = _require_int(row.id, row.data, "accept_percent")
        acceptance_rows.append((ordinal, percent, row.id))
    acceptance = validate_acceptance_curve(acceptance_rows)

    pray = _validate_pray(by_section.get(SECTION_PRAY, []))
    accrual = _validate_accrual(by_section.get(SECTION_ACCRUAL, []))
    offering = _validate_offering(by_section.get(SECTION_OFFERING, []))
    passive = _validate_passive_section(by_section.get(SECTION_PASSIVE_EFFECTS, []))

    validate_passive_polarity(REDEEM_CATALOG, passive)
    return ChurchRules(
        acceptance=acceptance,
        pray=pray,
        accrual=accrual,
        offering=offering,
        passive_effects=passive,
    )


# Loaded and fully gated at import (the combat_modifiers.yaml precedent): a
# malformed slice, a broken acceptance curve, or an unclassified PASSIVE
# effect fails process start with the offending row named, never a later
# runtime lookup.
_RULES = load_church_rules()


def get_church_rules() -> ChurchRules:
    """Return the validated church rulebook snapshot loaded at import."""
    return _RULES