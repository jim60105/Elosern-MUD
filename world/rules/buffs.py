"""BuffHandler integration for design sections 5.2 and 6.4."""

from dataclasses import dataclass
from math import floor, isfinite
import re
from pathlib import Path
from typing import Any

import yaml
try:
    from evennia.contrib.rpg.buffs import BaseBuff
except Exception:  # pragma: no cover - fallback when django settings not loaded
    class BaseBuff:  # type: ignore[no-redef]
        pass
from world.rules.quantum import SETTLEMENT_QUANTUM_SECONDS

from world.rules.traits import GAUGE_KEYS

#: The polarity-wide words :func:`remove_by_selector` understands beyond a
#: concrete definition key. Forward-declared seam (design D5): ``positive``
#: and ``all`` ship tested but caller-less until the item-effect change.
_REMOVE_SELECTORS = frozenset({"all", "positive", "negative"})


@dataclass(frozen=True)
class RecoveryRatePolicy:
    """Configured rate-of-change recovery profile for sustained healing.

    A recovery profile restores living recipients per tick using an authored
    base amount, live recipient effective exposure, and snapshotted caster
    heal_gain / optional grace multiplier.
    """

    target: str = "hp"
    base: int = 0
    exposure_percent_per_ordinal: float = 0.1


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
    """Load uniquely keyed buff definitions from YAML.

    A definition key may never collide with a :func:`remove_by_selector`
    selector word — one bare word must never mean both "remove everything of
    this polarity" and "remove this one status" (design Risks).
    """
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
        if key in _REMOVE_SELECTORS:
            raise ValueError(
                f"{path}: buff key {key!r} collides with a remove_by_selector selector"
            )
        modifiers = entry.get("modifiers", {})
        if not isinstance(modifiers, dict) or set(modifiers) - {"rate", "bounds", "decay", "divert"}:
            raise ValueError(f"{path}: buff {key!r} has invalid modifiers")
        rate = modifiers.get("rate")
        if rate is not None:
            if not isinstance(rate, dict):
                raise ValueError(f"{path}: buff {key!r} rate modifier must be a mapping")
            has_delta = "delta" in rate
            has_recovery = "recovery" in rate
            has_scale = "scale_from_source" in rate
            if has_delta and has_recovery:
                raise ValueError(
                    f"{path}: buff {key!r} rate modifier cannot declare both delta and recovery"
                )
            if not has_delta and not has_recovery and not has_scale:
                raise ValueError(
                    f"{path}: buff {key!r} rate modifier must declare either delta or recovery"
                )
            if has_delta:
                delta_val = rate["delta"]
                if rate.get("target") == "mp" and (isinstance(delta_val, bool) or not isinstance(delta_val, int)):
                    raise ValueError(
                        f"{path}: buff {key!r} mp rate delta must be an integer, got {delta_val!r}"
                    )
            if has_recovery:
                rec = rate["recovery"]
                if not isinstance(rec, dict):
                    raise ValueError(f"{path}: buff {key!r} recovery profile must be a mapping")
                resolved_target = rec.get("target", rate.get("target", "hp"))
                if resolved_target != "hp":
                    raise ValueError(f"{path}: buff {key!r} recovery profile target must be 'hp'")
                allowed_rec_keys = {"target", "base", "exposure_percent_per_ordinal"}
                if set(rec) - allowed_rec_keys:
                    raise ValueError(f"{path}: buff {key!r} recovery profile has unknown keys")
                base = rec.get("base")
                if isinstance(base, bool) or not isinstance(base, int) or base < 0:
                    raise ValueError(f"{path}: buff {key!r} recovery base must be a non-negative integer")
                exp_pct = rec.get("exposure_percent_per_ordinal", 0.1)
                if isinstance(exp_pct, bool) or not isinstance(exp_pct, (int, float)) or not isfinite(exp_pct) or exp_pct < 0:
                    raise ValueError(f"{path}: buff {key!r} exposure_percent_per_ordinal must be a finite non-negative number")
                tick_interval = entry.get("tick_interval")
                if isinstance(tick_interval, bool) or not isinstance(tick_interval, int) or tick_interval <= 0:
                    raise ValueError(f"{path}: buff {key!r} with recovery profile requires positive int tick_interval")
                if tick_interval % SETTLEMENT_QUANTUM_SECONDS != 0:
                    raise ValueError(
                        f"{path}: buff {key!r} tick_interval {tick_interval} must be a multiple of "
                        f"settlement quantum {SETTLEMENT_QUANTUM_SECONDS}"
                    )
            elif "target" not in rate:
                raise ValueError(f"{path}: buff {key!r} rate modifier must be a mapping with a target")
            effective_target = resolved_target if has_recovery else rate["target"]
            if effective_target not in GAUGE_KEYS and effective_target != "skill_practice":
                raise ValueError(
                    f"{path}: buff {key!r} rate target {effective_target!r} is not "
                    "a gauge key or the pull-only 'skill_practice' target "
                    "(the retired 'magic_level_growth' target is rejected here)"
                )
            if "caster_share" in rate:
                if has_recovery:
                    raise ValueError(
                        f"{path}: buff {key!r} rate modifier cannot declare both recovery and caster_share"
                    )
                if has_scale:
                    raise ValueError(
                        f"{path}: buff {key!r} rate modifier cannot declare both scale_from_source and caster_share"
                    )
                if not has_delta:
                    raise ValueError(
                        f"{path}: buff {key!r} rate modifier caster_share requires fixed delta"
                    )
                if effective_target != "hp":
                    raise ValueError(
                        f"{path}: buff {key!r} rate modifier caster_share target must be 'hp', got {effective_target!r}"
                    )
                delta_val = rate["delta"]
                if (
                    isinstance(delta_val, bool)
                    or not isinstance(delta_val, (int, float))
                    or not isfinite(delta_val)
                    or delta_val >= 0
                ):
                    raise ValueError(
                        f"{path}: buff {key!r} rate modifier caster_share requires a negative delta, got {delta_val!r}"
                    )
                share_val = rate["caster_share"]
                if (
                    isinstance(share_val, bool)
                    or not isinstance(share_val, (int, float))
                    or not isfinite(share_val)
                    or share_val <= 0
                    or share_val > 1
                ):
                    raise ValueError(
                        f"{path}: buff {key!r} rate modifier caster_share must be a finite number in (0, 1], got {share_val!r}"
                    )
                rate["caster_share"] = float(share_val)
        divert = modifiers.get("divert")
        if divert is not None:
            if not isinstance(divert, dict):
                raise ValueError(f"{path}: buff {key!r} divert modifier must be a mapping")
            allowed_divert_keys = {"target", "fraction", "cap"}
            if set(divert) - allowed_divert_keys or allowed_divert_keys - set(divert):
                raise ValueError(f"{path}: buff {key!r} divert modifier requires exactly keys {sorted(allowed_divert_keys)}")
            target = divert["target"]
            if target not in GAUGE_KEYS:
                raise ValueError(f"{path}: buff {key!r} divert target {target!r} must be a gauge key")
            if target not in ("mp", "hp"):
                raise ValueError(f"{path}: buff {key!r} divert target {target!r} is not supported (must be 'mp' or 'hp')")
            fraction = divert["fraction"]
            if isinstance(fraction, bool) or not isinstance(fraction, (int, float)) or not isfinite(fraction) or fraction <= 0 or fraction > 1:
                raise ValueError(f"{path}: buff {key!r} divert fraction must be a finite number in (0, 1]")
            cap = divert["cap"]
            if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
                raise ValueError(f"{path}: buff {key!r} divert cap must be a positive integer")
            duration = entry.get("duration")
            if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
                raise ValueError(f"{path}: buff {key!r} with divert profile requires a finite positive int duration")
            if rate is not None and isinstance(rate, dict) and "recovery" in rate:
                raise ValueError(f"{path}: buff {key!r} cannot declare both divert and recovery")
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


