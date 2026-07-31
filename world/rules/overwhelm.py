"""Deterministic overwhelm classification and bounded encounter resolution."""

from collections.abc import Iterable
from dataclasses import dataclass, replace
import math
from pathlib import Path
from typing import Any, Literal

import yaml

from world.rules import combat
from world.rules.combat import Battlefield
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.event_log import EventEntry, EventLog


OVERWHELM_YAML = yaml.safe_load(
    (Path(__file__).parent / "rulebook" / "overwhelm.yaml").read_text(
        encoding="utf-8"
    )
)


def _living_members(
    battlefield: Battlefield,
    team_key: str,
) -> tuple[Any, ...]:
    """Return a team's living, present, non-fled members in stable order."""
    return tuple(
        battlefield.roster[key]
        for key in sorted(battlefield.teams[team_key])
        if key in battlefield.roster
        and key not in battlefield.fled
        and combat._stored_hp(battlefield.roster[key]) > 0
    )


def team_effective_power(
    battlefield: Battlefield,
    team_key: str,
) -> float:
    """Return the aggregate effective power of one active team."""
    return sum(
        combat.effective_power(entity)
        for entity in _living_members(battlefield, team_key)
    )


def power_ratio_verdict(
    battlefield: Battlefield,
    team_a: str,
    team_b: str,
) -> str | None:
    """Return the team meeting the configured power ratio, if any."""
    power_a = team_effective_power(battlefield, team_a)
    power_b = team_effective_power(battlefield, team_b)
    threshold = float(OVERWHELM_YAML["power_ratio_threshold"])
    if power_b == 0 and power_a > 0:
        return team_a
    if power_a == 0 and power_b > 0:
        return team_b
    if power_b > 0 and power_a / power_b >= threshold:
        return team_a
    if power_a > 0 and power_b / power_a >= threshold:
        return team_b
    return None


def _apply_percent(base: float, modifier: str | None) -> float:
    if modifier is None:
        return base
    return combat._apply_percent_mod(base, modifier)


def _adjusted_agility(
    entity: Any,
    modifiers: dict[str, Any] | None = None,
) -> float:
    """Read agility through the same skill and modifier paths as combat."""
    if modifiers is None:
        modifiers = evaluate_combat_modifiers(entity)
    return _apply_percent(
        float(entity.skills.effective_value("agility")),
        modifiers.get("agility"),
    )


def _required_roll(attacker: Any, defender: Any) -> float:
    """Return the minimum inclusive d100 roll using combat's exact formula."""
    attacker_modifiers = evaluate_combat_modifiers(attacker)
    defender_modifiers = evaluate_combat_modifiers(defender)
    attacker_agility = _adjusted_agility(attacker, attacker_modifiers)
    defender_agility = _adjusted_agility(defender, defender_modifiers)
    return (
        float(combat.COMBAT_YAML["to_hit"]["defender_constant"])
        + defender_agility
        - attacker_agility
        - float(attacker_modifiers.get("accuracy", 0))
    )


def _agility_saturation(
    attacker: Any,
    defender: Any,
) -> Literal["hit", "miss", "contested"]:
    """Classify the inclusive d100 to-hit range without rolling."""
    required = _required_roll(attacker, defender)
    if required <= 1:
        return "hit"
    if required > 100:
        return "miss"
    return "contested"


def hit_rate_verdict(
    battlefield: Battlefield,
    team_a: str,
    team_b: str,
) -> str | None:
    """Return a team that always hits and can never be hit."""
    a_members = _living_members(battlefield, team_a)
    b_members = _living_members(battlefield, team_b)
    if not a_members or not b_members:
        return None
    a_always_hits = all(
        _agility_saturation(a, b) == "hit"
        for a in a_members
        for b in b_members
    )
    b_never_hits = all(
        _agility_saturation(b, a) == "miss"
        for a in a_members
        for b in b_members
    )
    if a_always_hits and b_never_hits:
        return team_a
    b_always_hits = all(
        _agility_saturation(b, a) == "hit"
        for a in a_members
        for b in b_members
    )
    a_never_hits = all(
        _agility_saturation(a, b) == "miss"
        for a in a_members
        for b in b_members
    )
    if b_always_hits and a_never_hits:
        return team_b
    return None


def _expected_damage_per_attack(attacker: Any, defender: Any) -> float:
    """Conservatively estimate one physical attack's expected damage."""
    required = math.ceil(_required_roll(attacker, defender))
    successful_rolls = max(0, 101 - max(1, required))
    hit_probability = min(successful_rolls, 100) / 100
    damage = combat.COMBAT_YAML["damage"]
    base_damage = max(
        round(
            attacker.skills.effective_value("atk_phys")
            * float(damage["base_multiplier"])
        )
        - defender.skills.effective_value("defense"),
        int(damage["floor"]),
    )
    return hit_probability * base_damage


