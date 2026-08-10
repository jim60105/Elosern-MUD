"""Loader and resolver for the affinity rulebook (affinity-system D-4).

``affinity.yaml`` carries the tunable numbers: the offline party-invite
threshold, the shared daily interaction cap, the quest-completion gain, and
exactly seven stage rules whose floors must equal the canonical sequence
0/10/30/50/70/90/100. Loading validates every entry and fails closed before
any consumer reads it; stage resolution ("last stage with floor <= value") is
a pure lookup so the display layer never duplicates balance constants.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


class AffinityConfigError(ValueError):
    """The affinity rulebook violates the canonical contract."""


CANONICAL_FLOORS = (0, 10, 30, 50, 70, 90, 100)
_STAGE_FIELDS = frozenset({"id", "floor", "name", "look_flavor"})
_TOP_LEVEL_FIELDS = frozenset(
    {
        "invite_threshold",
        "daily_interaction_cap",
        "quest_completion_gain",
        "friendly_fire_penalty_per_hit",
        "stages",
    }
)


@dataclass(frozen=True)
class AffinityStage:
    """One authored stage of the affinity ladder."""

    id: str
    floor: int
    name: str
    look_flavor: str


@dataclass(frozen=True)
class AffinityConfig:
    """The validated affinity balance table."""

    invite_threshold: int
    daily_interaction_cap: int
    quest_completion_gain: int
    friendly_fire_penalty_per_hit: int
    stages: tuple[AffinityStage, ...]

    def stage_for_value(self, value: int) -> AffinityStage:
        """Resolve one value to its stage (last stage with ``floor <= value``).

        Values at or above the topmost floor resolve to the topmost stage, so a
        future cap break never needs a display change.
        """
        resolved = self.stages[0]
        for stage in self.stages:
            if stage.floor <= value:
                resolved = stage
            else:
                break
        return resolved

    def stage_by_id(self, stage_id: str) -> AffinityStage | None:
        """Return the stage carrying ``stage_id``, or ``None``."""
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        return None


def _error(message: str) -> AffinityConfigError:
    return AffinityConfigError(f"affinity.yaml: {message}")


def _require_int(value: Any, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(f"{field} must be an integer")
    if value < minimum:
        raise _error(f"{field} must be at least {minimum}")
    return value


def load_config(path: Path | None = None) -> AffinityConfig:
    """Load and validate the affinity rulebook, failing closed on deviation.

    ``path`` overrides the canonical rulebook location. Tests exercise deviant
    rulebooks through a temporary copy so the shared source file is never
    rewritten, which keeps parallel workers from racing on the file.
    """
    rulebook = (
        Path(__file__).parent / "rulebook" / "affinity.yaml"
        if path is None
        else path
    )
    raw = yaml.safe_load(rulebook.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise _error("rulebook must be a mapping")
    raw = dict(raw)
    unknown = set(raw) - _TOP_LEVEL_FIELDS
    if unknown:
        raise _error(f"unknown top-level fields {sorted(unknown)}")
    missing = _TOP_LEVEL_FIELDS - set(raw)
    if missing:
        raise _error(f"missing top-level fields {sorted(missing)}")

    invite_threshold = _require_int(
        raw["invite_threshold"], "invite_threshold", minimum=1
    )
    daily_interaction_cap = _require_int(
        raw["daily_interaction_cap"], "daily_interaction_cap", minimum=1
    )
    quest_completion_gain = _require_int(
        raw["quest_completion_gain"], "quest_completion_gain", minimum=1
    )
    friendly_fire_penalty_per_hit = _require_int(
        raw["friendly_fire_penalty_per_hit"],
        "friendly_fire_penalty_per_hit",
        minimum=1,
    )

    stages_raw = raw["stages"]
    if not isinstance(stages_raw, list):
        raise _error("stages must be a list")
    if len(stages_raw) != len(CANONICAL_FLOORS):
        raise _error(
            f"exactly {len(CANONICAL_FLOORS)} stages are required, "
            f"got {len(stages_raw)}"
        )
    stages: list[AffinityStage] = []
    seen_ids: set[str] = set()
    for position, entry in enumerate(stages_raw, start=1):
        if not isinstance(entry, Mapping):
            raise _error(f"stage {position} must be a mapping")
        entry = dict(entry)
        if set(entry) != _STAGE_FIELDS:
            raise _error(
                f"stage {position} must carry exactly "
                f"{sorted(_STAGE_FIELDS)}"
            )
        stage_id = entry["id"]
        if not isinstance(stage_id, str) or not stage_id.strip():
            raise _error(f"stage {position} id must be a non-empty string")
        if stage_id in seen_ids:
            raise _error(f"duplicate stage id {stage_id!r}")
        seen_ids.add(stage_id)
        floor = _require_int(entry["floor"], f"stages.{stage_id}.floor", minimum=0)
        name = entry["name"]
        look_flavor = entry["look_flavor"]
        if not isinstance(name, str) or not name.strip():
            raise _error(f"stages.{stage_id}.name must be a non-empty string")
        if not isinstance(look_flavor, str) or not look_flavor.strip():
            raise _error(
                f"stages.{stage_id}.look_flavor must be a non-empty string"
            )
        stages.append(
            AffinityStage(
                id=stage_id,
                floor=floor,
                name=name,
                look_flavor=look_flavor,
            )
        )
    floors = tuple(stage.floor for stage in stages)
    if floors != CANONICAL_FLOORS:
        raise _error(
            f"stage floors must equal the canonical sequence "
            f"{list(CANONICAL_FLOORS)}, got {list(floors)}"
        )
    return AffinityConfig(
        invite_threshold=invite_threshold,
        daily_interaction_cap=daily_interaction_cap,
        quest_completion_gain=quest_completion_gain,
        friendly_fire_penalty_per_hit=friendly_fire_penalty_per_hit,
        stages=tuple(stages),
    )


_CONFIG: AffinityConfig | None = None


def get_config() -> AffinityConfig:
    """Return the validated affinity rulebook singleton."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_config()
    return _CONFIG
