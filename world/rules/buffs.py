"""BuffHandler integration for design sections 5.2 and 6.4."""

from dataclasses import dataclass
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
        stacking = entry.get("stacking", "refresh")
        if stacking not in {"refresh", "unique_per_source"}:
            raise ValueError(f"{path}: buff {key!r} has unsupported stacking {stacking!r}")
        definitions[key] = BuffDefinition(
            key=key,
            duration=entry.get("duration"),
            tick_interval=entry.get("tick_interval"),
            stacking=stacking,
            modifiers=dict(modifiers),
        )
    return definitions


BUFF_DEFINITIONS = load_buff_definitions(
    Path(__file__).parent / "rulebook" / "buffs.yaml"
)
BLOCKING_BUFF_KEYS = frozenset({"paralysis"})
_NO_OP_RATE_TARGETS = frozenset({"magic_level_growth"})


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


def _apply_rate_modifier(entity, rate_mod: dict[str, Any]) -> None:
    """Apply one rate tick.

    ``magic_level_growth`` intentionally does nothing here: change 11b reads it
    by pull through ``growth_rate_multiplier()``. Applying it on tick as well
    would double-apply the conferred scale.
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
    definition = BUFF_DEFINITIONS[definition_key]
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
    _add_buff(
        entity,
        "conferred_growth_rate",
        instance_key=f"conferred_growth_rate:{source_key}",
        source_key=source_key,
        scale=scale,
    )


def growth_rate_multiplier(entity) -> float:
    """Return the product of all active conferred growth-rate scales."""
    multiplier = 1.0
    for buff in _active_buff_instances(entity):
        if buff.definition_key == "conferred_growth_rate":
            multiplier *= buff.scale
    return multiplier


def tick_buffs(entity, elapsed_seconds: int | None = None) -> None:
    """Settle rulebook buffs from explicit game seconds, never wall time.

    Even finite rulebook durations use Evennia's non-expiring handler mode;
    ``remaining_seconds`` is the sole authority for expiry.
    """
    if elapsed_seconds is not None and elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative")
    for buff in _active_buff_instances(entity):
        interval = getattr(buff, "tick_interval", None)
        elapsed = interval if elapsed_seconds is None else elapsed_seconds
        remaining = getattr(buff, "remaining_seconds", None)
        applied_elapsed = elapsed if remaining is None else min(elapsed, remaining)
        if interval is not None:
            accumulated = buff.tick_elapsed_seconds + applied_elapsed
            while accumulated >= interval:
                buff.at_tick(initial=False)
                accumulated -= interval
            buff.tick_elapsed_seconds = accumulated
        if remaining is not None:
            buff.remaining_seconds = max(0, remaining - elapsed)