def estimated_rounds_to_conclude(
    battlefield: Battlefield,
    overwhelming_team: str,
    overwhelmed_team: str,
) -> float:
    """Estimate remaining rounds using current hp and conservative damage."""
    overwhelming = _living_members(battlefield, overwhelming_team)
    overwhelmed = _living_members(battlefield, overwhelmed_team)
    remaining_hp = sum(combat._stored_hp(member) for member in overwhelmed)
    if remaining_hp <= 0:
        return 0.0
    if not overwhelming or not overwhelmed:
        return math.inf
    toughest = max(overwhelmed, key=combat._stored_hp)
    damage_per_round = sum(
        _expected_damage_per_attack(attacker, toughest)
        for attacker in overwhelming
    )
    if damage_per_round <= 0:
        return math.inf
    return remaining_hp / damage_per_round


def _decided_direction(
    battlefield: Battlefield,
    team_a: str,
    team_b: str,
) -> str | None:
    ratio = power_ratio_verdict(battlefield, team_a, team_b)
    hit_rate = hit_rate_verdict(battlefield, team_a, team_b)
    if ratio is not None and hit_rate is not None:
        return ratio if ratio == hit_rate else None
    return ratio if ratio is not None else hit_rate


def classify_overwhelm(battlefield: Battlefield) -> str | None:
    """Return the overwhelming team when the encounter is decided and quick."""
    team_a, team_b = sorted(battlefield.teams)
    decided = _decided_direction(battlefield, team_a, team_b)
    if decided is None:
        return None
    overwhelmed = team_b if decided == team_a else team_a
    estimate = estimated_rounds_to_conclude(
        battlefield,
        decided,
        overwhelmed,
    )
    if estimate > float(OVERWHELM_YAML["max_estimated_rounds"]):
        return None
    return decided


@dataclass(frozen=True)
class OverwhelmResult:
    """Structured result from one bounded overwhelm-resolution call."""

    event_logs: tuple[EventLog, ...]
    rounds_elapsed: int
    total_seconds: int
    overwhelming_team: str | None
    verdict_after: str | None
    battle_over: bool


def _damage_entries(logs: Iterable[EventLog]) -> Iterable[EventEntry]:
    return (
        entry
        for log in logs
        for entry in log.entries
        if entry.kind == "damage"
    )


def compress_event_logs(
    raw_logs: Iterable[EventLog],
    overwhelming_team: str,
    overwhelmed_team: str,
    rounds: int,
) -> tuple[EventLog, ...]:
    """Remove redundant successful-hit rolls and prepend an encounter summary."""
    raw = tuple(raw_logs)
    filtered = tuple(
        replace(
            log,
            entries=tuple(
                entry
                for entry in log.entries
                if entry.kind != "roll" or not entry.data.get("hit", False)
            ),
        )
        for log in raw
    )
    filtered = tuple(log for log in filtered if log.entries)
    damage_entries = tuple(_damage_entries(filtered))
    hits = len(damage_entries)
    total_damage = sum(
        int(entry.data.get("amount", 0))
        for entry in damage_entries
    )
    summary_entry = EventEntry(
        kind="overwhelm_resolution",
        actor=overwhelming_team,
        target=overwhelmed_team,
        data={
            "rounds": rounds,
            "hits": hits,
            "total_damage": total_damage,
        },
        text_template=(
            "{actor} 與 {target} 在壓倒性態勢判定下交戰 "
            "{data[rounds]} 回合；雙方共命中 {data[hits]} 次，"
            "造成 {data[total_damage]} 點傷害。"
        ),
    )
    summary = EventLog(
        actor=overwhelming_team,
        skill_key="overwhelm_resolution",
        targets=(overwhelmed_team,),
        entries=(summary_entry,),
        time_cost_seconds=0,
    )
    return (summary,) + filtered


def _resolve_overwhelm_raw(
    battlefield: Battlefield,
    action_provider: combat.ActionProvider,
    max_rounds: int,
) -> tuple[str | None, str | None, list[EventLog], int]:
    """Resolve and expose raw logs for exact-equivalence tests."""
    if max_rounds < 0:
        raise ValueError("max_rounds must be non-negative")
    initial = classify_overwhelm(battlefield)
    if initial is None or combat.is_battle_over(battlefield):
        return initial, initial, [], 0
    raw_logs: list[EventLog] = []
    rounds = 0
    verdict_after = initial
    while rounds < max_rounds and not combat.is_battle_over(battlefield):
        raw_logs.extend(combat.run_round(battlefield, action_provider))
        rounds += 1
        verdict_after = classify_overwhelm(battlefield)
        if verdict_after != initial:
            break
    return initial, verdict_after, raw_logs, rounds


def resolve_overwhelm(
    battlefield: Battlefield,
    action_provider: combat.ActionProvider,
    max_rounds: int = 12,
) -> OverwhelmResult:
    """Resolve a currently overwhelming encounter through the normal loop."""
    initial, verdict_after, raw_logs, rounds = _resolve_overwhelm_raw(
        battlefield,
        action_provider,
        max_rounds,
    )
    event_logs = (
        ()
        if initial is None or not raw_logs
        else compress_event_logs(
            raw_logs,
            initial,
            next(team for team in battlefield.teams if team != initial),
            rounds,
        )
    )
    return OverwhelmResult(
        event_logs=event_logs,
        rounds_elapsed=rounds,
        total_seconds=rounds
        * int(combat.COMBAT_YAML["round"]["seconds"]),
        overwhelming_team=initial,
        verdict_after=verdict_after,
        battle_over=combat.is_battle_over(battlefield),
    )
