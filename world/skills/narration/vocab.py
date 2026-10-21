"""Frozen narration vocabulary: bounds, band tables, and row records.

Authored narration is presentation only. This module carries no game rule,
reads no clock, and imports no ``world.rules`` module; the selector and the
catalog use these records without ever touching gameplay state.

Bounds mirror the published combat-beat contract:

- :data:`MAX_LINE_CODE_POINTS` is the authored-line budget. A line's literal
  code points plus :data:`MAX_NAME_CODE_POINTS` per participant slot must not
  exceed it.
- :data:`MAX_NAME_CODE_POINTS` is the widest authored participant-name bound
  in the repository (character creation caps names at 64 code points).
- :data:`MAX_SLOTS` is the authored participant-slot budget (``{actor}`` and
  ``{target}``).
- :data:`MAX_COMPACT_CODE_POINTS` bounds the participant-free fallback.
- :data:`MAX_RENDERED_CODE_POINTS` is the settled beat-text bound the
  selector re-checks against actual names. ``world.rules.combat_beats`` owns
  the published constant; a narration test pins the two equal.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Mapping

MAX_LINE_CODE_POINTS = 248
MAX_NAME_CODE_POINTS = 80
MAX_SLOTS = 2
MAX_COMPACT_CODE_POINTS = 64
MAX_RENDERED_CODE_POINTS = 256

_ASCII_DIGITS = frozenset("0123456789")
_ALLOWED_SLOTS = frozenset({"actor", "target"})


class NarrationCatalogError(ValueError):
    """An authored narration row violates the catalog contract."""


@dataclass(frozen=True)
class BandTable:
    """One ascending, closed qualitative band table.

    ``bands`` holds ``(band_id, upper_ratio)`` pairs in ascending order; the
    final upper bound is exactly ``1.0`` so every finite non-negative ratio
    lands in a band.
    """

    name: str
    bands: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        _validate_band_table(self.name, self.bands)


@dataclass(frozen=True)
class NarrationBands:
    """The damage, heal, and pleasure band tables used at construction."""

    damage: BandTable
    heal: BandTable
    pleasure: BandTable


@dataclass(frozen=True)
class NarrationRow:
    """One authored narration row.

    ``key`` is a shipped skill key or a family-tier key. ``action`` holds the
    action clauses (one participant slot at most, so it can compose with an
    outcome clause inside the slot budget). ``kind_lines`` maps an entry kind
    to its authored override clauses; an empty mapping leaves the kind pools
    in charge. ``performer_lines`` and ``participant_lines`` map an entry kind
    to the clause used when that entry's participant is the cast's actor or
    another participant respectively; a sexual act uses them to name its own
    bodily focus, which the shared role pools cannot know.
    """

    key: str
    action: tuple[str, ...] = ()
    kind_lines: Mapping[str, tuple[str, ...]] = MappingProxyType({})
    performer_lines: Mapping[str, tuple[str, ...]] = MappingProxyType({})
    participant_lines: Mapping[str, tuple[str, ...]] = MappingProxyType({})

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key:
            raise NarrationCatalogError("narration row key must be non-empty")
        if not isinstance(self.action, tuple) or any(
            not isinstance(line, str) for line in self.action
        ):
            raise NarrationCatalogError(
                f"narration row {self.key!r} action must be a tuple of strings"
            )
        object.__setattr__(
            self,
            "kind_lines",
            _frozen_kind_lines(self.key, "kind_lines", self.kind_lines),
        )
        object.__setattr__(
            self,
            "performer_lines",
            _frozen_kind_lines(self.key, "performer_lines", self.performer_lines),
        )
        object.__setattr__(
            self,
            "participant_lines",
            _frozen_kind_lines(
                self.key, "participant_lines", self.participant_lines
            ),
        )


def _frozen_kind_lines(
    row_key: str, field: str, lines_by_kind: Mapping[str, tuple[str, ...]]
) -> Mapping[str, tuple[str, ...]]:
    """Return one row field as an immutable kind-to-clauses mapping."""
    if not isinstance(lines_by_kind, Mapping):
        raise NarrationCatalogError(
            f"narration row {row_key!r} {field} must be a mapping"
        )
    frozen: dict[str, tuple[str, ...]] = {}
    for kind, lines in lines_by_kind.items():
        if not isinstance(kind, str) or not kind:
            raise NarrationCatalogError(
                f"narration row {row_key!r} declares an invalid entry kind"
            )
        if not isinstance(lines, tuple) or any(
            not isinstance(line, str) for line in lines
        ):
            raise NarrationCatalogError(
                f"narration row {row_key!r} {field} {kind!r} must be a "
                "tuple of strings"
            )
        frozen[kind] = lines
    return MappingProxyType(frozen)


@dataclass(frozen=True)
class RoleClause:
    """One pooled narration entry with a performer and a participant clause.

    The performer clause speaks in the acting body's own voice; the
    participant clause describes a body that received the act. A pooled entry
    keyed by a lifetime counter carries both so the selector can pick by role
    without a second table.
    """

    performer: tuple[str, ...]
    participant: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("performer", "participant"):
            lines = getattr(self, name)
            if not isinstance(lines, tuple) or not lines:
                raise NarrationCatalogError(
                    f"role clause {name} must be a non-empty tuple of strings"
                )
            if any(not isinstance(line, str) for line in lines):
                raise NarrationCatalogError(
                    f"role clause {name} must be a tuple of strings"
                )

    def for_role(self, performer: bool) -> tuple[str, ...]:
        """Return the clause voiced for the performer or the participant."""
        return self.performer if performer else self.participant


def slot_count(line: str) -> int:
    """Return the number of participant placeholders in one authored line."""
    return sum(line.count("{" + slot + "}") for slot in _ALLOWED_SLOTS)


def literal_code_points(line: str) -> int:
    """Return the line's code points minus its placeholder text."""
    literal = line
    for slot in _ALLOWED_SLOTS:
        literal = literal.replace("{" + slot + "}", "")
    return sum(1 for _ in literal)


