"""Pure helpers and balance data for the sexual-act effect handlers.

A catalog act's ``pleasure:``/``sexual_counter:`` effect strings resolve
through ``world/rules/action.py``'s registered handlers, which delegate every
derivation here: which body part a participant resolves to (monsters collapse
to the generic channel), who participates in a cast, the scaled pleasure gain
formula, and the explicit counter-name-to-mutator table. This module owns the
two new balance tables (the participant-count multiplier ladder and the
climax-extension threshold) in ``rulebook/sexual_act_effects.yaml``; it reads
``PLEASURE_CONFIG``'s sensitivity/shame tables from ``sexual_state.py``
read-only, exactly as the shipped ``pleasure-gauge`` change declared them.

``sexual_state.py`` never imports this module, so the top-level
``PLEASURE_CONFIG`` import here is cycle-free — unlike the ``Monster`` import
in :func:`resolve_part`, which stays deferred inside the function body to
match ``SexualState.__init__``'s existing ``typeclasses``↔``world.rules``
deferral discipline.
"""

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Mapping

import yaml

from world.lore.sex import DEFAULT_SEX, SEX_VALUES
from world.lore.sexual_vocab import GENERIC_BODY_PART, SENSITIVITY_LEVELS
from world.rules.sexual_state import PLEASURE_CONFIG

_RULEBOOK = Path(__file__).with_name("rulebook") / "sexual_act_effects.yaml"
_PARTICIPANT_KEYS = ("1", "2", "3+")


class EffectsConfigError(ValueError):
    """The sexual_act_effects.yaml rulebook violates the canonical contract."""


@dataclass(frozen=True)
class EffectsConfig:
    """The validated participant-count ladder and extension threshold."""

    participant_multipliers: Mapping[str, float]
    climax_extension_threshold: int

    def participant_multiplier(self, participant_count: int) -> float:
        """Resolve one participant count to its crowd multiplier.

        Counts of one and two read the ``"1"``/``"2"`` tiers verbatim; every
        larger count falls into the ``"3+"`` bucket, matching the ladder's
        three-tier shape. A non-positive or non-integer count is a caller
        bug and raises.
        """
        if isinstance(participant_count, bool) or not isinstance(
            participant_count, int
        ) or participant_count < 1:
            raise ValueError(
                f"participant_count must be a positive integer, got "
                f"{participant_count!r}"
            )
        if participant_count == 1:
            return self.participant_multipliers["1"]
        if participant_count == 2:
            return self.participant_multipliers["2"]
        return self.participant_multipliers["3+"]


def _error(message: str) -> EffectsConfigError:
    return EffectsConfigError(f"sexual_act_effects.yaml: {message}")