def get_recovery_policy(definition: BuffDefinition) -> RecoveryRatePolicy | None:
    """Extract the RecoveryRatePolicy from a buff definition if declared."""
    rate = definition.modifiers.get("rate")
    if not isinstance(rate, dict) or "recovery" not in rate:
        return None
    rec = rate["recovery"]
    return RecoveryRatePolicy(
        target=rec.get("target", "hp"),
        base=int(rec["base"]),
        exposure_percent_per_ordinal=float(rec.get("exposure_percent_per_ordinal", 0.1)),
    )


def _parse_percent_value(value: Any) -> float:
    """Parse an int, float, or percent string (e.g. '+10%', '2.5%') to a float percent."""
    if isinstance(value, bool):
        raise ValueError(f"invalid percent value: {value!r}")
    if isinstance(value, (int, float)):
        if not isfinite(value):
            raise ValueError(f"invalid percent value: {value!r}")
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1]
        try:
            parsed = float(cleaned)
            if not isfinite(parsed):
                raise ValueError
            return parsed
        except ValueError:
            raise ValueError(f"invalid percent string: {value!r}")
    raise ValueError(f"invalid percent type: {type(value)}")
    return definitions


def get_divert_consumed(buff: Any) -> int:
    """Return the consumed divert budget for one buff instance."""
    val = getattr(buff, "divert_consumed", None)
    if val is None and hasattr(buff, "cache") and isinstance(buff.cache, dict):
        val = buff.cache.get("divert_consumed")
    if val is None and hasattr(buff, "handler") and hasattr(buff.handler, "buffcache"):
        entry = buff.handler.buffcache.get(getattr(buff, "buffkey", None))
        if isinstance(entry, dict):
            val = entry.get("divert_consumed")
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return 0
    return max(0, int(val))


