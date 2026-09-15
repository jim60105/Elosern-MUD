"""Subject-scoped cast-condition metadata for skill definitions.

Declarative metadata only: one frozen value object plus the closed key/field
vocabulary its authoring is validated against. Evaluation lives in
``world/rules/spell_conditions.py`` (which re-exports these names); the
definition side never reaches into the rules package.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

_ALLOWED_CONDITION_KEYS = frozenset({
    "field",
    "gte",
    "equals",
    "buff_active",
    "skill_owned",
    "dual_wielding",
    "equipment_worn",
})

_DISALLOWED_TRANSITION_KEYS = frozenset({
    "event",
    "field_changed",
    "direction",
})

_SUPPORTED_FIELDS = frozenset({
    "arousal",
    "exposure",
    "effective_exposure",
    "climax_phase",
    "wetness",
    "shame",
})


class CastConditionSubject(StrEnum):
    """Subject scope for a cast condition evaluation."""

    ACTOR = "actor"
    EACH_TARGET = "each_target"


@dataclass(frozen=True)
class CastCondition:
    """One subject-scoped condition required to cast a skill."""

    subject: CastConditionSubject
    condition: dict[str, Any]

    def __post_init__(self) -> None:
        if isinstance(self.subject, str):
            try:
                subj = CastConditionSubject(self.subject)
            except ValueError as error:
                raise ValueError(
                    f"invalid CastCondition subject {self.subject!r}; "
                    f"must be one of {list(CastConditionSubject)}"
                ) from error
            object.__setattr__(self, "subject", subj)
        elif not isinstance(self.subject, CastConditionSubject):
            raise ValueError(
                f"CastCondition subject must be a CastConditionSubject, got {self.subject!r}"
            )

        if not isinstance(self.condition, Mapping) or not self.condition:
            raise ValueError(
                f"CastCondition condition must be a non-empty mapping, got {self.condition!r}"
            )

        cond_keys = set(self.condition.keys())
        disallowed = cond_keys & _DISALLOWED_TRANSITION_KEYS
        if disallowed:
            raise ValueError(
                f"CastCondition cannot use transition-only keys: {sorted(disallowed)}"
            )

        unrecognized = cond_keys - _ALLOWED_CONDITION_KEYS
        if unrecognized:
            raise ValueError(
                f"unrecognized CastCondition keys: {sorted(unrecognized)}"
            )

        if "field" in self.condition:
            field = self.condition["field"]
            if field not in _SUPPORTED_FIELDS:
                raise ValueError(
                    f"unsupported CastCondition field {field!r}; "
                    f"must be one of {sorted(_SUPPORTED_FIELDS)}"
                )
            if "equals" not in self.condition and "gte" not in self.condition:
                raise ValueError("field condition requires equals or gte")
        elif "equals" in self.condition or "gte" in self.condition:
            raise ValueError("equals/gte requires field")

        object.__setattr__(self, "condition", dict(self.condition))


__all__ = ["CastCondition", "CastConditionSubject"]