def _require_multiplier(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error(f"{field} must be a positive number")
    if not isfinite(value) or value <= 0:
        raise _error(f"{field} must be a finite positive number")
    return float(value)


def load_effects_config(path: Path | None = None) -> EffectsConfig:
    """Load and validate the act-effects rulebook, failing closed on deviation.

    ``path`` overrides the canonical rulebook location so tests can exercise
    deviant tables through a temporary copy, keeping the shared source file
    untouched (the same override discipline ``load_pleasure_config`` and
    ``load_config`` follow). Validation rejects unknown or missing top-level
    fields, a ``participant_multipliers`` table that is not exactly the three
    canonical keys with finite positive values in non-descending order, and a
    non-positive ``climax_extension_threshold``.
    """
    rulebook = _RULEBOOK if path is None else path
    raw = yaml.safe_load(rulebook.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise _error("rulebook must be a mapping")
    raw = dict(raw)
    unknown = set(raw) - {"participant_multipliers", "climax_extension_threshold"}
    if unknown:
        raise _error(f"unknown top-level fields {sorted(unknown)}")
    missing = {"participant_multipliers", "climax_extension_threshold"} - set(raw)
    if missing:
        raise _error(f"missing top-level fields {sorted(missing)}")

    multipliers_raw = raw["participant_multipliers"]
    if not isinstance(multipliers_raw, Mapping):
        raise _error("participant_multipliers must be a mapping")
    multipliers_raw = dict(multipliers_raw)
    if set(multipliers_raw) != set(_PARTICIPANT_KEYS):
        raise _error(
            f"participant_multipliers must carry exactly the keys "
            f"{list(_PARTICIPANT_KEYS)}, got {sorted(multipliers_raw)}"
        )
    multipliers = {
        key: _require_multiplier(multipliers_raw[key], f"participant_multipliers.{key}")
        for key in _PARTICIPANT_KEYS
    }
    values = [multipliers[key] for key in _PARTICIPANT_KEYS]
    if any(lower > upper for lower, upper in zip(values, values[1:])):
        raise _error(
            "participant_multipliers must be in non-descending order "
            f"({list(_PARTICIPANT_KEYS)}), got {values}"
        )

    threshold = raw["climax_extension_threshold"]
    if isinstance(threshold, bool) or not isinstance(threshold, int):
        raise _error("climax_extension_threshold must be an integer")
    if threshold < 1:
        raise _error("climax_extension_threshold must be a positive integer")

    return EffectsConfig(
        participant_multipliers=multipliers,
        climax_extension_threshold=threshold,
    )


_EFFECTS_CONFIG = load_effects_config()


def resolve_part(entity: Any, declared_part: str | None) -> str:
    """Resolve one entity's body part for an act, collapsing to the generic channel.

    ``None`` collapses to ``GENERIC_BODY_PART`` unconditionally — whether the
    ``None`` came from an 異種/神之秘法 act declaring no target part or from a
    would-be monster collapse, the answer is the same constant, so the
    pleasure handler needs no per-line special case. A ``Monster`` collapses
    to ``GENERIC_BODY_PART`` regardless of the declared part (D-8: monsters
    are arbitrarily shaped and have one uniform generic channel). The
    ``Monster`` import stays deferred inside the function body to avoid the
    ``typeclasses``↔``world.rules`` import cycle.
    """
    if declared_part is None:
        return GENERIC_BODY_PART
    from typeclasses.monsters import Monster

    return GENERIC_BODY_PART if isinstance(entity, Monster) else declared_part


def participants(actor: Any, targets: list[Any]) -> list[Any]:
    """Return the actor-first, deduplicated participant list for a cast.

    ``ActionResolver``'s targeting step already resolves a ``SELF``-target
    skill to ``[actor]``, so a solo act's ``targets`` arrives with the actor
    present; the actor is prepended and every other entity kept once, in
    ``targets``' order. Deduplication is by object identity (``id()``), not by
    equality: two distinct entities that happen to compare equal are two
    different participants and both must receive the act's effects.
    """
    result = [actor]
    seen: set[int] = {id(actor)}
    for target in targets:
        if id(target) in seen:
            continue
        seen.add(id(target))
        result.append(target)
    return result


def _sensitivity_level(participant: Any, part: str) -> str:
    """Read one body part's sensitivity level without materializing its trait.

    ``participant.sexual.sensitivity[part]`` would lazily create the trait —
    a storage write — at effect-planning time, before the commit snapshot, so
    a cast rejected after planning would leave the created trait behind and
    break the action workflow's all-or-nothing boundary. ``items()`` surfaces
    only traits that already exist, and a missing trait's canonical default
    is 普通, exactly what the lazy creation would have stored.
    """
    for name, trait in participant.sexual.sensitivity.items():
        if name == part:
            return trait.level
    return SENSITIVITY_LEVELS[0]


def compute_pleasure_gain(
    participant: Any,
    part: str,
    base_pleasure: int,
    ratio: float,
    participant_count: int,
) -> int:
    """Compute one participant's pleasure gain from an act's base magnitude.

    The formula is base × ratio × sensitivity × shame × participant-count.
    The sensitivity and shame multipliers are read from ``PLEASURE_CONFIG``
    (``pleasure-gauge``-owned, read-only) keyed by the participant's current
    sensitivity level for the resolved part and its shame level; the
    participant-count multiplier comes from this module's own validated
    ladder. ``ratio`` is ``1.0`` for every recipient and
    ``act.actor_pleasure_ratio`` for the actor's own entry, so the D-4/D-9
    self-pleasure split lives entirely in the caller's ratio choice.
    """
    sensitivity = PLEASURE_CONFIG.sensitivity_multipliers[
        _sensitivity_level(participant, part)
    ]
    shame = PLEASURE_CONFIG.shame_multipliers[participant.sexual.shame.level]
    crowd = _EFFECTS_CONFIG.participant_multiplier(participant_count)
    return round(base_pleasure * ratio * sensitivity * shame * crowd)


# The eleven lifetime counter attribute names map to their sanctioned
# ``SexualState`` mutators explicitly: the method names do not follow one
# mechanical transform of the attribute names (``masturbation_count`` →
# ``record_masturbation`` drops ``_count`` while ``climax_count`` →
# ``record_climax_count`` keeps it and is deliberately distinct from the
# unrelated ``record_climax()`` daily-counter mutator), so a derived string
# transform would be wrong, and a structural test keeps both sides in lockstep.
_COUNTER_MUTATORS: dict[str, str] = {
    "masturbation_count": "record_masturbation",
    "toy_use_count": "record_toy_use",
    "exposure_act_count": "record_exposure_act",
    "watched_count": "record_watched",
    "duo_act_count": "record_duo_act",
    "group_act_count": "record_group_act",
    "hostile_act_count": "record_hostile_act",
    "restraint_count": "record_restraint",
    "interspecies_act_count": "record_interspecies_act",
    "climax_count": "record_climax_count",
    "climax_extension_count": "record_climax_extension",
}


def mutator_name_for(counter_name: str) -> str:
    """Return the sanctioned ``SexualState`` mutator name for one counter.

    Raises ``ValueError`` for an unrecognized counter name, which the effect
    pipeline converts into a named action rejection — a catalog author's typo
    must fail loudly rather than silently incrementing nothing.
    """
    try:
        return _COUNTER_MUTATORS[counter_name]
    except KeyError as error:
        raise ValueError(f"unknown lifetime counter {counter_name!r}") from error


def _read_sex(entity: Any) -> str:
    """Read one entity's ``sex`` attribute with the unknown-party fallback.

    An absent attribute, an explicit ``None``, and any value outside
    ``SEX_VALUES`` all read as ``DEFAULT_SEX`` (``"other"``) — every
    ``Monster``, which carries the ``LivingEntity`` default, lands in that
    branch, so the D-12 ``other``/unknown case "falls out for free"
    (catalog design D-5), and a corrupted non-string attribute can never
    crash the selector's pair sort.
    """
    value = getattr(entity, "sex", None)
    return value if value in SEX_VALUES else DEFAULT_SEX


def pair_event_name(actor: Any, targets: list[Any], act: Any) -> str | None:
    """Resolve one act's sex-conditional event from its cast participants.

    Builds the sorted two-member sex tuple of ``participants(actor,
    targets)`` (reading each participant's ``sex`` through :func:`_read_sex`)
    and returns the event name of the first ``act.pair_events`` entry whose
    pair equals it, or ``None`` when no entry matches — the D-12 table's
    "either party ``other``/unknown emits nothing" branch. The sort is plain
    ``sorted()`` on the two strings, matching ``_act_family()``'s
    construction-time sorted-pair validation, so a declared pair can only
    match casts in the same canonical order. A single-participant surviving
    cast (the one target resisted) never matches a two-member pair and
    therefore emits nothing: a resisted 交合 is no 交合 at all.
    """
    everyone = participants(actor, targets)
    pair = tuple(sorted(_read_sex(entity) for entity in everyone))
    for sex_pair, event_name in act.pair_events:
        if sex_pair == pair:
            return event_name
    return None


__all__ = [
    "EffectsConfig",
    "EffectsConfigError",
    "_COUNTER_MUTATORS",
    "compute_pleasure_gain",
    "load_effects_config",
    "mutator_name_for",
    "pair_event_name",
    "participants",
    "resolve_part",
]
