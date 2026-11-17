"""Pure identity validation shared by creation, draft portraits, and art subjects.

Every creation entry point converges on the same identity rules: an integer
apparent age inside the advertised range, a sex member the race's declaration
permits, a registered race, and a registered subrace that belongs to that race.
This module is the one implementation, so the deterministic creation preflight
(``world.rules.character_creation``), the pending-character draft portrait
request (``world.rules.creation_portrait``) and the draft description input
(``world.art.subjects``) cannot drift apart.

The module is deliberately pure and dependency-narrow: it imports the immutable
lore registries and the race-bounded sex seam only, never the art service, so
the ``world.art.subjects`` import direction stays acyclic. It never writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.lore.sex import SEX_VALUES
from world.rules.identity import IdentityError, resolve_sex

# The single canonical age range every creation entry point advertises and
# enforces (mirrors ``world.rules.creation_wizard`` AGE_MINIMUM/AGE_MAXIMUM).
AGE_MINIMUM = 0
AGE_MAXIMUM = 10000


class CharacterCreationError(ValueError):
    """Raised when a deterministic creation or draft-identity input is invalid.

    Defined here so both the deterministic creation service and the pure
    draft-identity validators raise the SAME type; ``world.rules.character_creation``
    re-exports it, so existing callers and the stable rejection-message mapping
    keep one exception surface.
    """


def validate_age(value: Any, field: str) -> int:
    """Validate one canonical age input as an exact integer in the reasonable range.

    The bounds mirror the creation wizard's advertised presentation constants
    (``AGE_MINIMUM``/``AGE_MAXIMUM``); this validator is the numeric authority
    every creation entry point converges on. Booleans are rejected because
    ``bool`` is an ``int`` subclass.
    """
    if type(value) is not int or not AGE_MINIMUM <= value <= AGE_MAXIMUM:
        raise CharacterCreationError(
            f"{field} must be an integer from {AGE_MINIMUM} to {AGE_MAXIMUM}"
        )
    return value


def validate_sex(value: Any, race_key: str) -> str:
    """Validate the sex channel against the race's declared set.

    Delegates the whole rule to ``world.rules.identity``: an omitted or
    ``None`` sex normalizes to the race-permitted default (``DEFAULT_SEX``
    when the race permits it, otherwise the race's single permitted member),
    and a declared member the race forbids is refused with the same named
    error. The identity seam is the only implementation of the rule; this
    wrapper preserves the player creation error surface.
    """
    try:
        return resolve_sex(race_key, value)
    except IdentityError as error:
        raise CharacterCreationError(str(error)) from error


def require_sex_member(value: Any) -> str:
    """Require one concrete shared-vocabulary sex member (no defaulting).

    The draft-portrait payload always carries a concrete member, so an omitted
    or null value is a rejection rather than the creation form's default.
    Race compatibility is checked afterwards by :func:`validate_sex`.
    """
    if not isinstance(value, str) or value not in SEX_VALUES:
        raise CharacterCreationError("sex must be one of: " + ", ".join(SEX_VALUES))
    return value


def resolve_race_and_subrace(
    race_key: Any, subrace_key: Any
) -> tuple[str, str | None]:
    """Resolve a registered race and an optional registered subrace of that race.

    Every rejection message here is a stable substring the shared rejection
    mapping dispatches on (``unknown race``, ``unknown subrace``,
    ``does not belong to race``).
    """
    if not isinstance(race_key, str):
        raise CharacterCreationError("race must be a registry key")
    if RACE_REGISTRY.get(race_key) is None:
        raise CharacterCreationError(f"unknown race {race_key!r}")
    if subrace_key is None:
        return race_key, None
    if not isinstance(subrace_key, str):
        raise CharacterCreationError("subrace must be a registry key or omitted")
    subrace = SUBRACE_REGISTRY.get(subrace_key)
    if subrace is None:
        raise CharacterCreationError(f"unknown subrace {subrace_key!r}")
    if subrace.race_key != race_key:
        raise CharacterCreationError(
            f"subrace {subrace_key!r} does not belong to race {race_key!r}"
        )
    return race_key, subrace_key


def race_display_label(race_key: Any, subrace_key: Any = None) -> str:
    """The prompt-facing RACE label for one registry identity pair.

    Image backends recognize 人類／獸人／精靈, not authored subrace labels like
    基亞蘭: a registered subrace resolves to its parent race's display name, a
    bare race key resolves directly, and an unregistered key degrades to the
    stored text exactly as the entity-shaped art seam always did.
    """
    if subrace_key:
        subrace = SUBRACE_REGISTRY.get(subrace_key)
        if subrace is not None:
            profile = RACE_REGISTRY.get(subrace.race_key)
            if profile is not None:
                return profile.display_name_zh
    profile = RACE_REGISTRY.get(str(race_key))
    if profile is not None:
        return profile.display_name_zh
    return str(race_key or "unknown race")


@dataclass(frozen=True)
class DraftIdentity:
    """One validated, registry-resolved draft identity snapshot."""

    race: str
    subrace: str
    sex: str
    apparent_age: int

    @property
    def race_label(self) -> str:
        """The prompt-facing parent-race display label."""
        return race_display_label(self.race, self.subrace)


def resolve_draft_identity(
    race: Any, subrace: Any, sex: Any, apparent_age: Any
) -> DraftIdentity:
    """Validate one complete draft identity: race, subrace, sex and apparent age.

    Both registry keys are required (a draft portrait is always submitted from
    a concrete form selection), the subrace must belong to the race, the sex
    must be a concrete member the race permits, and the apparent age is the
    canonical-range integer. No canonical character attribute is read.
    """
    resolved_race, resolved_subrace = resolve_race_and_subrace(race, subrace)
    if resolved_subrace is None:
        raise CharacterCreationError("draft identity requires a registered subrace")
    checked_sex = validate_sex(require_sex_member(sex), resolved_race)
    checked_age = validate_age(apparent_age, "apparent_age")
    return DraftIdentity(resolved_race, resolved_subrace, checked_sex, checked_age)


__all__ = [
    "AGE_MAXIMUM",
    "AGE_MINIMUM",
    "CharacterCreationError",
    "DraftIdentity",
    "race_display_label",
    "require_sex_member",
    "resolve_draft_identity",
    "resolve_race_and_subrace",
    "validate_age",
    "validate_sex",
]
