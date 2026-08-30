"""BuffHandler integration for design sections 5.2 and 6.4."""

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import yaml
from evennia.contrib.rpg.buffs import BaseBuff

from world.rules.traits import GAUGE_KEYS


@dataclass(frozen=True)
class BuffDefinition:
    """Validated setting data for one logical buff."""

    key: str
    duration: int | None
    tick_interval: int | None
    stacking: str
    modifiers: dict[str, Any]
    polarity: str = "buff"


@dataclass(frozen=True)
class TickRecord:
    """One damaging rate tick that actually fired, with attribution data.

    ``hp_before`` is the entity's HP immediately before this tick applied, so
    the combat upkeep settlement can detect the lethal crossing
    deterministically after the fact.
    """

    definition_key: str
    source_pk: int | None
    delta: int
    hp_before: float


def load_buff_definitions(path: Path) -> dict[str, BuffDefinition]:
    """Load uniquely keyed buff definitions from YAML."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected a YAML list")
    definitions: dict[str, BuffDefinition] = {}
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict) or not entry.get("key"):
            raise ValueError(f"{path}: entry {position} is missing key")
        key = entry["key"]
        if key in definitions:
            raise ValueError(f"{path}: duplicate buff key {key!r}")
        modifiers = entry.get("modifiers", {})
        if not isinstance(modifiers, dict) or set(modifiers) - {"rate", "bounds", "decay"}:
            raise ValueError(f"{path}: buff {key!r} has invalid modifiers")
        rate = modifiers.get("rate")
        if rate is not None:
            if not isinstance(rate, dict) or "target" not in rate:
                raise ValueError(f"{path}: buff {key!r} rate modifier must be a mapping with a target")
            if rate["target"] not in GAUGE_KEYS and rate["target"] != "skill_practice":
                raise ValueError(
                    f"{path}: buff {key!r} rate target {rate['target']!r} is not "
                    "a gauge key or the pull-only 'skill_practice' target "
                    "(the retired 'magic_level_growth' target is rejected here)"
                )
        stacking = entry.get("stacking", "refresh")
        if stacking not in {"refresh", "unique_per_source"}:
            raise ValueError(f"{path}: buff {key!r} has unsupported stacking {stacking!r}")
        polarity = entry.get("polarity", "buff")
        if polarity not in {"buff", "debuff"}:
            raise ValueError(f"{path}: buff {key!r} has unsupported polarity {polarity!r}")
        definitions[key] = BuffDefinition(
            key=key,
            duration=entry.get("duration"),
            tick_interval=entry.get("tick_interval"),
            stacking=stacking,
            modifiers=dict(modifiers),
            polarity=polarity,
        )
    return definitions


BUFF_DEFINITIONS = load_buff_definitions(
    Path(__file__).parent / "rulebook" / "buffs.yaml"
)
BLOCKING_BUFF_KEYS = frozenset({"paralysis"})
_NO_OP_RATE_TARGETS = frozenset({"skill_practice"})


class RulebookBuff(BaseBuff):
    """One generic buff class parameterized by persistent definition data."""

    key = "rulebook"
    duration = -1
    tickrate = 0
    refresh = True
    unique = True

    def at_tick(self, initial: bool = False, *args, **kwargs) -> None:
        """Apply this definition's rate modifier when explicitly ticked."""
        rate = BUFF_DEFINITIONS[self.definition_key].modifiers.get("rate")
        if rate:
            _apply_rate_modifier(self.owner, rate)


def _is_damaging_rate(rate: dict[str, Any] | None) -> bool:
    """Return whether one rate modifier damages HP (negative delta)."""
    if not isinstance(rate, dict):
        return False
    return (
        rate.get("target") == "hp"
        and isinstance(rate.get("delta"), (int, float))
        and not isinstance(rate.get("delta"), bool)
        and rate["delta"] < 0
    )


