"""Skill handling from design section 5.2 and ``skills-equipment``."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .effects import StatMultiplyEffect
from .registry import SKILL_REGISTRY
from .restrictions import restricted_neutral_value, skill_effect_allowed


# Change 10c/16 grant universal actions that must not depend on imported skill data.
INNATE_SKILL_KEYS: frozenset[str] = frozenset({"flee", "basic_attack"})
# Deterministic append order for the innate set (frozenset iteration order is
# not guaranteed, and combat/report consumers rely on stable ordering).
INNATE_SKILL_ORDER: tuple[str, ...] = ("flee", "basic_attack")
if set(INNATE_SKILL_ORDER) != set(INNATE_SKILL_KEYS):
    raise RuntimeError("INNATE_SKILL_ORDER must name exactly the innate keys")


@dataclass(frozen=True)
class ConferredSkillGrant:
    """A fractional grant of one source entity's continuous-valued skill effect."""

    source_key: str
    skill_key: str
    scale: float


class SkillHandler:
    """Read imported skill ownership and compute transient effective values."""

    def __init__(self, entity: Any):
        self.entity = entity

    @property
    def _raw(self) -> dict[str, list[str]]:
        raw = self.entity.db.skills
        return raw or {"active": [], "passive": []}

    def base_owned_keys(self) -> list[str]:
        """Return active and passive owned skill keys in stored order.

        Exactly what ``owned_keys()`` returned before sexual acts existed;
        the sexual-state mastery check reads this pre-extension set so it
        can never recurse back into ``owned_keys()``.
        """
        return [
            *self._raw.get("active", []),
            *self._raw.get("passive", []),
            *INNATE_SKILL_ORDER,
        ]

    def owned_keys(self) -> list[str]:
        """Return base owned keys plus the entity's unlocked sexual acts.

        Unlocked act keys are appended sorted for deterministic iteration.
        The unlocked set resolves from PERSISTED counter values, so reading
        ownership never mounts the sexual handler: ``SexualState.__init__``
        writes a complete baseline whenever the stored records are
        incomplete, and a no-create consumer must not trigger that write.
        The unmaterialized case is the same read with every counter absent,
        which ``unlocked_act_keys_for`` takes as zero.
        """
        base = self.base_owned_keys()
        from world.skills.sexual_acts import unlocked_act_keys_for

        return [
            *base,
            *sorted(unlocked_act_keys_for(base, self._stored_counter_values())),
        ]

    def _stored_counter_values(self) -> dict[str, int]:
        """Return the persisted lifetime sexual counters, handler-free.

        Counter traits store their value as ``base``; a missing record and a
        malformed record both read as absent, which the unlock rule treats as
        the zero baseline.
        """
        from collections.abc import Mapping

        from world.rules.sexual_state.lifecycle import _LIFETIME_COUNTER_KEYS

        attributes = getattr(self.entity, "attributes", None)
        if attributes is None:
            return {}
        records = attributes.get(
            "sexual_traits", default=None, category="traits"
        )
        if not isinstance(records, Mapping):
            return {}
        values: dict[str, int] = {}
        for name in _LIFETIME_COUNTER_KEYS:
            record = records.get(name)
            if not isinstance(record, Mapping):
                continue
            base = record.get("base")
            if isinstance(base, bool) or not isinstance(base, (int, float)):
                continue
            values[name] = int(base)
        return values

    def _sexual_state_materialized(self) -> bool:
        """Return whether the entity's sexual handler was already mounted.

        The handler's trait storage is created on first mount, so its
        presence is the canonical materialization marker — the same
        attribute the no-create read paths check.
        """
        attributes = getattr(self.entity, "attributes", None)
        if attributes is None:
            return False
        return (
            attributes.get("sexual_traits", default=None, category="traits")
            is not None
        )

    def _unlocked_act_keys_without_sexual(self) -> tuple[str, ...]:
        """Return the unlocked act keys of an unmaterialized entity.

        Pure registry data only: an unmaterialized sexual state means every
        lifetime counter is at zero, which ``unlocked_act_keys_for`` reads
        as the seed acts (or the whole catalogue for a directly owned
        mastery skill) without creating any persistent state.
        """
        from world.skills.sexual_acts import unlocked_act_keys_for

        return tuple(sorted(unlocked_act_keys_for(self.base_owned_keys(), {})))

    def effective_value(self, trait_key: str) -> int:
        """Return a derived multiplied value without mutating stored traits."""
        base = getattr(self.entity.traits, trait_key).value
        return self._effective_value_from_base(trait_key, base)

    def stored_effective_value(self, trait_key: str) -> int:
        """Read the identical static fold without mounting a trait handler."""
        return self.stored_effective_values((trait_key,))[trait_key]

    def stored_effective_values(self, trait_keys: Iterable[str]) -> dict[str, int]:
        """Fold several static traits from ONE persisted-trait storage read.

        A decision projects every effective trait it needs through one call,
        so the persisted ``traits`` attribute is read once instead of once
        per key. Keys absent from storage fold from a zero base, exactly as
        the single-key reader did.
        """
        attributes = getattr(self.entity, "attributes", None)
        traits = (
            attributes.get("traits", default={}, category="traits")
            if attributes is not None
            else {}
        )
        records = traits if isinstance(traits, Mapping) else {}
        values: dict[str, int] = {}
        for trait_key in trait_keys:
            raw = records.get(trait_key) or {}
            base = raw.get(
                "value",
                raw.get(
                    "current", (raw.get("base", 0) + raw.get("mod", 0)) * raw.get("mult", 1)
                ),
            )
            values[trait_key] = self._effective_value_from_base(trait_key, base)
        return values

    def _effective_value_from_base(self, trait_key: str, base: int) -> int:
        """One passive/grant fold shared by live and no-create readers."""
        multiplier = 1.0
        owned = [
            *self._raw.get("active", []),
            *self._raw.get("passive", []),
        ]
        for skill_key in dict.fromkeys(owned):
            if not skill_effect_allowed(self.entity, skill_key):
                continue
            skill = SKILL_REGISTRY.get(skill_key)
            if skill is None:
                continue
            owned_multiplier = _matching_multiplier(skill.parsed_effects, trait_key)
            if owned_multiplier is not None:
                multiplier *= owned_multiplier

        for grant in self.conferred_grants():
            if not skill_effect_allowed(self.entity, grant.skill_key):
                continue
            source_skill = SKILL_REGISTRY.get(grant.skill_key)
            if source_skill is None:
                continue
            source_multiplier = _matching_multiplier(
                source_skill.parsed_effects, trait_key
            )
            if source_multiplier is not None:
                multiplier *= source_multiplier * grant.scale
        return restricted_neutral_value(
            self.entity, trait_key, round(base * multiplier)
        )

    def conferred_grants(self) -> list[ConferredSkillGrant]:
        """Return explicitly recorded partial skill grants."""
        return list(self.entity.db.skill_grants or [])


def _matching_multiplier(
    parsed_effects: tuple, trait_key: str
) -> float | None:
    """Combine stat multipliers in one skill that match a trait."""
    multipliers = [
        effect.multiplier
        for effect in parsed_effects
        if isinstance(effect, StatMultiplyEffect) and effect.trait == trait_key
    ]
    if not multipliers:
        return None
    if len(multipliers) > 1:
        raise ValueError(
            f"skill defines duplicate stat multipliers for trait {trait_key!r}"
        )
    return multipliers[0]
