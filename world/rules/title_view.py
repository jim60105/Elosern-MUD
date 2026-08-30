"""Pure bounded codex read model for the title 冊 (title-codex-removal D5/D7).

The view is a projection over the lore registry, ``db.title_collection``,
``db.title_equipped``, and ``db.pending_title_ballot`` — it adds no persistent
state and mutates nothing. Fixed rows render in registry order carrying the
authored ``hint_zh`` while locked and ``flavor_zh`` once unlocked (never both);
epithet rows render newest-first with their basis quote, an equipped flag, and
the server-derived ``can_remove`` verdict (the client renders the flag and
evaluates no gate rule of its own). Every string respects the caller-passed
maxima; the shipped ``TITLE_MAX_DISPLAY_CHARS`` equals the epithet storage cap
so a rendered action identifier is never a truncated non-matching string.

Strictness mirrors the rules module: malformed title state raises
``TitleDataError`` (fail closed, the presenter maps it to the unavailable
form), while the pending ballot — a separate surface with its own degradation
discipline — reads through ``safe_pending_ballot`` so a corrupt ballot hides
only the 「提名中」 tab and never contaminates the title rows.
"""

from dataclasses import dataclass
from typing import Any

from world.lore.titles import FIXED_TITLE_REGISTRY
from world.rules.titles import (
    MAX_FULL_TITLE_CODE_POINTS,
    TitleDataError,
    compose_full_title,
    read_title_state,
    safe_pending_ballot,
)

# Wire bounds owned here and mirrored by the WebClient panel validator, the
# JS validator, and the boundary tests (the four mirrors every OOB surface
# keeps). Display equals the epithet storage cap (64): a fixed registry
# display is capped at 63, an epithet display at 64, and the composed
# full-title wire bound is exactly 63 + 1 + 64 = 128, so shipping these caps
# never truncates an addressable identifier and never overflows the compose.
TITLE_MAX_ROWS = 50
TITLE_MAX_DISPLAY_CHARS = 64
TITLE_MAX_BASIS_CHARS = 160


@dataclass(frozen=True)
class FixedTitleRowView:
    """One registry row: locked rows carry hint, unlocked rows carry flavor."""

    key: str
    display: str
    category: str
    hint: str
    flavor: str
    unlocked: bool
    granted_tick: int


@dataclass(frozen=True)
class EpithetRowView:
    """One banked epithet: quote, equipment star, server-computed removal flag."""

    display: str
    basis: str
    granted_tick: int
    equipped: bool
    can_remove: bool


@dataclass(frozen=True)
class TitleCodexView:
    """The whole codex; counters describe the registry, not the truncated rows."""

    fixed_rows: tuple[FixedTitleRowView, ...]
    epithet_rows: tuple[EpithetRowView, ...]
    equipped: dict[str, str | None]
    full_title: str
    unlocked: int
    total: int
    pending_ballot: tuple[dict[str, str], ...]


def _clip(value: str, maximum: int) -> str:
    """Clip to a contiguous prefix without ever raising on short strings."""
    return value[:maximum]


def _newest_first(
    entries: list[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Epithet entries newest-first by ``granted_tick``.

    Ties keep reverse collection order (a later bank sits later in the stored
    list), so the render is deterministic even for equal ticks.
    """
    return tuple(
        entry
        for _, entry in sorted(
            enumerate(entries),
            key=lambda pair: (pair[1]["granted_tick"], pair[0]),
            reverse=True,
        )
    )


def build_title_codex_view(
    character: Any,
    *,
    max_rows: int = TITLE_MAX_ROWS,
    max_display_chars: int = TITLE_MAX_DISPLAY_CHARS,
    max_basis_chars: int = TITLE_MAX_BASIS_CHARS,
) -> TitleCodexView:
    """Build the pure codex view; strict title reads, safe ballot read.

    Repeatable and byte-identical while state is unchanged. Malformed
    collection/equip state propagates ``TitleDataError``; a malformed ballot
    degrades to an empty ballot tab only.
    """
    collection, equipped = read_title_state(character)
    granted_by_key = {
        entry["key"]: entry["granted_tick"]
        for entry in collection
        if entry["kind"] == "fixed"
    }
    banked_keys = frozenset(granted_by_key)

    fixed_rows: list[FixedTitleRowView] = []
    unlocked = 0
    for definition in FIXED_TITLE_REGISTRY.values():
        is_unlocked = definition.key in banked_keys
        if is_unlocked:
            unlocked += 1
        fixed_rows.append(
            FixedTitleRowView(
                key=definition.key,
                display=_clip(definition.display_name_zh, max_display_chars),
                category=definition.category.value,
                hint="" if is_unlocked else _clip(definition.hint_zh, max_basis_chars),
                flavor=(
                    _clip(definition.flavor_zh, max_basis_chars)
                    if is_unlocked
                    else ""
                ),
                unlocked=is_unlocked,
                granted_tick=granted_by_key.get(definition.key, 0),
            )
        )

    epithet_entries = [
        entry for entry in collection if entry["kind"] == "epithet"
    ]
    multi_epithet = len(epithet_entries) > 1
    epithet_rows = tuple(
        EpithetRowView(
            display=_clip(entry["display"], max_display_chars),
            basis=_clip(entry["origin_quote"], max_basis_chars),
            granted_tick=entry["granted_tick"],
            equipped=entry["display"] == equipped["epithet"],
            # Server gate verdict (both gates, precedence-aware): the target
            # is neither the sole epithet nor the equipped one. A
            # two-epithet collection still refuses its equipped row, which
            # the gate also enforces at execution.
            can_remove=multi_epithet and entry["display"] != equipped["epithet"],
        )
        for entry in _newest_first(epithet_entries)
    )

    ballot = tuple(
        {
            "display": _clip(entry["display"], max_display_chars),
            "basis": _clip(entry["basis"], max_basis_chars),
        }
        for entry in safe_pending_ballot(character)
    )

    return TitleCodexView(
        # The row lists clip; the counters and the equipped dict describe the
        # FULL untruncated view, exactly like the lineage header counts.
        fixed_rows=tuple(fixed_rows[:max_rows]),
        epithet_rows=epithet_rows[:max_rows],
        equipped=dict(equipped),
        full_title=_clip(compose_full_title(character), MAX_FULL_TITLE_CODE_POINTS),
        unlocked=unlocked,
        total=len(FIXED_TITLE_REGISTRY),
        pending_ballot=ballot,
    )


__all__ = [
    "TITLE_MAX_BASIS_CHARS",
    "TITLE_MAX_DISPLAY_CHARS",
    "TITLE_MAX_ROWS",
    "EpithetRowView",
    "FixedTitleRowView",
    "TitleCodexView",
    "TitleDataError",
    "build_title_codex_view",
]
