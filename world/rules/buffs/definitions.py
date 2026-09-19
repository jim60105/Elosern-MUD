"""Buff-definition vocabulary: YAML schema, policies, and the loader.

Extracted from :mod:`world.rules.buffs` as the definitions layer of the
package: nothing here depends on buff instances or entity mutation.
"""

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from world.rules.quantum import SETTLEMENT_QUANTUM_SECONDS

from world.rules.traits import GAUGE_KEYS

#: The polarity-wide words :func:`world.rules.buffs.remove_by_selector`
#: understands beyond a concrete definition key. Forward-declared seam
#: (design D5): ``positive`` and ``all`` ship tested but caller-less until
#: the item-effect change.
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


MARKER_VOCABULARY = frozenset({"ground", "positional"})
ROUND_ORDER_VOCABULARY = frozenset({"advance_to_head", "retreat_to_tail"})


@dataclass(frozen=True)
class BuffDefinition:
    """Validated setting data for one logical buff."""

    key: str
    duration: int | None
    tick_interval: int | None
    stacking: str
    modifiers: dict[str, Any]
    polarity: str = "buff"
    marker: str | None = None
    round_order: dict[str, str] | None = None


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
        marker = None
        if "marker" in entry:
            marker_val = entry["marker"]
            if isinstance(marker_val, bool) or not isinstance(marker_val, str) or marker_val not in MARKER_VOCABULARY:
                raise ValueError(
                    f"{path}: buff {key!r} has invalid marker {marker_val!r}; must be in {sorted(MARKER_VOCABULARY)}"
                )
            marker = marker_val
        round_order = None
        if "round_order" in entry:
            ro_val = entry["round_order"]
            if (
                isinstance(ro_val, bool)
                or not isinstance(ro_val, dict)
                or set(ro_val.keys()) != {"action"}
                or isinstance(ro_val["action"], bool)
                or not isinstance(ro_val["action"], str)
                or ro_val["action"] not in ROUND_ORDER_VOCABULARY
            ):
                raise ValueError(
                    f"{path}: buff {key!r} has invalid round_order {ro_val!r}; must be a mapping with action in {sorted(ROUND_ORDER_VOCABULARY)}"
                )
            round_order = dict(ro_val)
        definitions[key] = BuffDefinition(
            key=key,
            duration=entry.get("duration"),
            tick_interval=entry.get("tick_interval"),
            stacking=stacking,
            modifiers=dict(modifiers),
            polarity=polarity,
            marker=marker,
            round_order=round_order,
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


BUFF_DEFINITIONS = load_buff_definitions(
    Path(__file__).parent.parent / "rulebook" / "buffs.yaml"
)
BLOCKING_BUFF_KEYS = frozenset({"paralysis"})
_NO_OP_RATE_TARGETS = frozenset({"skill_practice"})
