"""Registered deterministic story-phase predicates (design §6).

Phase selection uses only committed observations resolved by their owning
system; a package declares finite phases whose conditions come from this closed
registry, never an arbitrary expression or generated code. Escort and reunion
observations stay guarded: their owning capability is the second design, so a
package that declares them is rejected here rather than faking the outcome.
"""

from __future__ import annotations

from typing import Any

#: Committed observations this change can select on. ``separation`` and
#: ``unresolved`` describe the pre-acceptance story state; ``closure`` is the
#: supported generic closure fact; ``abandoned`` is the supported unresolved
#: terminal outcome.
REGISTERED_FACTS: frozenset[str] = frozenset(
    {"separation", "closure", "abandoned", "unresolved"}
)

#: Observations owned by the second design (escort/reunion). Declaring one is a
#: named validation failure until that capability lands; the transition boundary
#: never derives them from prose or from a caller-supplied mapping.
GUARDED_FACTS: tuple[str, ...] = (
    "reunion",
    "escort_started",
    "escort_complete",
    "reunion_closure",
)


class PhaseConditionError(ValueError):
    """A phase condition is unknown, guarded, or malformed."""


def validate_condition(condition: Any) -> dict[str, Any]:
    """Normalize one declared condition, or raise :class:`PhaseConditionError`."""
    if not isinstance(condition, dict) or len(condition) != 1:
        raise PhaseConditionError(
            "a phase condition is exactly one {fact: value} or {default: true}"
        )
    if "default" in condition:
        if condition["default"] is not True:
            raise PhaseConditionError("the default condition must be exactly true")
        return {"default": True}
    fact, expected = next(iter(condition.items()))
    if not isinstance(fact, str) or not fact:
        raise PhaseConditionError("a phase condition fact must be a non-empty string")
    if fact in GUARDED_FACTS:
        raise PhaseConditionError(
            f"observation {fact!r} is guarded until escort/reunion mechanics land"
        )
    if fact not in REGISTERED_FACTS:
        raise PhaseConditionError(f"unknown observation fact {fact!r}")
    if not isinstance(expected, bool):
        raise PhaseConditionError(
            f"observation {fact!r} must be compared to a boolean, got {expected!r}"
        )
    return {fact: expected}


def condition_matches(condition: dict[str, Any], observations: dict[str, bool]) -> bool:
    """Whether one normalized condition holds under ``observations``."""
    if condition.get("default"):
        return True
    fact, expected = next(iter(condition.items()))
    return bool(observations.get(fact, False)) is expected


def resolve_observations(observations: Any) -> dict[str, bool]:
    """Validate a caller-supplied observation mapping against the registry.

    The mapping is *not* authority by itself: the owning system resolves the
    committed facts and passes only registered names. Unknown or guarded names
    raise instead of silently selecting a phase.
    """
    if observations is None:
        return {}
    if not isinstance(observations, dict):
        raise PhaseConditionError("observations must be a mapping")
    resolved: dict[str, bool] = {}
    for fact, value in observations.items():
        if fact in GUARDED_FACTS:
            raise PhaseConditionError(
                f"observation {fact!r} is guarded until escort/reunion mechanics land"
            )
        if fact not in REGISTERED_FACTS:
            raise PhaseConditionError(f"unknown observation fact {fact!r}")
        resolved[fact] = bool(value)
    return resolved