def _apply_rate_modifier(entity, rate_mod: dict[str, Any]) -> None:
    """Apply one rate tick.

    ``skill_practice`` (the ``conferred_growth_rate`` buff's declared rate
    target) intentionally does nothing here: change 11b's
    ``growth_rate_multiplier(entity)`` reads it by pull at the moment
    progression is computed. Applying it on tick as well would double-apply
    the conferred scale.
    """
    target = rate_mod["target"]
    if target in _NO_OP_RATE_TARGETS:
        return
    if target not in GAUGE_KEYS:
        raise NotImplementedError(
            f"buff rate target {target!r} belongs to its owning future change"
        )
    trait = getattr(entity.traits, target)
    trait.current = trait.current + rate_mod["delta"]


def _add_buff(
    entity, definition_key: str, *, instance_key: str | None = None, **data
) -> None:
    from world.rules.equipment_effects import equipment_immune_buff_keys

    definition = BUFF_DEFINITIONS[definition_key]
    if (
        definition.polarity == "debuff"
        and definition_key in equipment_immune_buff_keys(entity)
    ):
        # Defense-in-depth no-write backstop (P3 D1): the action workflow
        # already stages a visible neutralization event before this point;
        # this gate refuses the write for any direct caller so an immune
        # debuff can never silently half-apply. Grant-time-only semantics:
        # already-applied debuffs are untouched. The import is function-local
        # because ``equipment_effects`` imports this module at module level.
        return
    if definition.stacking == "unique_per_source" and "source_key" not in data:
        raise ValueError(f"buff {definition_key!r} requires source_key")
    cache = {
        "definition_key": definition_key,
        "tick_interval": definition.tick_interval,
        "remaining_seconds": definition.duration,
        "tick_elapsed_seconds": 0,
        **data,
    }
    entity.buffs.add(
        RulebookBuff,
        key=instance_key or definition_key,
        duration=-1,
        to_cache=cache,
    )


def entity_active_buffs(entity) -> set[str]:
    """Return logical definition keys for every active buff instance."""
    return {buff.definition_key for buff in _active_buff_instances(entity)}


def active_buff_keys_from_storage(entity) -> set[str]:
    """Return active definition keys from stored buff cache without a handler.

    Presentation and preview paths must never materialize ``entity.buffs``.
    This read-only accessor mirrors :func:`entity_active_buffs` against the
    persisted buff attribute, skipping paused, zero-stack, and expired entries.
    """
    from collections.abc import Mapping

    cache = entity.attributes.get("buffs", default={})
    if cache is None:
        return set()
    if not isinstance(cache, Mapping):
        raise TypeError("buff cache storage is malformed")
    active: set[str] = set()
    for buff_cache in cache.values():
        if not isinstance(buff_cache, Mapping):
            raise TypeError("buff cache entry is malformed")
        if buff_cache.get("paused"):
            continue
        stacks = buff_cache.get("stacks")
        if not isinstance(stacks, int) or stacks <= 0:
            continue
        remaining = buff_cache.get("remaining_seconds")
        if isinstance(remaining, int) and remaining <= 0:
            continue
        definition_key = buff_cache.get("definition_key")
        if isinstance(definition_key, str):
            active.add(definition_key)
    return active


def _active_buff_instances(entity) -> tuple[RulebookBuff, ...]:
    """Return unpaused game-time-unexpired buff instances with positive stacks."""
    return tuple(
        buff
        for buff in entity.buffs.all.values()
        if not buff.paused
        and buff.stacks > 0
        and (
            getattr(buff, "remaining_seconds", None) is None
            or buff.remaining_seconds > 0
        )
    )


def blocks_action(entity) -> bool:
    """Report whether a marker buff forbids action, without resolving one."""
    return bool(entity_active_buffs(entity) & BLOCKING_BUFF_KEYS)


def grant_conferred_growth_rate(entity, source_key: str, scale: float) -> None:
    """Persist an unconditional source-qualified growth-rate conferral."""
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        raise ValueError("growth-rate scale must be a finite non-negative number")
    if not isfinite(scale) or scale < 0:
        raise ValueError("growth-rate scale must be a finite non-negative number")
    _add_buff(
        entity,
        "conferred_growth_rate",
        instance_key=f"conferred_growth_rate:{source_key}",
        source_key=source_key,
        scale=float(scale),
    )


