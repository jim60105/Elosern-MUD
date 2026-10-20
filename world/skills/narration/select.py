"""Pure deterministic narration selection.

Selection is a CRC over a canonical seed of stable identifiers. It consumes no
gameplay randomness, reads no clock, and never raises: a miss degrades through
the lookup chain (exact row -> family tier -> kind pool -> compact fallback).
"""

from __future__ import annotations

import zlib
from collections.abc import Mapping
from typing import Any

from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.sexual_acts._builder import SexualActDef

from .catalog import FAMILY_ROWS, NARRATION_CATALOG
from .families import base_family_key
from .pools import (
    COMMANDED_ACTION_LINES,
    COMPACT_POOLS,
    DAMAGE_BAND_LINES,
    GENERIC_ACTION_LINES,
    HEAL_BAND_LINES,
    HIT_LINES,
    INTERNAL_KINDS,
    KIND_POOLS,
    MISS_LINES,
    PLEASURE_ACTOR_LINES,
    PLEASURE_TARGET_LINES,
    SELF_HEAL_BAND_LINES,
    SEXUAL_COUNTER_ACTOR_LINES,
    SEXUAL_COUNTER_SHARED_LINES,
    TRAIT_DELTA_LINES,
    TRANSITION_LINES,
    VERDICT_LINES,
)
from .vocab import (
    DAMAGE_BANDS,
    HEAL_BANDS,
    MAX_RENDERED_CODE_POINTS,
    NarrationRow,
    PLEASURE_BANDS,
    band_for,
)

Grid = Mapping[str, NarrationRow]


def variant_index(seed: str, count: int) -> int:
    """Return a stable variant index for one canonical seed."""
    if count <= 0:
        return 0
    return zlib.crc32(seed.encode("utf-8")) % count


def narration_seed(
    scope: str,
    skill_key: str,
    kind: str,
    ordinal: int,
    target_key: str,
    band: str,
) -> str:
    """Assemble the canonical seed in its fixed order."""
    return "|".join(
        (
            scope or "",
            skill_key or "",
            kind or "",
            str(ordinal),
            target_key or "",
            band or "",
        )
    )


def _render(template: str, actor: str, target: str) -> str:
    return template.format(actor=actor or "", target=target or "")


def _fits(template: str, actor: str, target: str) -> bool:
    return sum(1 for _ in _render(template, actor, target)) <= MAX_RENDERED_CODE_POINTS


def choose_line(
    lines: tuple[str, ...] | list[str] | None,
    seed: str,
    *,
    actor: str,
    target: str,
) -> str | None:
    """Return the seeded variant, then forward, then backward, that fits."""
    if not lines:
        return None
    count = len(lines)
    start = variant_index(seed, count)
    for offset in range(count):
        candidate = lines[(start + offset) % count]
        if _fits(candidate, actor, target):
            return candidate
    for offset in range(count):
        candidate = lines[(start - offset) % count]
        if _fits(candidate, actor, target):
            return candidate
    return None


def _override_tiers(
    skill_key: str,
    family: str | None,
    kind: str,
    catalog: Grid,
    families: Grid,
) -> list[tuple[str, ...]]:
    tiers: list[tuple[str, ...]] = []
    row = catalog.get(skill_key)
    if row is not None:
        lines = row.kind_lines.get(kind)
        if lines:
            tiers.append(lines)
    for key in _family_chain(family):
        family_row = families.get(key)
        if family_row is not None:
            lines = family_row.kind_lines.get(kind)
            if lines:
                tiers.append(lines)
    return tiers


def _family_chain(family: str | None) -> tuple[str, ...]:
    if not family:
        return ()
    base = base_family_key(family)
    return (family,) if base == family else (family, base)


def _action_tiers(
    skill_key: str,
    family: str | None,
    catalog: Grid = NARRATION_CATALOG,
    families: Grid = FAMILY_ROWS,
) -> list[tuple[str, ...]]:
    """Return the action-clause tiers in lookup order."""
    tiers: list[tuple[str, ...]] = []
    row = catalog.get(skill_key)
    if row is not None and row.action:
        tiers.append(row.action)
    for key in _family_chain(family):
        family_row = families.get(key)
        if family_row is not None and family_row.action:
            tiers.append(family_row.action)
    tiers.append(GENERIC_ACTION_LINES)
    return tiers


def action_lines(
    skill_key: str,
    family: str | None,
    catalog: Grid = NARRATION_CATALOG,
    families: Grid = FAMILY_ROWS,
) -> tuple[str, ...]:
    """Return the first action-clause tier for one skill."""
    return _action_tiers(skill_key, family, catalog, families)[0]


def action_line(
    skill_key: str,
    family: str | None,
    *,
    scope: str = "",
    target_key: str = "",
    actor: str = "",
    catalog: Grid = NARRATION_CATALOG,
    families: Grid = FAMILY_ROWS,
) -> str:
    """Return the selected action-clause template for one resolved action."""
    seed = narration_seed(scope, skill_key, "action", 0, target_key, "")
    for lines in _action_tiers(skill_key, family, catalog, families):
        chosen = choose_line(lines, seed, actor=actor, target="")
        if chosen is not None:
            return chosen
    return COMPACT_POOLS["action_narration"]