def contains_ascii_digit(line: str) -> bool:
    return any(character in _ASCII_DIGITS for character in line)


def validate_line(
    line: str,
    *,
    owner: str,
    compact: bool = False,
    max_slots: int = MAX_SLOTS,
) -> None:
    """Fail closed when one authored line breaks the authoring contract."""
    if not isinstance(line, str) or not line:
        raise NarrationCatalogError(f"{owner}: narration line must be non-empty")
    if contains_ascii_digit(line):
        raise NarrationCatalogError(
            f"{owner}: narration line carries an ASCII digit: {line!r}"
        )
    if "{data" in line or "{data[" in line:
        raise NarrationCatalogError(
            f"{owner}: narration line references entry data: {line!r}"
        )
    for token in _placeholders(line):
        if token not in _ALLOWED_SLOTS:
            raise NarrationCatalogError(
                f"{owner}: narration line declares unknown placeholder "
                f"{{{token}}}: {line!r}"
            )
    slots = slot_count(line)
    if compact:
        if slots:
            raise NarrationCatalogError(
                f"{owner}: compact fallback must declare no participant slot: "
                f"{line!r}"
            )
        if sum(1 for _ in line) > MAX_COMPACT_CODE_POINTS:
            raise NarrationCatalogError(
                f"{owner}: compact fallback exceeds {MAX_COMPACT_CODE_POINTS} "
                f"code points: {line!r}"
            )
        return
    if slots > max_slots:
        raise NarrationCatalogError(
            f"{owner}: narration line declares {slots} participant slots, "
            f"budget is {max_slots}: {line!r}"
        )
    if literal_code_points(line) + MAX_NAME_CODE_POINTS * slots > MAX_LINE_CODE_POINTS:
        raise NarrationCatalogError(
            f"{owner}: narration line exceeds the authored length bound: {line!r}"
        )


def composed_fits(action: str, outcome: str) -> bool:
    """Return whether one action-plus-outcome pair fits the authored bound."""
    slots = slot_count(action) + slot_count(outcome)
    if slots > MAX_SLOTS:
        return False
    literal = literal_code_points(action) + literal_code_points(outcome)
    return literal + MAX_NAME_CODE_POINTS * slots <= MAX_LINE_CODE_POINTS


def _placeholders(line: str) -> tuple[str, ...]:
    tokens: list[str] = []
    start = 0
    while True:
        opening = line.find("{", start)
        if opening < 0:
            return tuple(tokens)
        closing = line.find("}", opening + 1)
        if closing < 0:
            return tuple(tokens)
        tokens.append(line[opening + 1:closing])
        start = closing + 1


def _validate_band_table(name: str, bands: tuple[tuple[str, float], ...]) -> None:
    if not isinstance(bands, tuple) or not bands:
        raise NarrationCatalogError(f"{name} band table must be a non-empty tuple")
    previous = 0.0
    for band_id, upper in bands:
        if not isinstance(band_id, str) or not band_id:
            raise NarrationCatalogError(f"{name} band id must be non-empty")
        if isinstance(upper, bool) or not isinstance(upper, (int, float)):
            raise NarrationCatalogError(f"{name} band {band_id!r} bound is not numeric")
        if not isfinite(upper) or upper <= 0 or upper > 1:
            raise NarrationCatalogError(
                f"{name} band {band_id!r} bound must be finite and inside (0, 1]"
            )
        if upper <= previous:
            raise NarrationCatalogError(
                f"{name} band {band_id!r} bound must be strictly ascending"
            )
        previous = float(upper)
    if previous != 1.0:
        raise NarrationCatalogError(f"{name} band table must be closed by 1.0")


def band_for(table: BandTable, ratio: float | None) -> str:
    """Return the band id for one ratio, degrading to the middle band."""
    if ratio is None or not isfinite(ratio):
        return table.bands[len(table.bands) // 2][0]
    for band_id, upper in table.bands:
        if ratio <= upper:
            return band_id
    return table.bands[-1][0]


DAMAGE_BANDS = BandTable(
    "damage",
    (
        ("graze", 0.05),
        ("light", 0.15),
        ("solid", 0.30),
        ("heavy", 0.50),
        ("dire", 1.0),
    ),
)

HEAL_BANDS = BandTable(
    "heal",
    (
        ("minor", 0.10),
        ("restoring", 0.30),
        ("bountiful", 1.0),
    ),
)

PLEASURE_BANDS = BandTable(
    "pleasure",
    (
        ("faint", 0.10),
        ("clear", 0.30),
        ("strong", 0.60),
        ("overwhelming", 1.0),
    ),
)

DEFAULT_BANDS = NarrationBands(DAMAGE_BANDS, HEAL_BANDS, PLEASURE_BANDS)


__all__ = [
    "DAMAGE_BANDS",
    "DEFAULT_BANDS",
    "HEAL_BANDS",
    "MAX_COMPACT_CODE_POINTS",
    "MAX_LINE_CODE_POINTS",
    "MAX_NAME_CODE_POINTS",
    "MAX_RENDERED_CODE_POINTS",
    "MAX_SLOTS",
    "BandTable",
    "NarrationBands",
    "NarrationCatalogError",
    "NarrationRow",
    "PLEASURE_BANDS",
    "RoleClause",
    "band_for",
    "composed_fits",
    "contains_ascii_digit",
    "literal_code_points",
    "slot_count",
    "validate_line",
]
