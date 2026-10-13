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
        """The persisted skill record, or the empty baseline.

        The read is store-tolerant: a store object carrying no ``skills``
        attribute at all -- a pure fixture rather than a persisted typeclass --
        reads as no stored skills instead of raising from inside the read.
        """
        raw = getattr(getattr(self.entity, "db", None), "skills", None)
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
        The unlocked set resolves from the entity's lifetime counters, read
        without ever attaching the sexual handler: an already mounted handler
        answers through the duck-typed ``getattr(self.entity, "sexual", None)``
        and an unmounted entity reads the same counters out of storage.
        ``SexualState.__init__`` writes a complete baseline whenever the stored
        records are incomplete, so a decision, preview or status read must
        never touch the property, and the unmaterialized case is the storage
        read with every counter absent, which ``unlocked_act_keys_for`` takes
        as zero. No import from the rules layer is involved.
        """
        base = self.base_owned_keys()
        from world.skills.sexual_acts import unlocked_act_keys_for

        return [*base, *sorted(unlocked_act_keys_for(base, self._counter_values()))]

    def _counter_values(self) -> dict[str, int]:
        """Return this entity's lifetime counters without attaching a handler.

        An already mounted handler is read through the duck-typed
        ``getattr(self.entity, "sexual", None)`` -- the live authority for the
        entity's sexual state -- while an unmounted entity falls back to the
        persisted storage read, because reading the ``sexual`` property would
        mount the handler and create its records.
        """
        if "sexual" in getattr(self.entity, "__dict__", {}):
            from world.skills.sexual_acts import gated_counter_keys

            mounted = getattr(self.entity, "sexual", None)
            if mounted is not None:
                return {
                    name: int(getattr(mounted, name))
                    for name in gated_counter_keys()
                }
        return self._stored_counter_values()

    def _stored_counter_values(self) -> dict[str, int]:
        """Return the persisted lifetime counters, handler-free.

        Exactly the counters the catalogue's own unlock maps read, so this
        module needs no vocabulary from the layer that materializes them as
        traits: a counter no act gates on cannot change the unlocked set. Each
        record's ``current`` wins over its ``base``, the same precedence the
        status read model's stored facade applies, so every no-create reader
        agrees; a missing record and a malformed record both read as absent,
        which the unlock rule treats as the zero baseline.
        """
        from collections.abc import Mapping

        from world.skills.sexual_acts import gated_counter_keys

        attributes = getattr(self.entity, "attributes", None)
        if attributes is None:
            return {}
        records = attributes.get(
            "sexual_traits", default=None, category="traits"
        )
        if not isinstance(records, Mapping):
            return {}
        values: dict[str, int] = {}
        for name in gated_counter_keys():
            record = records.get(name)
            if not isinstance(record, Mapping):
                continue
            value = record.get("current", record.get("base"))
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            values[name] = int(value)
        return values

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
        """Return explicitly recorded partial skill grants.

        Store-tolerant like :attr:`_raw`: a store carrying no ``skill_grants``
        attribute reads as no grants rather than raising.
        """
        grants = getattr(getattr(self.entity, "db", None), "skill_grants", None)
        return list(grants or [])


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