def _amount(data: Mapping[str, Any], key: str = "amount") -> float | None:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def band_for_entry(kind: str, data: Mapping[str, Any], max_hp: float | None) -> str:
    """Resolve the qualitative band id for one entry, or ``""``."""
    if kind == "damage":
        amount = _amount(data)
        return band_for(DAMAGE_BANDS, _ratio(amount, max_hp))
    if kind in ("heal", "self_heal"):
        amount = _amount(data)
        return band_for(HEAL_BANDS, _ratio(amount, max_hp))
    if kind == "pleasure_gain":
        amount = _amount(data)
        return band_for(PLEASURE_BANDS, _ratio(amount, 100.0))
    return ""


def _ratio(amount: float | None, maximum: float | None) -> float | None:
    if amount is None or maximum is None or maximum <= 0:
        return None
    return amount / maximum


def _special_lines(
    kind: str,
    data: Mapping[str, Any],
    *,
    actor_key: str,
    target_key: str,
    act: SexualActDef | None,
    band: str,
) -> tuple[str, ...]:
    if kind == "roll":
        return HIT_LINES if bool(data.get("hit")) else MISS_LINES
    if kind == "damage":
        table = DAMAGE_BAND_LINES
        return table.get(band, table["solid"])
    if kind == "heal":
        table = HEAL_BAND_LINES
        return table.get(band, table["restoring"])
    if kind == "self_heal":
        table = SELF_HEAL_BAND_LINES
        return table.get(band, table["restoring"])
    if kind == "pleasure_gain":
        table = (
            PLEASURE_ACTOR_LINES
            if target_key and target_key == actor_key
            else PLEASURE_TARGET_LINES
        )
        return table.get(band, table["clear"])
    if kind == "sexual_counter":
        counter = str(data.get("counter", ""))
        if act is not None and counter in act.participant_counters:
            return SEXUAL_COUNTER_SHARED_LINES
        return SEXUAL_COUNTER_ACTOR_LINES
    if kind == "trait_delta":
        trait = str(data.get("trait_key", ""))
        if trait in TRAIT_DELTA_LINES:
            return TRAIT_DELTA_LINES[trait]
        return KIND_POOLS["trait_delta"]
    if kind == "sexual_transition":
        event = str(data.get("event", ""))
        return TRANSITION_LINES.get(event, KIND_POOLS["sexual_transition"])
    if kind == "sexual_resist":
        if bool(data.get("resisted")):
            verdict = "resist"
        elif bool(data.get("auto_comply")):
            verdict = "auto_comply"
        else:
            verdict = "comply"
        return VERDICT_LINES[verdict]
    return ()


def entry_line(
    kind: str,
    data: Mapping[str, Any],
    *,
    skill_key: str = "",
    family: str | None = None,
    scope: str = "",
    ordinal: int = 0,
    actor_key: str = "",
    target_key: str = "",
    actor: str = "",
    target: str = "",
    act: SexualActDef | None = None,
    max_hp: float | None = None,
    catalog: Grid = NARRATION_CATALOG,
    families: Grid = FAMILY_ROWS,
) -> str:
    """Return the selected narration template for one non-first entry."""
    if kind in INTERNAL_KINDS:
        return ""
    band = band_for_entry(kind, data, max_hp)
    seed = narration_seed(scope, skill_key, kind, ordinal, target_key, band)
    for lines in _override_tiers(skill_key, family, kind, catalog, families):
        chosen = choose_line(lines, seed, actor=actor, target=target)
        if chosen is not None:
            return chosen
    special = _special_lines(
        kind,
        data,
        actor_key=actor_key,
        target_key=target_key,
        act=act,
        band=band,
    )
    chosen = choose_line(special, seed, actor=actor, target=target)
    if chosen is not None:
        return chosen
    chosen = choose_line(
        KIND_POOLS.get(kind, ()), seed, actor=actor, target=target
    )
    if chosen is not None:
        return chosen
    compact = COMPACT_POOLS.get(kind)
    return compact if compact is not None else ""


def compose_first_line(
    skill_key: str,
    family: str | None,
    outcome_template: str,
    *,
    scope: str = "",
    target_key: str = "",
    actor: str = "",
    target: str = "",
    catalog: Grid = NARRATION_CATALOG,
    families: Grid = FAMILY_ROWS,
) -> str:
    """Compose the action clause behind the first entry's outcome clause."""
    if not outcome_template:
        return outcome_template
    action = action_line(
        skill_key,
        family,
        scope=scope,
        target_key=target_key,
        actor=actor,
        catalog=catalog,
        families=families,
    )
    if not action:
        return outcome_template
    if _fits(action + outcome_template, actor, target):
        return action + outcome_template
    if _fits(outcome_template, actor, target):
        return outcome_template
    if _fits(action, actor, target):
        return action
    return outcome_template


def commanded_action_line(action_kind: str, *, actor: str) -> str:
    """Return the numbered-free marker line for one commanded action."""
    lines = COMMANDED_ACTION_LINES.get(action_kind) or COMMANDED_ACTION_LINES["skill"]
    return choose_line(
        lines,
        narration_seed("", "", "commanded_action", 0, action_kind, ""),
        actor=actor,
        target="",
    ) or COMPACT_POOLS["commanded_action"]


def act_for_skill(skill_key: str) -> SexualActDef | None:
    """Return the sexual-act sidecar for one key, when it is an act."""
    return SEXUAL_ACT_REGISTRY.get(skill_key)


__all__ = [
    "act_for_skill",
    "action_line",
    "action_lines",
    "band_for_entry",
    "choose_line",
    "commanded_action_line",
    "compose_first_line",
    "entry_line",
    "narration_seed",
    "variant_index",
]
