"""Validators for the core-owned rulebook sections.

``pg_lines`` / ``weak_debuff`` (defeat-aftermath-core D-C8) and
``recovery`` (defeat-aftermath-recovery D-R2).

Part of the :mod:`world.rules.defeat_aftermath` package split; the package
re-exports the historical public surface.
"""
import math
from pathlib import Path
from typing import Any

from world.rules.clock import MAX_ADVANCE_SECONDS
from world.rules.defeat_aftermath.contracts import RecoveryConfig


def _validate_pg_lines(raw: dict[str, Any], path: Path) -> tuple[str, ...]:
    pg_lines = raw.get("pg_lines")
    if (
        not isinstance(pg_lines, list)
        or not pg_lines
        or any(not isinstance(line, str) or not line.strip() for line in pg_lines)
    ):
        raise ValueError(
            f"{path}: section 'pg_lines' must be a nonempty list of nonempty strings"
        )
    return tuple(pg_lines)


def _validate_weak_debuff(raw: dict[str, Any], path: Path) -> str:
    weak_debuff = raw.get("weak_debuff")
    if not isinstance(weak_debuff, dict) or not isinstance(
        weak_debuff.get("buff_key"), str
    ):
        raise ValueError(
            f"{path}: section 'weak_debuff' must be a mapping with a string 'buff_key'"
        )
    from world.rules.buffs import BUFF_DEFINITIONS

    if weak_debuff["buff_key"] not in BUFF_DEFINITIONS:
        raise ValueError(
            f"{path}: weak_debuff buff_key {weak_debuff['buff_key']!r} "
            "is not a rulebook buff"
        )
    return weak_debuff["buff_key"]


def _validate_recovery(raw: dict[str, Any], path: Path) -> RecoveryConfig:
    """Validate the ``recovery`` section fail-closed (delta requirement 3).

    ``regen_scale`` must be a finite real in ``(0, 1]``: a scale above 1 makes
    the real un-scaled advance heal less than the virtual solve, so the
    downward-only clamp could never pin the mandatory exact-target wake
    (rubber-duck plan review finding 7). ``max_recovery_seconds`` is bounded
    by the clock's one-advance day bound so the capped advance can never raise
    ``ClockAdvanceBoundError``.
    """
    recovery = raw.get("recovery")
    if not isinstance(recovery, dict):
        raise ValueError(f"{path}: section 'recovery' must be a mapping")
    scale = recovery.get("regen_scale")
    if (
        isinstance(scale, bool)
        or not isinstance(scale, (int, float))
        or not math.isfinite(scale)
        or not 0 < scale <= 1
    ):
        raise ValueError(
            f"{path}: recovery regen_scale must be a finite real in (0, 1], got {scale!r}"
        )
    cap = recovery.get("max_recovery_seconds")
    if (
        isinstance(cap, bool)
        or not isinstance(cap, int)
        or cap < 1
        or cap > MAX_ADVANCE_SECONDS
    ):
        raise ValueError(
            f"{path}: recovery max_recovery_seconds must be an integer in "
            f"[1, {MAX_ADVANCE_SECONDS}], got {cap!r}"
        )
    fraction = recovery.get("wake_fraction")
    if (
        isinstance(fraction, bool)
        or not isinstance(fraction, (int, float))
        or not math.isfinite(fraction)
        or not 0 < fraction < 1
    ):
        raise ValueError(
            f"{path}: recovery wake_fraction must be a finite real in (0, 1), got {fraction!r}"
        )
    return RecoveryConfig(
        regen_scale=float(scale),
        max_recovery_seconds=int(cap),
        wake_fraction=float(fraction),
    )