def update_divert_consumed(buff: Any, consumed: int) -> None:
    """Update the consumed divert budget on a buff instance cache."""
    consumed_int = max(0, int(consumed))
    if hasattr(buff, "cache") and isinstance(buff.cache, dict):
        buff.cache["divert_consumed"] = consumed_int
    if hasattr(buff, "handler") and hasattr(buff.handler, "buffcache"):
        key = getattr(buff, "buffkey", None)
        if key and key in buff.handler.buffcache:
            buff.handler.buffcache[key]["divert_consumed"] = consumed_int
    try:
        setattr(buff, "divert_consumed", consumed_int)
    except Exception:  # observability: ignore R2: optional write-through on foreign test instances
        pass


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
        recovery = get_recovery_policy(BUFF_DEFINITIONS[self.definition_key])
        if rate and recovery is None:
            source_tier = getattr(self, "source_tier", None) or "學徒"
            source_skill = getattr(self, "source_skill", None)
            source_pk = None
            if "caster_share" in rate:
                source_pk = getattr(self, "source_pk", None)
                if source_pk is None and hasattr(self, "cache") and isinstance(self.cache, dict):
                    source_pk = self.cache.get("source_pk")
            _apply_rate_modifier(
                self.owner,
                rate,
                source_tier=source_tier,
                source_skill=source_skill,
                source_pk=source_pk,
            )


def _is_damaging_gauge_rate(rate: dict[str, Any] | None) -> bool:
    """Return whether one rate modifier damages a gauge (HP or MP, negative delta)."""
    if not isinstance(rate, dict):
        return False
    return (
        rate.get("target") in ("hp", "mp")
        and isinstance(rate.get("delta"), (int, float))
        and not isinstance(rate.get("delta"), bool)
        and rate["delta"] < 0
    )


def _is_damaging_rate(rate: dict[str, Any] | None) -> bool:
    """Return whether one rate modifier damages HP (negative delta)."""
    return _is_damaging_gauge_rate(rate) and isinstance(rate, dict) and rate.get("target") == "hp"


