"""Loader and resolver for the affinity rulebook (affinity-system D-4).

``affinity.yaml`` carries the tunable numbers: the offline party-invite
threshold, the shared daily interaction cap, the quest-completion gain, the
per-hit friendly-fire penalty, and exactly seven stage rules whose floors must
equal the canonical sequence 0/10/30/50/70/90/100. It also carries the
``cap_breaks`` milestone table: each entry names exactly one matching identity
(``npc_key`` or ``role``), a ``quest_key`` that resolves in the quest
definition registry, and an integer ``new_cap`` strictly above the natural cap.
Loading validates every entry and fails closed before any consumer reads it;
stage resolution ("last stage with floor <= value") is a pure lookup so the
display layer never duplicates balance constants.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


class AffinityConfigError(ValueError):
    """The affinity rulebook violates the canonical contract."""


CANONICAL_FLOORS = (0, 10, 30, 50, 70, 90, 100)
_STAGE_FIELDS = frozenset({"id", "floor", "name", "look_flavor"})
_CAP_BREAK_FIELDS = frozenset({"npc_key", "role", "quest_key", "new_cap"})
_TOP_LEVEL_FIELDS = frozenset(
    {
        "invite_threshold",
        "daily_interaction_cap",
        "quest_completion_gain",
        "friendly_fire_penalty_per_hit",
        "cap_breaks",
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
class CapBreak:
    """One milestone cap-break entry (affinity-cap-break D2/D3).

    ``selector_kind`` is ``"npc_key"`` or ``"role"``; ``selector`` is the
    matching value. ``quest_key`` must resolve in the quest definition registry
    at load; ``new_cap`` is strictly above the natural cap 99. A then-in-party
    companion matches an ``npc_key`` selector when ``npc.key`` equals it, and a
    ``role`` selector when the companion's schedule is a template reference
    whose template key equals it (the schedule rulebook's "role templates").
    """

    quest_key: str
    selector_kind: str
    selector: str
    new_cap: int


@dataclass(frozen=True)
class AffinityConfig:
    """The validated affinity balance table."""

    invite_threshold: int
    daily_interaction_cap: int
    quest_completion_gain: int
    friendly_fire_penalty_per_hit: int
    cap_breaks: tuple[CapBreak, ...]
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

    def cap_break_for(self, quest_key: str) -> tuple[CapBreak, ...]:
        """Return every cap-break entry declared for ``quest_key``."""
        return tuple(entry for entry in self.cap_breaks if entry.quest_key == quest_key)


def _error(message: str) -> AffinityConfigError:
    return AffinityConfigError(f"affinity.yaml: {message}")


def _require_int(value: Any, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(f"{field} must be an integer")
    if value < minimum:
        raise _error(f"{field} must be at least {minimum}")
    return value


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error(f"{field} must be a non-empty string")
    return value


def _load_cap_breaks(raw: Any, definition_registry: Mapping[str, Any]) -> tuple[CapBreak, ...]:
    """Validate the ``cap_breaks`` table, failing closed on any deviation.

    Each entry must carry exactly one matching identity (``npc_key`` or
    ``role``), a ``quest_key`` that resolves in the supplied quest definition
    registry, an integer ``new_cap`` strictly above the natural cap 99, and no
    duplicate (``quest_key``, selector-kind, selector) triple.
    """
    if not isinstance(raw, list):
        raise _error("cap_breaks must be a list")
    from world.rules.affinity import NATURAL_CAP

    entries: list[CapBreak] = []
    seen_pairs: set[tuple[str, str]] = set()
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, Mapping):
            raise _error(f"cap_breaks[{position}] must be a mapping")
        entry = dict(entry)
        if set(entry) - _CAP_BREAK_FIELDS:
            raise _error(
                f"cap_breaks[{position}] has unknown fields "
                f"{sorted(set(entry) - _CAP_BREAK_FIELDS)}"
            )
        if "quest_key" not in entry:
            raise _error(f"cap_breaks[{position}].quest_key is required")
        quest_key = _require_non_empty_string(
            entry["quest_key"], f"cap_breaks[{position}].quest_key"
        )
        if "new_cap" not in entry:
            raise _error(f"cap_breaks[{position}].new_cap is required")
        if quest_key not in definition_registry:
            raise _error(
                f"cap_breaks[{position}].quest_key {quest_key!r} is not a "
                "registered quest definition"
            )
        # Mutual exclusion is decided by key presence, not by the value, so an
        # entry carrying both keys is rejected even when one value is
        # malformed (a mistyped selector must never silently fall back to the
        # other one).
        if ("npc_key" in entry) == ("role" in entry):
            raise _error(
                f"cap_breaks[{position}] must declare exactly one of "
                "npc_key / role"
            )
        selector_kind = "npc_key" if "npc_key" in entry else "role"
        selector = _require_non_empty_string(
            entry[selector_kind], f"cap_breaks[{position}].{selector_kind}"
        )
        new_cap = _require_int(
            entry["new_cap"], f"cap_breaks[{position}].new_cap", minimum=NATURAL_CAP + 1
        )
        pair = (quest_key, selector_kind, selector)
        if pair in seen_pairs:
            raise _error(
                f"cap_breaks duplicates quest_key {quest_key!r} and selector "
                f"{selector_kind} {selector!r}"
            )
        seen_pairs.add(pair)
        entries.append(
            CapBreak(
                quest_key=quest_key,
                selector_kind=selector_kind,
                selector=selector,
                new_cap=new_cap,
            )
        )
    return tuple(entries)


def load_config(
    path: Path | None = None, definition_registry: Mapping[str, Any] | None = None
) -> AffinityConfig:
    """Load and validate the affinity rulebook, failing closed on deviation.

    ``path`` overrides the canonical rulebook location. Tests exercise deviant
    rulebooks through a temporary copy so the shared source file is never
    rewritten, which keeps parallel workers from racing on the file.
    ``definition_registry`` supplies the quest definition registry that
    ``cap_breaks`` quest keys must resolve in; when omitted the live
    ``QUEST_DEFINITION_REGISTRY`` is used (mirrors ``guild_config``).
    """
    if definition_registry is None:
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY

        definition_registry = QUEST_DEFINITION_REGISTRY
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
    cap_breaks = _load_cap_breaks(raw["cap_breaks"], definition_registry)
    return AffinityConfig(
        invite_threshold=invite_threshold,
        daily_interaction_cap=daily_interaction_cap,
        quest_completion_gain=quest_completion_gain,
        friendly_fire_penalty_per_hit=friendly_fire_penalty_per_hit,
        cap_breaks=cap_breaks,
        stages=tuple(stages),
    )


_CONFIG: AffinityConfig | None = None


def get_config() -> AffinityConfig:
    """Return the validated affinity rulebook singleton."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_config()
    return _CONFIG