def growth_rate_multiplier(entity) -> float:
    """Return the product of all active conferred growth-rate scales."""
    multiplier = 1.0
    for buff in _active_buff_instances(entity):
        if buff.definition_key == "conferred_growth_rate":
            multiplier *= buff.scale
    return multiplier


def _remove_buff_keys(entity, keys: tuple[str, ...]) -> None:
    """Dispel one active buff instance per key; missing keys are no-ops.

    ``dispel=True`` routes the removal through Evennia's external-removal
    hooks (``at_dispel`` then ``at_remove``) rather than the bare remove path:
    a cleanse is a forced external removal, not a natural expiry. ``RulebookBuff``
    defines neither hook today, so this is a recorded semantic contract for
    future buffs that need "cleansed" cleanup.
    """
    for key in keys:
        entity.buffs.remove(key, dispel=True)

def cleanse_debuffs(entity) -> int:
    """Remove every active debuff-polarity buff and return the count removed.

    Reuses the shipped ``cleanse:status`` removal path so holy-water
    settlement and the cleanse effect handler share one semantics. Returns 0
    when nothing is active (and writes nothing).
    """
    debuff_keys = tuple(
        buff.buffkey
        for buff in _active_buff_instances(entity)
        if BUFF_DEFINITIONS[buff.definition_key].polarity == "debuff"
    )
    if debuff_keys:
        _remove_buff_keys(entity, debuff_keys)
    return len(debuff_keys)


def _handle_cleanse(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[Any]:
    """Stage removal of every active debuff-polarity buff on each target.

    ``PendingEffect`` is imported lazily to keep ``world.rules.action``'s
    top-level import of this module from forming an import cycle.
    """
    del actor, context, scale
    scope = effect_id.partition(":")[2]
    if scope != "status":
        raise ValueError(f"cleanse effect must be cleanse:status, got {effect_id!r}")
    from world.rules.action import PendingEffect

    pending: list[Any] = []
    for target in targets:
        debuffs = tuple(
            buff
            for buff in _active_buff_instances(target)
            if BUFF_DEFINITIONS[buff.definition_key].polarity == "debuff"
        )
        if not debuffs:
            continue
        keys = tuple(buff.buffkey for buff in debuffs)
        pending.append(
            PendingEffect(
                entity=target,
                description=f"buffs_cleansed|{target.key}|{len(keys)}",
                surfaces=frozenset(),
                apply=lambda target=target, keys=keys: _remove_buff_keys(
                    target, keys
                ),
            )
        )
    return pending


def tick_buffs(
    entity, elapsed_seconds: int | None = None
) -> tuple[TickRecord, ...]:
    """Settle rulebook buffs from explicit game seconds, never wall time.

    Returns one ordered ``TickRecord`` per damaging rate tick that actually
    fired, in application order. Marker and growth-rate buffs apply as today
    and yield no records; a caller that ignores the return value observes
    exactly the pre-change state changes.

    Even finite rulebook durations use Evennia's non-expiring handler mode;
    ``remaining_seconds`` is the sole authority for expiry.
    """
    if elapsed_seconds is not None and elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative")
    records: list[TickRecord] = []
    for buff in _active_buff_instances(entity):
        interval = getattr(buff, "tick_interval", None)
        elapsed = interval if elapsed_seconds is None else elapsed_seconds
        remaining = getattr(buff, "remaining_seconds", None)
        applied_elapsed = elapsed if remaining is None else min(elapsed, remaining)
        if interval is not None:
            accumulated = buff.tick_elapsed_seconds + applied_elapsed
            while accumulated >= interval:
                rate = BUFF_DEFINITIONS[buff.definition_key].modifiers.get("rate")
                if _is_damaging_rate(rate):
                    records.append(
                        TickRecord(
                            definition_key=buff.definition_key,
                            source_pk=getattr(buff, "source_pk", None),
                            delta=int(rate["delta"]),
                            hp_before=float(entity.traits.hp.current),
                        )
                    )
                buff.at_tick(initial=False)
                accumulated -= interval
            buff.tick_elapsed_seconds = accumulated
        if remaining is not None:
            buff.remaining_seconds = max(0, remaining - elapsed)
    return tuple(records)