def _resolve_source_origin(entity: Any, source_pk: int | None) -> Any | None:
    """Resolve a tick's cached source dbref to a live entity, or ``None``.

    Consults active battlefields first (roster-then-dbref posture matching
    upkeep credit resolver), falling back to ObjectDB.
    """
    if source_pk is None:
        return None
    from world.rules.skip_safety import _active_battlefield_for

    battlefield = _active_battlefield_for(entity)
    if battlefield is not None:
        for member in battlefield.roster.values():
            pk = getattr(member, "pk", None)
            if isinstance(pk, int) and pk == source_pk:
                return member
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(id=source_pk).first()


def _credit_caster_share(origin: Any, amount: int) -> None:
    """Credit HP to a living origin caster, clamped at max HP, without reviving or dispatching."""
    if amount <= 0:
        return
    traits = getattr(origin, "traits", None)
    if traits is None or not hasattr(traits, "hp"):
        return
    from world.rules.action import stored_gauge_pair

    current_hp, max_hp = stored_gauge_pair(origin, "hp")
    if current_hp <= 0:
        return
    new_hp = min(max_hp, current_hp + amount)
    hp_trait = origin.traits.hp
    if hasattr(hp_trait, "current"):
        hp_trait.current = new_hp
    else:
        hp_trait.value = new_hp


def _apply_rate_modifier(
    entity,
    rate_mod: dict[str, Any],
    source_tier: str | None = None,
    source_skill: str | None = None,
    source_pk: int | None = None,
) -> None:
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
    delta = rate_mod["delta"]
    if target == "mp":
        from world.rules.mp_flow import apply_mp_change

        apply_mp_change(
            entity,
            delta,
            source_skill=source_skill,
            source_tier=source_tier,
        )
        return

    trait = getattr(entity.traits, target)
    current = getattr(trait, "current", None)
    if current is not None:
        before = float(current)
        if target == "hp" and before <= 0:
            return
        trait.current = current + delta
        after = float(getattr(trait, "current", 0))
    else:
        before = float(getattr(trait, "value", 0))
        if target == "hp" and before <= 0:
            return
        trait.value = getattr(trait, "value", 0) + delta
        after = float(getattr(trait, "value", 0))

    if target == "hp" and delta < 0:
        actual_loss = max(0, int(before - max(0.0, after)))
        if actual_loss > 0:
            from world.rules.state_reactions import dispatch_outcome_reaction

            tier = source_tier or "學徒"
            dispatch_outcome_reaction(entity, "hp_loss", source_tier=tier)

        caster_share = rate_mod.get("caster_share")
        if caster_share is not None and actual_loss > 0 and source_pk is not None:
            credit = floor(actual_loss * float(caster_share))
            if credit > 0:
                origin = _resolve_source_origin(entity, source_pk)
                if origin is not None:
                    _credit_caster_share(origin, credit)



def _apply_recovery_tick(entity, buff: RulebookBuff, policy: RecoveryRatePolicy) -> None:
    """Execute one sustained recovery tick according to the RecoveryRatePolicy.

    Restores living recipients:
    amount = max(0, floor(base * (1 + 0.1 * exposure_ordinal) * (1 + snapshot_heal_gain / 100) * snapshot_grace_multiplier))
    clamped to living HP gap. Never revives dead recipients.
    """
    trait = getattr(getattr(entity, "traits", None), policy.target, None)
    if trait is None:
        return
    current = getattr(trait, "current", None)
    if current is None:
        current = getattr(trait, "value", None)
    if current is None or current <= 0:
        # Dead recipient or missing HP gauge: never revive or tick
        return

    max_hp = getattr(trait, "max", None)
    if max_hp is None:
        max_hp = getattr(trait, "max_value", None)
    if max_hp is None:
        return

    # Live recipient effective exposure
    from world.rules.equipment_effects import effective_exposure
    from world.rules.sexual_state import EXPOSURE_LEVELS
    from world.rules.stored_sexual_reads import StoredLevel

    exposure = effective_exposure(entity)
    ordinal = 0
    if isinstance(exposure, StoredLevel) and tuple(exposure.levels) == EXPOSURE_LEVELS:
        ordinal = int(exposure.value)
    elif isinstance(exposure, str) and exposure in EXPOSURE_LEVELS:
        ordinal = EXPOSURE_LEVELS.index(exposure)
    elif isinstance(exposure, StoredLevel):
        ordinal = int(exposure.value)

    snap_heal_gain = float(getattr(buff, "snapshot_heal_gain", 0.0) or 0.0)
    snap_grace = float(getattr(buff, "snapshot_grace_multiplier", 1.0) or 1.0)

    exposure_factor = 1.0 + policy.exposure_percent_per_ordinal * ordinal
    heal_gain_factor = 1.0 + (snap_heal_gain / 100.0)
    raw_amount = floor(policy.base * exposure_factor * heal_gain_factor * snap_grace)
    amount = max(0, raw_amount)

    hp_gap = max(0, int(max_hp) - int(current))
    actual_heal = min(amount, hp_gap)
    if actual_heal > 0:
        trait.current = current + actual_heal


