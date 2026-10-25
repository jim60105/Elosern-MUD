"""Immutable conditions for authored dialogue qualification.

This module defines the frozen condition expression tree and the
``DialogueReferences`` permission catalog used to validate condition operands.
Evaluators do not belong here; runtime evaluation belongs in ``world.rules``.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from world.lore.sexual_vocab import EXPOSURE_LEVELS

REFERENCE_FAMILIES = (
    "profile",
    "preset",
    "daypart",
    "race",
    "social_identity",
    "guild_rank",
    "quest",
    "item",
    "skill",
    "affinity_stage",
)

MAX_CONDITION_CHILDREN = 16
MAX_CONDITION_DEPTH = 4

COMPANION_SOURCE_KINDS = ("preset", "profile", "package_role")
#: The six ``QuestIs`` states. The four stored record states come from
#: ``world.quests.runtime.QuestState``; ``not_accepted`` is the absence of any
#: matching record and ``reward_claimed`` joins a completed record with the
#: authoritative reward-claim ledger.
QUEST_STATES = (
    "not_accepted",
    "in_progress",
    "completed",
    "reward_claimed",
    "failed",
    "invalidated",
)


@dataclass(frozen=True)
class DialogueReferences:
    """Read-only permission catalog for dialogue condition references.

    A mapping from each of the fixed families:
    ``profile``, ``preset``, ``daypart``, ``race``, ``social_identity``,
    ``guild_rank``, ``quest``, ``item``, ``skill``, ``affinity_stage``
    to a read-only ``{safe_key: public_label}`` table.
    """

    tables: MappingProxyType[str, MappingProxyType[str, str]]

    @classmethod
    def empty(cls) -> DialogueReferences:
        """Create an empty reference catalog where every family is an empty table."""
        empty_tables = {family: MappingProxyType({}) for family in REFERENCE_FAMILIES}
        return cls(tables=MappingProxyType(empty_tables))

    def keys_for(self, family: str) -> frozenset[str]:
        """Return the set of valid keys in the specified family."""
        table = self.tables.get(family)
        if table is None:
            return frozenset()
        return frozenset(table.keys())

    def label(self, family: str, key: str) -> str | None:
        """Return the public label for key in family, or None if missing."""
        table = self.tables.get(family)
        if table is None:
            return None
        return table.get(key)

    def child(self, family: str, table: dict[str, str] | MappingProxyType[str, str]) -> DialogueReferences:
        """Return a new frozen instance with the specified family table replaced/updated."""
        if family not in REFERENCE_FAMILIES:
            raise ValueError(f"Unknown reference family {family!r}; expected one of {REFERENCE_FAMILIES}")
        new_tables = dict(self.tables)
        new_tables[family] = MappingProxyType(dict(table))
        return DialogueReferences(tables=MappingProxyType(new_tables))


@dataclass(frozen=True)
class All:
    """Conjunction of 1..16 conditions with max nesting depth 4."""

    children: tuple[Condition, ...]
    kind: Literal["all"] = "all"

    def __post_init__(self) -> None:
        if self.kind != "all":
            raise ValueError("All condition kind must be 'all'")
        if not isinstance(self.children, tuple):
            raise TypeError("All condition children must be a tuple")
        if not (1 <= len(self.children) <= MAX_CONDITION_CHILDREN):
            raise ValueError(
                f"All condition must have 1..{MAX_CONDITION_CHILDREN} children, got {len(self.children)}"
            )


@dataclass(frozen=True)
class Any:
    """Disjunction of 1..16 conditions with max nesting depth 4."""

    children: tuple[Condition, ...]
    kind: Literal["any"] = "any"

    def __post_init__(self) -> None:
        if self.kind != "any":
            raise ValueError("Any condition kind must be 'any'")
        if not isinstance(self.children, tuple):
            raise TypeError("Any condition children must be a tuple")
        if not (1 <= len(self.children) <= MAX_CONDITION_CHILDREN):
            raise ValueError(
                f"Any condition must have 1..{MAX_CONDITION_CHILDREN} children, got {len(self.children)}"
            )


@dataclass(frozen=True)
class RaceIs:
    """Requires actor race to match race_key."""

    race_key: str
    kind: Literal["race_is"] = "race_is"

    def __post_init__(self) -> None:
        if self.kind != "race_is":
            raise ValueError("RaceIs condition kind must be 'race_is'")
        if not isinstance(self.race_key, str) or not self.race_key:
            raise ValueError("RaceIs race_key must be a nonempty string")


@dataclass(frozen=True)
class SocialIdentityIs:
    """Requires actor social identity to match identity_key."""

    identity_key: str
    kind: Literal["social_identity_is"] = "social_identity_is"

    def __post_init__(self) -> None:
        if self.kind != "social_identity_is":
            raise ValueError("SocialIdentityIs condition kind must be 'social_identity_is'")
        if not isinstance(self.identity_key, str) or not self.identity_key:
            raise ValueError("SocialIdentityIs identity_key must be a nonempty string")


@dataclass(frozen=True)
class GuildRankAtLeast:
    """Requires owner guild rank to be at least rank_key."""

    rank_key: str
    kind: Literal["guild_rank_at_least"] = "guild_rank_at_least"

    def __post_init__(self) -> None:
        if self.kind != "guild_rank_at_least":
            raise ValueError("GuildRankAtLeast condition kind must be 'guild_rank_at_least'")
        if not isinstance(self.rank_key, str) or not self.rank_key:
            raise ValueError("GuildRankAtLeast rank_key must be a nonempty string")


@dataclass(frozen=True)
class QuestIs:
    """Requires quest definition_key state to match state."""

    definition_key: str
    state: str
    kind: Literal["quest_is"] = "quest_is"

    def __post_init__(self) -> None:
        if self.kind != "quest_is":
            raise ValueError("QuestIs condition kind must be 'quest_is'")
        if not isinstance(self.definition_key, str) or not self.definition_key:
            raise ValueError("QuestIs definition_key must be a nonempty string")
        if not isinstance(self.state, str) or not self.state:
            raise ValueError("QuestIs state must be a nonempty string")


@dataclass(frozen=True)
class AffinityAtLeast:
    """Requires host-to-owner relationship stage to be at least stage_key."""

    stage_key: str
    kind: Literal["affinity_at_least"] = "affinity_at_least"

    def __post_init__(self) -> None:
        if self.kind != "affinity_at_least":
            raise ValueError("AffinityAtLeast condition kind must be 'affinity_at_least'")
        if not isinstance(self.stage_key, str) or not self.stage_key:
            raise ValueError("AffinityAtLeast stage_key must be a nonempty string")


@dataclass(frozen=True)
class Carries:
    """Requires actor inventory to carry at least minimum items of item_key."""

    item_key: str
    minimum: int = 1
    kind: Literal["carries"] = "carries"

    def __post_init__(self) -> None:
        if self.kind != "carries":
            raise ValueError("Carries condition kind must be 'carries'")
        if not isinstance(self.item_key, str) or not self.item_key:
            raise ValueError("Carries item_key must be a nonempty string")
        if isinstance(self.minimum, bool) or not isinstance(self.minimum, int) or self.minimum < 1:
            raise ValueError("Carries minimum must be an integer >= 1")


@dataclass(frozen=True)
class CompanionPresent:
    """Requires companion of source_kind and source_key to be present."""

    source_kind: str
    source_key: str
    kind: Literal["companion_present"] = "companion_present"

    def __post_init__(self) -> None:
        if self.kind != "companion_present":
            raise ValueError("CompanionPresent condition kind must be 'companion_present'")
        if self.source_kind not in COMPANION_SOURCE_KINDS:
            raise ValueError(
                f"CompanionPresent source_kind must be one of {COMPANION_SOURCE_KINDS}, got {self.source_kind!r}"
            )
        if not isinstance(self.source_key, str) or not self.source_key:
            raise ValueError("CompanionPresent source_key must be a nonempty string")


@dataclass(frozen=True)
class TimePeriod:
    """Requires current cyclic world daypart to fall within [start_daypart, end_daypart)."""

    start_daypart: str
    end_daypart: str
    kind: Literal["time_period"] = "time_period"

    def __post_init__(self) -> None:
        if self.kind != "time_period":
            raise ValueError("TimePeriod condition kind must be 'time_period'")
        if not isinstance(self.start_daypart, str) or not self.start_daypart:
            raise ValueError("TimePeriod start_daypart must be a nonempty string")
        if not isinstance(self.end_daypart, str) or not self.end_daypart:
            raise ValueError("TimePeriod end_daypart must be a nonempty string")
        if self.start_daypart == self.end_daypart:
            raise ValueError("TimePeriod endpoints cannot be equal")


@dataclass(frozen=True)
class SkillOwned:
    """Requires actor to own skill_key with optional minimum proficiency."""

    skill_key: str
    min_proficiency: int | None = None
    kind: Literal["skill_owned"] = "skill_owned"

    def __post_init__(self) -> None:
        if self.kind != "skill_owned":
            raise ValueError("SkillOwned condition kind must be 'skill_owned'")
        if not isinstance(self.skill_key, str) or not self.skill_key:
            raise ValueError("SkillOwned skill_key must be a nonempty string")
        if self.min_proficiency is not None:
            if isinstance(self.min_proficiency, bool) or not isinstance(self.min_proficiency, int) or self.min_proficiency < 0:
                raise ValueError("SkillOwned min_proficiency must be None or an integer >= 0")


@dataclass(frozen=True)
class Exposure:
    """Requires actor effective exposure level to fall within [minimum, maximum]."""

    minimum: int | None = None
    maximum: int | None = None
    kind: Literal["exposure"] = "exposure"

    def __post_init__(self) -> None:
        if self.kind != "exposure":
            raise ValueError("Exposure condition kind must be 'exposure'")
        if self.minimum is None and self.maximum is None:
            raise ValueError("Exposure condition requires at least one of minimum or maximum")
        if self.minimum is not None:
            if isinstance(self.minimum, bool) or not isinstance(self.minimum, int):
                raise TypeError("Exposure minimum must be an integer")
        if self.maximum is not None:
            if isinstance(self.maximum, bool) or not isinstance(self.maximum, int):
                raise TypeError("Exposure maximum must be an integer")
        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ValueError(
                    f"Exposure minimum ({self.minimum}) cannot exceed maximum ({self.maximum})"
                )


Condition = (
    All
    | Any
    | RaceIs
    | SocialIdentityIs
    | GuildRankAtLeast
    | QuestIs
    | AffinityAtLeast
    | Carries
    | CompanionPresent
    | TimePeriod
    | SkillOwned
    | Exposure
)


def condition_depth(condition: Condition) -> int:
    """Return the nesting depth of a condition tree."""
    if isinstance(condition, (All, Any)):
        if not condition.children:
            return 1
        return 1 + max(condition_depth(child) for child in condition.children)
    return 1


def condition_to_dict(condition: Condition) -> dict[str, object]:
    """Serialize a Condition to its canonical wire/payload dictionary form."""
    if isinstance(condition, All):
        return {"kind": "all", "children": [condition_to_dict(c) for c in condition.children]}
    if isinstance(condition, Any):
        return {"kind": "any", "children": [condition_to_dict(c) for c in condition.children]}
    if isinstance(condition, RaceIs):
        return {"kind": "race_is", "race_key": condition.race_key}
    if isinstance(condition, SocialIdentityIs):
        return {"kind": "social_identity_is", "identity_key": condition.identity_key}
    if isinstance(condition, GuildRankAtLeast):
        return {"kind": "guild_rank_at_least", "rank_key": condition.rank_key}
    if isinstance(condition, QuestIs):
        return {"kind": "quest_is", "definition_key": condition.definition_key, "state": condition.state}
    if isinstance(condition, AffinityAtLeast):
        return {"kind": "affinity_at_least", "stage_key": condition.stage_key}
    if isinstance(condition, Carries):
        result: dict[str, object] = {"kind": "carries", "item_key": condition.item_key}
        if condition.minimum != 1:
            result["minimum"] = condition.minimum
        return result
    if isinstance(condition, CompanionPresent):
        return {
            "kind": "companion_present",
            "source_kind": condition.source_kind,
            "source_key": condition.source_key,
        }
    if isinstance(condition, TimePeriod):
        return {
            "kind": "time_period",
            "start_daypart": condition.start_daypart,
            "end_daypart": condition.end_daypart,
        }
    if isinstance(condition, SkillOwned):
        result = {"kind": "skill_owned", "skill_key": condition.skill_key}
        if condition.min_proficiency is not None:
            result["min_proficiency"] = condition.min_proficiency
        return result
    if isinstance(condition, Exposure):
        result = {"kind": "exposure"}
        if condition.minimum is not None:
            result["minimum"] = condition.minimum
        if condition.maximum is not None:
            result["maximum"] = condition.maximum
        return result
    raise TypeError(f"Unknown condition type: {type(condition)!r}")


def validate_condition(
    condition: Condition,
    references: DialogueReferences,
    *,
    depth: int = 1,
    package_roles: frozenset[str] | None = None,
    package_quests: frozenset[str] | None = None,
) -> None:
    """Validate a condition node and its operands against the reference catalog."""
    if depth > MAX_CONDITION_DEPTH:
        raise ValueError(
            f"Condition nesting depth exceeds maximum of {MAX_CONDITION_DEPTH}"
        )

    if isinstance(condition, (All, Any)):
        for child in condition.children:
            validate_condition(
                child,
                references,
                depth=depth + 1,
                package_roles=package_roles,
                package_quests=package_quests,
            )
        return

    # Leaf validations
    if isinstance(condition, RaceIs):
        valid = references.keys_for("race")
        if condition.race_key not in valid:
            raise ValueError(f"Unknown race_key {condition.race_key!r} in RaceIs condition")
        return

    if isinstance(condition, SocialIdentityIs):
        valid = references.keys_for("social_identity")
        if condition.identity_key not in valid:
            raise ValueError(
                f"Unknown identity_key {condition.identity_key!r} in SocialIdentityIs condition"
            )
        return

    if isinstance(condition, GuildRankAtLeast):
        valid = references.keys_for("guild_rank")
        if condition.rank_key not in valid:
            raise ValueError(
                f"Unknown rank_key {condition.rank_key!r} in GuildRankAtLeast condition"
            )
        return

    if isinstance(condition, QuestIs):
        valid = references.keys_for("quest")
        if condition.state not in QUEST_STATES:
            raise ValueError(
                f"Unknown quest state {condition.state!r}; expected one of {QUEST_STATES}"
            )
        is_known = (condition.definition_key in valid) or (
            package_quests is not None and condition.definition_key in package_quests
        )
        if not is_known:
            raise ValueError(
                f"Unknown definition_key {condition.definition_key!r} in QuestIs condition"
            )
        return

    if isinstance(condition, AffinityAtLeast):
        valid = references.keys_for("affinity_stage")
        if condition.stage_key not in valid:
            raise ValueError(
                f"Unknown stage_key {condition.stage_key!r} in AffinityAtLeast condition"
            )
        return

    if isinstance(condition, Carries):
        valid = references.keys_for("item")
        if condition.item_key not in valid:
            raise ValueError(f"Unknown item_key {condition.item_key!r} in Carries condition")
        return

    if isinstance(condition, CompanionPresent):
        if condition.source_kind == "preset":
            valid = references.keys_for("preset")
            if condition.source_key not in valid:
                raise ValueError(
                    f"Unknown preset source_key {condition.source_key!r} in CompanionPresent"
                )
        elif condition.source_kind == "profile":
            valid = references.keys_for("profile")
            if condition.source_key not in valid:
                raise ValueError(
                    f"Unknown profile source_key {condition.source_key!r} in CompanionPresent"
                )
        elif condition.source_kind == "package_role":
            if package_roles is None or condition.source_key not in package_roles:
                raise ValueError(
                    f"Unknown package_role source_key {condition.source_key!r} not in permitted package roles"
                )
        return

    if isinstance(condition, TimePeriod):
        valid = references.keys_for("daypart")
        if condition.start_daypart not in valid:
            raise ValueError(
                f"Unknown start_daypart {condition.start_daypart!r} in TimePeriod condition"
            )
        if condition.end_daypart not in valid:
            raise ValueError(
                f"Unknown end_daypart {condition.end_daypart!r} in TimePeriod condition"
            )
        return

    if isinstance(condition, SkillOwned):
        valid = references.keys_for("skill")
        if condition.skill_key not in valid:
            raise ValueError(
                f"Unknown skill_key {condition.skill_key!r} in SkillOwned condition"
            )
        return

    if isinstance(condition, Exposure):
        for bound_name, bound in (
            ("minimum", condition.minimum),
            ("maximum", condition.maximum),
        ):
            if bound is not None and not 0 <= bound < len(EXPOSURE_LEVELS):
                raise ValueError(
                    f"Exposure {bound_name} {bound} is outside EXPOSURE_LEVELS "
                    f"(0..{len(EXPOSURE_LEVELS) - 1})"
                )
        return

    raise TypeError(f"Unknown condition node: {condition!r}")
