"""Immutable authored offline persona bundle pools and pure deterministic selector.

Change 10 of the NPC persona authoring suite (design D1-D4). Provides coherent
whole-card offline voices for every role tier and every race without an authored
profile, chosen once by stable identity without rerolling.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from world.lore.npc_card import NpcCard, NpcCardError
from world.lore.npc_profiles.shape import _KEY_RE
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.races import RACE_REGISTRY


@dataclass(frozen=True)
class NpcPersonaBundle:
    """One immutable authored offline persona bundle.

    Holds a stable key, a complete compact NPC character card satisfying the
    card contract, and the race it is written for.
    """

    key: str
    card: NpcCard
    race_key: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not _KEY_RE.match(self.key):
            raise ValueError(
                f"NpcPersonaBundle key {self.key!r} must be a lowercase snake identifier "
                "(1..64 chars, starting with a letter)"
            )
        if not isinstance(self.card, NpcCard):
            raise ValueError(f"NpcPersonaBundle {self.key!r} card must be an NpcCard instance")
        if not isinstance(self.race_key, str) or self.race_key not in RACE_REGISTRY:
            raise ValueError(
                f"NpcPersonaBundle {self.key!r} race_key {self.race_key!r} must be a registered race"
            )


@dataclass(frozen=True)
class NpcBundlePool:
    """One immutable pool of offline persona bundles for a role tier or race."""

    key: str
    race_key: str
    bundles: tuple[NpcPersonaBundle, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not _KEY_RE.match(self.key):
            raise ValueError(
                f"NpcBundlePool key {self.key!r} must be a lowercase snake identifier "
                "(1..64 chars, starting with a letter)"
            )
        if not isinstance(self.race_key, str) or self.race_key not in RACE_REGISTRY:
            raise ValueError(
                f"NpcBundlePool {self.key!r} race_key {self.race_key!r} must be a registered race"
            )
        if not isinstance(self.bundles, tuple):
            object.__setattr__(self, "bundles", tuple(self.bundles))


def _validate_bundle_pools(pools: Mapping[str, NpcBundlePool]) -> None:
    """Validate bundle pools against invariants, tiers, and races.

    Requirements:
    - Every registered NPC role tier (NPC_TIER_REGISTRY) must have a pool matching
      the tier's key and race_key.
    - Every race in RACE_REGISTRY not covered by any tier pool must have a generic
      pool (named f"{race}_generic") matching that race.
    - Every pool key in the mapping must match its pool.key.
    - Every pool must contain at least two bundles.
    - Bundle keys within a pool must be unique.
    - Every bundle's race_key must match its pool's race_key.
    - Every bundle card must round-trip cleanly through NpcCard.from_record(card.to_record())
      (re-raising NpcCardError as ValueError naming pool and bundle).
    - Every bundle card must carry empty hidden identity and social connection.
    - No two bundles in a pool share personality or speech_style text.
    """
    for pool_key, pool in pools.items():
        if pool_key != pool.key:
            raise ValueError(f"Pool key mismatch: mapping key {pool_key!r} != pool.key {pool.key!r}")
        if pool.race_key not in RACE_REGISTRY:
            raise ValueError(
                f"Bundle pool {pool.key!r} has unregistered race_key {pool.race_key!r}"
            )
        if len(pool.bundles) < 2:
            raise ValueError(
                f"Bundle pool {pool.key!r} must contain at least 2 bundles, got {len(pool.bundles)}"
            )

        seen_bundle_keys: set[str] = set()
        seen_personalities: set[str] = set()
        seen_speech_styles: set[str] = set()

        for bundle in pool.bundles:
            if not isinstance(bundle, NpcPersonaBundle):
                raise ValueError(
                    f"Bundle pool {pool.key!r} contains non-NpcPersonaBundle item: {bundle!r}"
                )
            if bundle.key in seen_bundle_keys:
                raise ValueError(
                    f"Bundle pool {pool.key!r} contains duplicate bundle key {bundle.key!r}"
                )
            seen_bundle_keys.add(bundle.key)

            if bundle.race_key != pool.race_key:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} has race {bundle.race_key!r}, "
                    f"expected pool race {pool.race_key!r}"
                )

            # Round-trip card validation to catch budget/leaf errors and name pool + bundle
            try:
                validated_card = NpcCard.from_record(bundle.card.to_record())
            except NpcCardError as err:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} has malformed card: {err}"
                ) from err

            if validated_card.identity.hidden:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} must have empty hidden identity"
                )
            if validated_card.social_connection:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} must have empty social_connection"
                )

            if validated_card.personality in seen_personalities:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} shares duplicate personality "
                    "with another bundle in the same pool"
                )
            seen_personalities.add(validated_card.personality)

            if validated_card.speech_style in seen_speech_styles:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} shares duplicate speech_style "
                    "with another bundle in the same pool"
                )
            seen_speech_styles.add(validated_card.speech_style)

    # Validate tier coverage
    for tier_key, tier in NPC_TIER_REGISTRY.items():
        if tier_key not in pools:
            raise ValueError(f"Missing bundle pool for role tier {tier_key!r}")
        if pools[tier_key].race_key != tier.race_key:
            raise ValueError(
                f"Bundle pool {tier_key!r} race {pools[tier_key].race_key!r} does not match "
                f"tier race {tier.race_key!r}"
            )

    # Validate race coverage: every race in RACE_REGISTRY must have at least one pool
    tier_races = {tier.race_key for tier in NPC_TIER_REGISTRY.values()}
    for race_key in RACE_REGISTRY:
        if race_key not in tier_races:
            generic_pool_key = f"{race_key}_generic"
            if generic_pool_key not in pools:
                raise ValueError(
                    f"Race {race_key!r} has no tier pools and is missing generic pool {generic_pool_key!r}"
                )
            if pools[generic_pool_key].race_key != race_key:
                raise ValueError(
                    f"Generic pool {generic_pool_key!r} race {pools[generic_pool_key].race_key!r} "
                    f"does not match race {race_key!r}"
                )


def offline_pool_for(tier_key: str | None, race_key: str) -> NpcBundlePool:
    """Resolve the offline bundle pool for an NPC.

    Prefers the role tier's pool when registered and bound to the NPC's race;
    otherwise falls back to the race's generic pool:
    - human -> civilian
    - elf -> elven_civilian
    - beastfolk -> beastfolk_generic
    - other -> {race_key}_generic

    Raises:
        ValueError: when race_key is not registered or no pool resolves.
    """
    if race_key not in RACE_REGISTRY:
        raise ValueError(f"Unknown race {race_key!r}")

    if tier_key is not None and tier_key in NPC_TIER_REGISTRY:
        tier = NPC_TIER_REGISTRY[tier_key]
        if tier.race_key == race_key and tier_key in NPC_PERSONA_BUNDLE_POOLS:
            return NPC_PERSONA_BUNDLE_POOLS[tier_key]

    # Generic fallback by race
    if race_key == "human":
        fallback_key = "civilian"
    elif race_key == "elf":
        fallback_key = "elven_civilian"
    else:
        fallback_key = f"{race_key}_generic"

    if fallback_key in NPC_PERSONA_BUNDLE_POOLS:
        return NPC_PERSONA_BUNDLE_POOLS[fallback_key]

    raise ValueError(f"No offline bundle pool resolvable for race {race_key!r}")


def select_offline_bundle(pool_key: str, stable_seed: str | int) -> tuple[str, NpcCard]:
    """Pure, deterministic selection of an offline persona bundle.

    Hashes (pool_key + NUL + stable_seed) with SHA-256 and indexes the pool's
    fixed bundle order. Returns (bundle.key, bundle.card).
    Does not mutate state or perform I/O.

    Raises:
        ValueError: when pool_key is not registered in NPC_PERSONA_BUNDLE_POOLS.
    """
    if pool_key not in NPC_PERSONA_BUNDLE_POOLS:
        raise ValueError(f"Unknown bundle pool {pool_key!r}")

    pool = NPC_PERSONA_BUNDLE_POOLS[pool_key]
    seed_str = str(stable_seed)
    payload = f"{pool_key}\0{seed_str}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    index = int.from_bytes(digest[:8], byteorder="big", signed=False) % len(pool.bundles)
    selected = pool.bundles[index]
    return (selected.key, selected.card)


# Placeholder empty pool mapping for step 1.1 testing, replaced by authored content in step 2.1
NPC_PERSONA_BUNDLE_POOLS: MappingProxyType[str, NpcBundlePool] = MappingProxyType({})