def apply_buff(
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
    target_key = instance_key or definition_key
    existing = (
        entity.buffs.all.get(target_key)
        if hasattr(getattr(entity, "buffs", None), "all")
        else None
    )
    is_refresh = (
        existing is not None
        and not getattr(existing, "paused", False)
        and getattr(existing, "stacks", 1) > 0
        and (
            getattr(existing, "remaining_seconds", None) is None
            or existing.remaining_seconds > 0
        )
    )
    source_tier = data.get("source_tier")
    if source_tier is None:
        source_tier = "學徒"
    data["source_tier"] = source_tier
    recovery_policy = get_recovery_policy(definition)
    if recovery_policy is not None:
        # Normalize snapshot data with neutral defaults
        raw_heal_gain = data.get("snapshot_heal_gain", 0.0)
        raw_grace = data.get("snapshot_grace_multiplier", 1.0)
        data["snapshot_heal_gain"] = _parse_percent_value(raw_heal_gain)
        if isinstance(raw_grace, bool) or not isinstance(raw_grace, (int, float)) or not isfinite(raw_grace) or raw_grace < 0:
            raise ValueError(f"invalid snapshot_grace_multiplier: {raw_grace!r}")
        data["snapshot_grace_multiplier"] = float(raw_grace)
    cache = {
        "definition_key": definition_key,
        "tick_interval": definition.tick_interval,
        "remaining_seconds": definition.duration,
        "tick_elapsed_seconds": 0,
        **data,
    }
    if "divert" in definition.modifiers and not is_refresh and "divert_consumed" not in data:
        cache["divert_consumed"] = 0
    entity.buffs.add(
        RulebookBuff,
        key=instance_key or definition_key,
        duration=-1,
        to_cache=cache,
    )
    if definition.polarity == "debuff" and not is_refresh:
        from world.rules.state_reactions import dispatch_outcome_reaction

        dispatch_outcome_reaction(
            entity, "negative_buff_added", source_tier=source_tier
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


def active_stack_count(arg1: Any, arg2: Any) -> int:
    """Return the total active stacks for a buff definition key on an entity.

    Accepts either (entity, definition_key) or (definition_key, entity) for
    ergonomics. Reads stored state without materializing entity.buffs if possible,
    so preview paths remain side-effect-free.
    """
    if isinstance(arg1, str) and not isinstance(arg2, str):
        definition_key, entity = arg1, arg2
    else:
        entity, definition_key = arg1, str(arg2)

    from collections.abc import Mapping

    if hasattr(entity, "attributes") and entity.attributes.has("buffs"):
        cache = entity.attributes.get("buffs", default={})
        if isinstance(cache, Mapping):
            total = 0
            for buff_cache in cache.values():
                if not isinstance(buff_cache, Mapping):
                    continue
                if buff_cache.get("paused"):
                    continue
                if buff_cache.get("definition_key") != definition_key:
                    continue
                stacks = buff_cache.get("stacks")
                if not isinstance(stacks, int) or stacks <= 0:
                    continue
                remaining = buff_cache.get("remaining_seconds")
                if isinstance(remaining, int) and remaining <= 0:
                    continue
                total += stacks
            return total

    if hasattr(entity, "buffs") and hasattr(entity.buffs, "all"):
        total = 0
        for buff in entity.buffs.all.values():
            if getattr(buff, "paused", False):
                continue
            if getattr(buff, "definition_key", None) != definition_key:
                continue
            if getattr(buff, "remaining_seconds", None) is not None and buff.remaining_seconds <= 0:
                continue
            stacks = getattr(buff, "stacks", 0)
            if isinstance(stacks, int) and stacks > 0:
                total += stacks
        return total

    return 0

def _active_buff_instances(entity) -> tuple[RulebookBuff, ...]:
    """Return unpaused game-time-unexpired buff instances with positive stacks."""
    if not hasattr(entity, "buffs"):
        return ()
    if hasattr(entity, "attributes") and not entity.attributes.has("buffs"):
        return ()
    buffs = getattr(entity, "buffs", None)
    if buffs is None or not hasattr(buffs, "all"):
        return ()
    return tuple(
        buff
        for buff in buffs.all.values()
        if not getattr(buff, "paused", False)
        and getattr(buff, "stacks", 1) > 0
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
    apply_buff(
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

def remove_by_selector(entity, selector: str) -> int:
    """Remove every live buff instance one selector names; return the count.

    The selector vocabulary is exactly a concrete ``buffs.yaml`` definition
    key or one of the polarity-wide words ``all`` / ``positive`` /
    ``negative`` (``_REMOVE_SELECTORS``); an unrecognized selector fails
    closed rather than silently removing nothing. Selection resolves against
    live buff **instances**, so a definition with several live instances
    (distinct instance keys) loses all of them, and every removal routes
    through the same ``dispel=True`` external-removal path the cleanse
    handler already uses. A selector matching nothing writes nothing and
    returns ``0``. An empty result is a legitimate outcome, not an error.
    """
    if selector not in _REMOVE_SELECTORS and selector not in BUFF_DEFINITIONS:
        raise ValueError(f"unknown buff removal selector {selector!r}")

    def _matches(definition_key: str) -> bool:
        if selector == "all":
            return True
        if selector == "negative":
            return BUFF_DEFINITIONS[definition_key].polarity == "debuff"
        if selector == "positive":
            return BUFF_DEFINITIONS[definition_key].polarity == "buff"
        return definition_key == selector

    keys = tuple(
        buff.buffkey
        for buff in _active_buff_instances(entity)
        if _matches(buff.definition_key)
    )
    if not keys:
        return 0
    _remove_buff_keys(entity, keys)
    return len(keys)


def cleanse_debuffs(entity) -> int:
    """Remove every active debuff-polarity buff and return the count removed.

    The shipped ``negative`` alias of :func:`remove_by_selector`, so
    holy-water settlement and the cleanse effect handler share one
    semantics. Returns 0 when nothing is active (and writes nothing).
    """
    return remove_by_selector(entity, "negative")


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
                # The stage-time selection above exists only for the effect
                # description and the skip-when-empty check; applying through
                # the shared selector keeps the cleanse effect and every
                # other debuff-clearing caller on one removal (delta trace
                # scenario) instead of replaying a snapshot key tuple.
                apply=lambda target=target: remove_by_selector(target, "negative"),
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
                recovery_policy = get_recovery_policy(BUFF_DEFINITIONS[buff.definition_key])
                if recovery_policy is not None:
                    _apply_recovery_tick(entity, buff, recovery_policy)
                accumulated -= interval
            buff.tick_elapsed_seconds = accumulated
        if remaining is not None:
            buff.remaining_seconds = max(0, remaining - elapsed)
    return tuple(records)
