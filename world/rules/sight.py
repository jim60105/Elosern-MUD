"""Pure wilderness sight rules: light phase, ground radius, disc and markers.

``rulebook/sight.yaml`` is the single authority for every light phase, ground
sight radius, sighting factor and anonymous silhouette. This module turns that
policy into pure projections:

- :func:`light_phase` maps one calendar hour to a named phase;
- :func:`ground_radius` derives the observer's ground-sight radius from the
  cell's terrain row, elevation prominence tier and authored vantage holding;
- :func:`in_ground_disc` is the one radius predicate;
- :func:`distant_markers` projects the transient sighting markers of the
  current phase.

Every function takes immutable inputs and a policy, writes nothing, and never
lights a district: seeing a landmark is not visiting it. Terrain, elevation and
district registration are read only by the thin runtime seam at the bottom of
this module, so the rules above stay testable with synthetic policies.

Authored values live in the rulebook, never here, and the initial rules are the
approved sight design §3 and §6: a boundary hour belongs to the phase that
starts at it, the canopy suppresses the prominence bonus (a vantage landmark
stays eligible), the maximum ground radius is
:data:`MAX_GROUND_SIGHT_RADIUS`, a source inside live ground sight is not a
distant marker, and an observer under a canopy sees none at all.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

RULEBOOK_PATH = Path(__file__).parent / "rulebook" / "sight.yaml"

#: The hard ceiling of the approved design: no policy, terrain, tier or vantage
#: combination may derive a larger ground radius.
MAX_GROUND_SIGHT_RADIUS = 8

#: The three radius columns every table is read with. Dusk and dawn share the
#: twilight column.
PHASE_COLUMNS = ("day", "twilight", "night")

#: Anchor kinds never disclosed as a distant source: an elven village and a
#: dungeon are discovered by visiting them, never by looking at the horizon.
HIDDEN_ANCHOR_KINDS = frozenset({"elven_village", "dungeon"})

#: The non-hidden settlement kinds the silhouette policy must cover. It is the
#: published anchor vocabulary minus :data:`HIDDEN_ANCHOR_KINDS`; a dungeon is
#: not a settlement and is never an automatic source.
SUPPORTED_SETTLEMENT_KINDS = ("capital",)

#: Authored silhouette length bound, counted in Unicode code points.
SILHOUETTE_MAX_CODE_POINTS = 256

#: Distant distances are reported to the nearest this many kilometres.
DISTANCE_ROUNDING_KM = 5

#: The exact wire keys of one marker. A source cell, a target identity and a
#: district key never serialize.
MARKER_KEYS = frozenset({"bearing", "distance_km", "silhouette_zh", "name"})

#: Sixteen compass bearings, north first and clockwise, in Traditional Chinese.
BEARINGS = (
    "北",
    "北北東",
    "東北",
    "東北東",
    "東",
    "東南東",
    "東南",
    "南南東",
    "南",
    "南南西",
    "西南",
    "西南西",
    "西",
    "西北西",
    "西北",
    "北北西",
)

_PHASE_KEYS = frozenset({"name", "start_hour", "column"})
_SILHOUETTE_KEYS = frozenset({"day", "night"})


class SightRulebookError(ValueError):
    """The sight rulebook violates the phase/radius/silhouette contract."""


@dataclass(frozen=True, slots=True)
class GroundSightInputs:
    """The immutable observer facts one ground-radius derivation needs.

    ``terrain`` is a sight terrain row (the region join is published policy),
    ``prominence_tier`` is the elevation runtime's 0..3 tier, and ``vantage`` is
    whether the cell holds a ``vantage: true`` district landmark. Woodland and
    deep-forest cells carry the canopy rule; the caller does not pre-clear the
    tier, because the policy owns which rows are canopy.
    """

    terrain: str
    prominence_tier: int
    vantage: bool


@dataclass(frozen=True, slots=True)
class SightPolicy:
    """One validated, immutable sight policy.

    ``phases`` holds ``(name, start_hour, column)`` in rulebook order;
    ``prominence_bonus`` is indexed by elevation tier.
    """

    phases: tuple[tuple[str, int, str], ...]
    terrain_radius: Mapping[str, Mapping[str, int]]
    region_terrain: Mapping[str, str]
    canopy_terrain: frozenset[str]
    prominence_bonus: tuple[Mapping[str, int], ...]
    vantage_radius: Mapping[str, int]
    twilight_factor: float
    settlement_footprint_factor: Mapping[str, float]
    settlement_silhouettes: Mapping[str, Mapping[str, str]]

    def phase_for_hour(self, hour: int) -> tuple[str, str]:
        """The ``(name, column)`` of the phase ``hour`` falls in.

        A boundary hour belongs to the phase that starts at it: the winner is
        the entry with the greatest ``start_hour`` at or below ``hour``,
        wrapping through midnight.
        """

        best: tuple[str, int, str] | None = None
        for entry in self.phases:
            start = entry[1]
            reached = hour - start if hour >= start else hour - start + 24
            if best is None:
                best = entry
                continue
            best_reached = hour - best[1] if hour >= best[1] else hour - best[1] + 24
            if reached < best_reached:
                best = entry
        if best is None:  # a validated policy always declares a phase
            raise SightRulebookError("sight rulebook: no light phase is declared")
        return best[0], best[2]

    def column_for_phase(self, name: str) -> str:
        """The radius column of the named phase."""

        for entry in self.phases:
            if entry[0] == name:
                return entry[2]
        raise SightRulebookError(f"sight rulebook: unknown light phase {name!r}")

    def terrain_for_region(self, region: str) -> str:
        """The sight terrain row of one wilderness region key."""

        try:
            return self.region_terrain[region]
        except KeyError:
            raise SightRulebookError(
                f"sight rulebook: wilderness region {region!r} has no terrain row"
            ) from None


@dataclass(frozen=True, slots=True)
class SightSource:
    """One immutable distant-sighting source.

    ``source_key`` is comparison-only: it decides whether two constructs are the
    same place (an authored landmark that references a settlement and that
    settlement's own automatic source) and never reaches the wire. ``sight_km``
    is the daytime range and ``light_km`` the night (light) range; the twilight
    column reads ``sight_km`` scaled by the policy factor. ``authored`` marks an
    explicitly authored range, which wins a merge over a derived one.
    """

    source_key: str
    cell: tuple[int, int]
    sight_km: float
    light_km: float
    silhouette_day: str
    silhouette_night: str
    district_key: str | None
    authored: bool = False


@dataclass(frozen=True, slots=True)
class SettlementFootprint:
    """One published settlement's automatic-source facts.

    ``occupied_cells`` is the authored wilderness-entry mask area (``#`` count),
    which is exactly ``1`` for a concealed point entry; the footprint's visible
    size is its square root, so a point settlement is never invisible.
    """

    anchor_key: str
    kind: str
    cell: tuple[int, int]
    occupied_cells: int


@dataclass(frozen=True, slots=True)
class LandmarkSighting:
    """One district landmark that may be a distant-sighting source.

    The runtime seam resolves ``cell`` (its wilderness projection) and ``hidden``
    (its anchor kind); this record keeps the authored range and silhouette, so
    the filtering and merging below stay pure and testable with synthetic rows.
    """

    source_key: str
    cell: tuple[int, int]
    district_key: str
    sight_km: float
    light_km: float
    silhouette_zh: str
    hidden: bool = False


# -- policy loading ---------------------------------------------------------
def _number(value: Any, label: str) -> float:
    """One finite non-negative number; booleans never count as numbers."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SightRulebookError(f"sight rulebook: {label} must be a number")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise SightRulebookError(
            f"sight rulebook: {label} must be finite and non-negative, got {value!r}"
        ) from None
    if not math.isfinite(number) or number < 0:
        raise SightRulebookError(
            f"sight rulebook: {label} must be finite and non-negative, got {value!r}"
        )
    return number


def _radius(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SightRulebookError(f"sight rulebook: {label} must be an integer radius")
    if not 0 <= value <= MAX_GROUND_SIGHT_RADIUS:
        raise SightRulebookError(
            f"sight rulebook: {label} must be inside 0..{MAX_GROUND_SIGHT_RADIUS}, "
            f"got {value!r}"
        )
    return value


def _columns(value: Any, label: str) -> Mapping[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(PHASE_COLUMNS):
        raise SightRulebookError(
            f"sight rulebook: {label} must declare exactly {list(PHASE_COLUMNS)}"
        )
    return MappingProxyType(
        {column: _radius(value[column], f"{label}.{column}") for column in PHASE_COLUMNS}
    )


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SightRulebookError(f"sight rulebook: {label} must be a mapping")
    return value


def _silhouette(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SightRulebookError(f"sight rulebook: {label} must be non-blank text")
    if len(value) > SILHOUETTE_MAX_CODE_POINTS:
        raise SightRulebookError(
            f"sight rulebook: {label} exceeds {SILHOUETTE_MAX_CODE_POINTS} code points"
        )
    return value


def load_policy(path: str | Path | None = None) -> SightPolicy:
    """Load and validate one sight policy document.

    Validation is closed: unknown keys, malformed or duplicate phases, unknown
    radius columns or terrain rows, radii outside 0..8, non-finite or negative
    factors, a reachable combination above the maximum radius, and missing,
    blank or over-bound settlement-kind silhouettes all reject the policy.
    """

    source = RULEBOOK_PATH if path is None else Path(path)
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise SightRulebookError("sight rulebook: the document must be a mapping")
    expected = {
        "phases",
        "terrain_radius",
        "region_terrain",
        "canopy_terrain",
        "prominence_bonus",
        "vantage_radius",
        "twilight_factor",
        "settlement_footprint_factor",
        "settlement_silhouettes",
    }
    if set(document) != expected:
        raise SightRulebookError(
            "sight rulebook: top-level keys must be exactly "
            f"{sorted(expected)}, got {sorted(document)}"
        )

    raw_phases = document["phases"]
    if not isinstance(raw_phases, list) or not raw_phases:
        raise SightRulebookError("sight rulebook: phases must be a non-empty list")
    phases: list[tuple[str, int, str]] = []
    for raw in raw_phases:
        if not isinstance(raw, Mapping) or set(raw) != _PHASE_KEYS:
            raise SightRulebookError(
                "sight rulebook: each phase declares exactly "
                f"{sorted(_PHASE_KEYS)}, got {raw!r}"
            )
        name, start, column = raw["name"], raw["start_hour"], raw["column"]
        if not isinstance(name, str) or not name:
            raise SightRulebookError("sight rulebook: phase names must be non-empty")
        if isinstance(start, bool) or not isinstance(start, int) or not 0 <= start <= 23:
            raise SightRulebookError(
                f"sight rulebook: phase {name!r} start_hour must be an hour 0..23"
            )
        if column not in PHASE_COLUMNS:
            raise SightRulebookError(
                f"sight rulebook: phase {name!r} column must be one of {list(PHASE_COLUMNS)}"
            )
        phases.append((name, start, column))
    names = [entry[0] for entry in phases]
    starts = [entry[1] for entry in phases]
    if len(set(names)) != len(names):
        raise SightRulebookError(f"sight rulebook: duplicate phase names {names}")
    if len(set(starts)) != len(starts):
        raise SightRulebookError(f"sight rulebook: duplicate phase start hours {starts}")

    raw_terrain = _mapping(document["terrain_radius"], "terrain_radius")
    if not raw_terrain:
        raise SightRulebookError("sight rulebook: terrain_radius must not be empty")
    terrain_radius = MappingProxyType(
        {str(row): _columns(value, f"terrain_radius.{row}") for row, value in raw_terrain.items()}
    )
    canopy = document["canopy_terrain"]
    if not isinstance(canopy, list) or any(not isinstance(row, str) for row in canopy):
        raise SightRulebookError("sight rulebook: canopy_terrain must be a list of rows")
    canopy_terrain = frozenset(canopy)
    unknown_canopy = sorted(canopy_terrain - set(terrain_radius))
    if unknown_canopy:
        raise SightRulebookError(
            f"sight rulebook: canopy rows without a terrain table: {unknown_canopy}"
        )

    raw_regions = _mapping(document["region_terrain"], "region_terrain")
    if not raw_regions:
        raise SightRulebookError("sight rulebook: region_terrain must not be empty")
    region_terrain: dict[str, str] = {}
    for region, row in raw_regions.items():
        if not isinstance(region, str) or not region:
            raise SightRulebookError("sight rulebook: region keys must be non-empty")
        if row not in terrain_radius:
            raise SightRulebookError(
                f"sight rulebook: region {region!r} names unknown terrain row {row!r}"
            )
        region_terrain[region] = str(row)

    raw_bonus = document["prominence_bonus"]
    if not isinstance(raw_bonus, list) or len(raw_bonus) != 4:
        raise SightRulebookError(
            "sight rulebook: prominence_bonus must declare exactly 4 tiers"
        )
    prominence_bonus = tuple(
        _columns(value, f"prominence_bonus[{tier}]") for tier, value in enumerate(raw_bonus)
    )

    vantage_radius = _columns(document["vantage_radius"], "vantage_radius")
    twilight_factor = _number(document["twilight_factor"], "twilight_factor")
    raw_footprint = _mapping(
        document["settlement_footprint_factor"], "settlement_footprint_factor"
    )
    if set(raw_footprint) != {"day", "night"}:
        raise SightRulebookError(
            "sight rulebook: settlement_footprint_factor declares exactly day and night"
        )
    settlement_footprint_factor = MappingProxyType(
        {
            column: _number(raw_footprint[column], f"settlement_footprint_factor.{column}")
            for column in ("day", "night")
        }
    )

    raw_silhouettes = _mapping(
        document["settlement_silhouettes"], "settlement_silhouettes"
    )
    if set(raw_silhouettes) != set(SUPPORTED_SETTLEMENT_KINDS):
        raise SightRulebookError(
            "sight rulebook: settlement_silhouettes must cover exactly the supported "
            f"non-hidden settlement kinds {list(SUPPORTED_SETTLEMENT_KINDS)}, "
            f"got {sorted(raw_silhouettes)}"
        )
    silhouettes: dict[str, Mapping[str, str]] = {}
    for kind, value in raw_silhouettes.items():
        if not isinstance(value, Mapping) or set(value) != _SILHOUETTE_KEYS:
            raise SightRulebookError(
                f"sight rulebook: settlement_silhouettes.{kind} declares exactly "
                f"{sorted(_SILHOUETTE_KEYS)}"
            )
        silhouettes[kind] = MappingProxyType(
            {
                column: _silhouette(value[column], f"settlement_silhouettes.{kind}.{column}")
                for column in ("day", "night")
            }
        )

    policy = SightPolicy(
        phases=tuple(phases),
        terrain_radius=terrain_radius,
        region_terrain=MappingProxyType(region_terrain),
        canopy_terrain=canopy_terrain,
        prominence_bonus=prominence_bonus,
        vantage_radius=vantage_radius,
        twilight_factor=twilight_factor,
        settlement_footprint_factor=settlement_footprint_factor,
        settlement_silhouettes=MappingProxyType(silhouettes),
    )
    _validate_reachable_radius(policy)
    return policy


def _validate_reachable_radius(policy: SightPolicy) -> None:
    """Reject a policy whose every-combination radius can exceed the maximum.

    Each individual table value is legal, yet a terrain row and a prominence
    bonus can still add up past :data:`MAX_GROUND_SIGHT_RADIUS`; that must be a
    load-time rejection, never a runtime surprise.
    """

    for terrain, row in policy.terrain_radius.items():
        for tier in range(len(policy.prominence_bonus)):
            effective = 0 if terrain in policy.canopy_terrain else tier
            for column in PHASE_COLUMNS:
                radius = max(
                    row[column] + policy.prominence_bonus[effective][column],
                    policy.vantage_radius[column],
                )
                if radius > MAX_GROUND_SIGHT_RADIUS:
                    raise SightRulebookError(
                        "sight rulebook: terrain "
                        f"{terrain!r} tier {effective} column {column} derives radius "
                        f"{radius} above the maximum {MAX_GROUND_SIGHT_RADIUS}"
                    )


#: The shipped policy, validated at import so a broken rulebook fails startup.
POLICY = load_policy()


def _policy(policy: SightPolicy | None) -> SightPolicy:
    return POLICY if policy is None else policy


# -- pure sight rules -------------------------------------------------------
def light_phase(calendar: Any, *, policy: SightPolicy | None = None) -> str:
    """The light phase name of one calendar hour (``calendar.hour``)."""

    resolved = _policy(policy)
    hour = getattr(calendar, "hour", None)
    if isinstance(hour, bool) or not isinstance(hour, int) or not 0 <= hour <= 23:
        raise ValueError(f"light phase needs a calendar hour 0..23, got {hour!r}")
    return resolved.phase_for_hour(hour)[0]


def ground_radius(
    calendar: Any,
    inputs: GroundSightInputs,
    *,
    policy: SightPolicy | None = None,
) -> int:
    """The observer's ground-sight radius in cells for the calendar's phase.

    The radius is ``max(terrain + prominence bonus, vantage)``. A canopy row
    forces the prominence tier to 0 before the addition, so a high forest hill
    never widens the view, while an authored vantage landmark stays eligible.
    """

    resolved = _policy(policy)
    if not isinstance(inputs, GroundSightInputs):
        raise TypeError("ground radius needs GroundSightInputs")
    if not isinstance(inputs.terrain, str) or inputs.terrain not in resolved.terrain_radius:
        raise SightRulebookError(
            f"sight rulebook: unknown terrain row {inputs.terrain!r}"
        )
    tier = inputs.prominence_tier
    if isinstance(tier, bool) or not isinstance(tier, int) or not 0 <= tier < len(
        resolved.prominence_bonus
    ):
        raise ValueError(f"prominence tier must be 0..{len(resolved.prominence_bonus) - 1}")
    column = resolved.phase_for_hour(_hour(calendar))[1]
    effective_tier = 0 if inputs.terrain in resolved.canopy_terrain else tier
    terrain_radius = resolved.terrain_radius[inputs.terrain][column]
    vantage = resolved.vantage_radius[column] if inputs.vantage else 0
    radius = max(terrain_radius + resolved.prominence_bonus[effective_tier][column], vantage)
    if radius > MAX_GROUND_SIGHT_RADIUS:
        raise SightRulebookError(
            f"sight rulebook: derived radius {radius} exceeds {MAX_GROUND_SIGHT_RADIUS}"
        )
    return radius


def _hour(calendar: Any) -> int:
    hour = getattr(calendar, "hour", None)
    if isinstance(hour, bool) or not isinstance(hour, int) or not 0 <= hour <= 23:
        raise ValueError(f"sight needs a calendar hour 0..23, got {hour!r}")
    return hour


def in_ground_disc(
    observer: tuple[int, int],
    target: tuple[int, int],
    radius: int,
) -> bool:
    """Whether ``target`` lies in the ground disc of ``radius`` around ``observer``.

    ``dx² + dy² <= (radius + 0.5)²``; radius 0 covers only the observer's own
    cell because a neighbouring cell is already one full cell away.
    """

    if isinstance(radius, bool) or not isinstance(radius, int) or radius < 0:
        raise ValueError(f"ground disc needs a non-negative integer radius, got {radius!r}")
    dx = int(target[0]) - int(observer[0])
    dy = int(target[1]) - int(observer[1])
    reach = radius + 0.5
    return dx * dx + dy * dy <= reach * reach


def bearing_index(degrees: float) -> int:
    """The 16-point sector index of one bearing in degrees clockwise from north.

    A half-sector tie belongs to the clockwise sector: the index is
    ``floor((degrees + 11.25) / 22.5)`` wrapped to 0..15.
    """

    if isinstance(degrees, bool) or not isinstance(degrees, (int, float)):
        raise TypeError("a bearing must be a number of degrees")
    if not math.isfinite(float(degrees)):
        raise ValueError(f"a bearing must be finite, got {degrees!r}")
    sector = 360 / len(BEARINGS)
    return int(math.floor((float(degrees) % 360 + sector / 2) / sector)) % len(BEARINGS)


def bearing_label(observer: tuple[int, int], target: tuple[int, int]) -> str:
    """The 16-point compass label from ``observer`` to ``target``.

    East is the positive x axis and north the positive y axis; the angle is
    measured clockwise from north and a half-sector tie goes clockwise.
    """

    dx = int(target[0]) - int(observer[0])
    dy = int(target[1]) - int(observer[1])
    if dx == 0 and dy == 0:
        return BEARINGS[0]
    return BEARINGS[bearing_index(math.degrees(math.atan2(dx, dy)))]


def rounded_distance_km(distance_km: float) -> int:
    """The nearest multiple of 5 km; a tie rounds upward."""

    if isinstance(distance_km, bool) or not isinstance(distance_km, (int, float)):
        raise TypeError("distance must be a number of kilometres")
    if not math.isfinite(distance_km) or distance_km < 0:
        raise ValueError(f"distance must be finite and non-negative, got {distance_km!r}")
    return DISTANCE_ROUNDING_KM * int(
        math.floor(float(distance_km) / DISTANCE_ROUNDING_KM + 0.5)
    )


def validate_sight_region_coverage(
    region_keys: Iterable[str],
    *,
    policy: SightPolicy | None = None,
) -> None:
    """Reject a published region set this policy cannot classify.

    The region vocabulary is map-owned and loaded from the continent source, so
    the join runs when that geography is published, never at this module's
    import.
    """

    resolved = _policy(policy)
    missing = sorted(set(region_keys) - set(resolved.region_terrain))
    if missing:
        raise SightRulebookError(
            f"sight rulebook: wilderness regions without a terrain row: {missing}"
        )


# -- distant sources --------------------------------------------------------
def settlement_sources(
    placements: Iterable[SettlementFootprint],
    *,
    policy: SightPolicy | None = None,
) -> tuple[SightSource, ...]:
    """The automatic distant sources of every non-hidden settlement.

    Visibility comes from the settlement's footprint size (the square root of
    its occupied cells) times the authored day or night factor, so it scales
    with the settlement instead of naming it. Twilight scales the daytime range
    by the twilight factor at :func:`distant_markers` time. A hidden kind is
    never a source, and the silhouette is selected by kind and light column.
    """

    resolved = _policy(policy)
    sources: list[SightSource] = []
    for placement in placements:
        if placement.kind in HIDDEN_ANCHOR_KINDS:
            continue
        if placement.kind not in resolved.settlement_silhouettes:
            raise SightRulebookError(
                f"sight rulebook: settlement kind {placement.kind!r} has no silhouette row"
            )
        if (
            isinstance(placement.occupied_cells, bool)
            or not isinstance(placement.occupied_cells, int)
            or placement.occupied_cells < 1
        ):
            raise ValueError(
                f"settlement {placement.anchor_key!r} needs at least one occupied cell"
            )
        size = math.sqrt(placement.occupied_cells)
        silhouettes = resolved.settlement_silhouettes[placement.kind]
        sources.append(
            SightSource(
                source_key=f"settlement:{placement.anchor_key}",
                cell=(int(placement.cell[0]), int(placement.cell[1])),
                sight_km=size * resolved.settlement_footprint_factor["day"],
                light_km=size * resolved.settlement_footprint_factor["night"],
                silhouette_day=silhouettes["day"],
                silhouette_night=silhouettes["night"],
                district_key=None,
                authored=False,
            )
        )
    return tuple(sorted(sources, key=lambda source: source.source_key))


def landmark_sources(rows: Iterable[LandmarkSighting]) -> tuple[SightSource, ...]:
    """The distant sources of landmarks with an authored range.

    A hidden place is never a source, and a landmark without an authored range
    produces no marker; both rejections happen here rather than in a caller.
    """

    sources: list[SightSource] = []
    for row in rows:
        if row.hidden:
            continue
        if row.sight_km <= 0 and row.light_km <= 0:
            continue
        if not row.silhouette_zh.strip():
            raise SightRulebookError(
                f"sight rulebook: landmark {row.district_key!r} declares a range without "
                "an authored silhouette"
            )
        sources.append(
            SightSource(
                source_key=row.source_key,
                cell=(int(row.cell[0]), int(row.cell[1])),
                sight_km=float(row.sight_km),
                light_km=float(row.light_km),
                silhouette_day=row.silhouette_zh,
                silhouette_night=row.silhouette_zh,
                district_key=row.district_key,
                authored=True,
            )
        )
    return tuple(sorted(sources, key=lambda source: source.source_key))


def merge_sources(sources: Iterable[SightSource]) -> tuple[SightSource, ...]:
    """Merge sources that name the same place into one marker source.

    Two constructs are the same place when they resolve to the same cell. The
    merged record keeps the largest daytime and night range of the group, so a
    day-only authored landmark never removes a settlement's night light, and
    never drops a phase. Nothing is dropped: merging only widens.

    Silhouettes come from the automatic settlement record when the group holds
    one, because that is the validated kind/phase anonymity of the place; an
    authored landmark silhouette only describes a landmark that is a source on
    its own. The identity and the naming district come from the authored record
    first, then from the lowest ``source_key`` and ``district_key``, so
    iteration order never decides the outcome.
    """

    grouped: dict[tuple[int, int], list[SightSource]] = {}
    for source in sources:
        grouped.setdefault(source.cell, []).append(source)
    merged: list[SightSource] = []
    for cell, group in grouped.items():
        ordered = sorted(
            group,
            key=lambda source: (
                not source.authored,
                source.source_key,
                source.district_key or "",
            ),
        )
        first = ordered[0]
        anonymous = [source for source in ordered if not source.authored]
        silhouette = anonymous[0] if anonymous else first
        merged.append(
            SightSource(
                source_key=first.source_key,
                cell=cell,
                sight_km=max(source.sight_km for source in ordered),
                light_km=max(source.light_km for source in ordered),
                silhouette_day=silhouette.silhouette_day,
                silhouette_night=silhouette.silhouette_night,
                district_key=first.district_key,
                authored=first.authored,
            )
        )
    return tuple(sorted(merged, key=lambda source: (source.cell, source.source_key)))


def visible_distant_sources(
    observer: tuple[int, int],
    calendar: Any,
    sources: Iterable[SightSource],
    *,
    inputs: GroundSightInputs,
    cell_size_km: float,
    policy: SightPolicy | None = None,
) -> tuple[tuple[SightSource, str, float], ...]:
    """The merged distant sources visible from ``observer`` right now.

    This is the single visibility decision behind both the wire markers and
    the travel interrupts' ``landmark_sighted`` comparison: a source is
    visible only while the current phase can see it, only when it lies outside
    live ground sight, and never under a canopy. Each entry carries the merged
    source, its phase silhouette and its distance in kilometres; nothing is
    stored, lit or named here.
    """

    resolved = _policy(policy)
    if not isinstance(inputs, GroundSightInputs):
        raise TypeError("distant sources need GroundSightInputs")
    if inputs.terrain in resolved.canopy_terrain:
        return ()
    if isinstance(cell_size_km, bool) or not isinstance(cell_size_km, (int, float)):
        raise TypeError("cell size must be a number of kilometres")
    if not math.isfinite(float(cell_size_km)) or cell_size_km <= 0:
        raise ValueError(f"cell size must be positive, got {cell_size_km!r}")

    column = resolved.phase_for_hour(_hour(calendar))[1]
    radius = ground_radius(calendar, inputs, policy=resolved)
    visible: list[tuple[SightSource, str, float]] = []
    for source in merge_sources(sources):
        if in_ground_disc(observer, source.cell, radius):
            continue
        if column == "night":
            visibility = source.light_km
            silhouette = source.silhouette_night
        elif column == "twilight":
            visibility = source.sight_km * resolved.twilight_factor
            silhouette = source.silhouette_day
        else:
            visibility = source.sight_km
            silhouette = source.silhouette_day
        distance_cells = math.dist(observer, source.cell)
        distance_km = distance_cells * float(cell_size_km)
        if visibility <= 0 or distance_km > visibility:
            continue
        visible.append((source, silhouette, distance_km))
    return tuple(visible)


def visible_distant_source_keys(
    observer: tuple[int, int],
    calendar: Any,
    sources: Iterable[SightSource],
    *,
    inputs: GroundSightInputs,
    cell_size_km: float,
    policy: SightPolicy | None = None,
) -> frozenset[str]:
    """The internal source keys visible from ``observer`` right now.

    The comparison identity behind ``landmark_sighted``: callers diff two
    committed positions' key sets instead of comparing localized wire markers.
    """

    return frozenset(
        source.source_key
        for source, _silhouette, _distance_km in visible_distant_sources(
            observer,
            calendar,
            sources,
            inputs=inputs,
            cell_size_km=cell_size_km,
            policy=policy,
        )
    )


def distant_markers(
    observer: tuple[int, int],
    calendar: Any,
    sources: Iterable[SightSource],
    lit_districts: Iterable[str],
    *,
    inputs: GroundSightInputs,
    cell_size_km: float,
    district_names: Mapping[str, str] | None = None,
    policy: SightPolicy | None = None,
) -> tuple[dict[str, Any], ...]:
    """The current distant-sighting markers around ``observer``.

    A source produces a marker only while the current phase can see it, only
    when it lies outside live ground sight, and never under a canopy. The marker
    is exactly :data:`MARKER_KEYS`: the bearing, the distance to the nearest
    5 km, the phase silhouette, and the containing district's landmark name,
    present only when that district is lit for the character. The source cell,
    its identity and its district key never leave this function, and nothing is
    stored or lit by reading.
    """

    visible = visible_distant_sources(
        observer,
        calendar,
        sources,
        inputs=inputs,
        cell_size_km=cell_size_km,
        policy=policy,
    )
    if not visible:
        # The canopy short circuit (and an observation with no visible source)
        # answers before the caller's lighting iterable is consumed.
        return ()
    lit = frozenset(lit_districts)
    names = {} if district_names is None else district_names
    markers: list[tuple[tuple[int, int], str, dict[str, Any]]] = []
    for source, silhouette, distance_km in visible:
        name = None
        if source.district_key is not None and source.district_key in lit:
            name = names.get(source.district_key)
        markers.append(
            (
                source.cell,
                source.source_key,
                {
                    "bearing": bearing_label(observer, source.cell),
                    "distance_km": rounded_distance_km(distance_km),
                    "silhouette_zh": silhouette,
                    "name": name,
                },
            )
        )
    markers.sort(key=lambda item: (item[0], item[1]))
    return tuple(marker for _, _, marker in markers)


# -- runtime seams ----------------------------------------------------------
# Everything below reads the published world. The rules above never do.
def sight_terrain_class(region: str, *, policy: SightPolicy | None = None) -> str:
    """The sight terrain row of one published wilderness region key."""

    return _policy(policy).terrain_for_region(region)


def published_vantage_cells() -> frozenset[tuple[int, int]]:
    """Every wilderness cell that holds a ``vantage: true`` district landmark."""

    from world.lore.map_districts import current as districts_current
    from world.maps.static_references import map_reference_index, resolve_static

    bindings = map_reference_index()
    cells: set[tuple[int, int]] = set()
    for district in districts_current().districts.values():
        if not district.vantage:
            continue
        cell = _vantage_cell(district.landmark, bindings)
        if cell is not None:
            cells.add(cell)
    return frozenset(cells)


def published_ground_inputs(cell: tuple[int, int]) -> GroundSightInputs:
    """The committed observer inputs of one wilderness cell.

    The region comes from the published terrain model, the tier from the
    admitted elevation artifact, and the vantage holding from the published
    district landmarks; an unloaded elevation runtime raises instead of
    assuming flat ground.
    """

    from world.maps import elevation, wilderness_provider

    return GroundSightInputs(
        terrain=sight_terrain_class(wilderness_provider.region_for_coordinates(*cell)),
        prominence_tier=elevation.prominence_tier(cell[0], cell[1]),
        vantage=cell in published_vantage_cells(),
    )


def ground_radius_at(cell: tuple[int, int], calendar: Any) -> int:
    """The committed ground-sight radius of one wilderness cell."""

    return ground_radius(calendar, published_ground_inputs(cell))


def published_distant_sources() -> tuple[SightSource, ...]:
    """Every committed distant source: authored landmarks and settlements."""

    from world.lore.anchors import anchor_geography, anchors
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

    return distant_sources(
        _published_landmark_rows(),
        settlement_placements(
            {
                key: anchor.kind.value
                for key, anchor in anchors().items()
                if key in anchor_geography()
            },
            {key: tuple(row.cell) for key, row in anchor_geography().items()},
            {
                key: entry.hash_cell_count
                for key, entry in WILDERNESS_ENTRY_REGISTRY.items()
            },
        ),
    )


def published_settlement_sources() -> tuple[SightSource, ...]:
    """The committed automatic sources of every non-hidden settlement."""

    from world.lore.anchors import anchor_geography, anchors
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

    return settlement_sources(
        settlement_placements(
            {key: anchor.kind.value for key, anchor in anchors().items()},
            {key: tuple(row.cell) for key, row in anchor_geography().items()},
            {
                key: entry.hash_cell_count
                for key, entry in WILDERNESS_ENTRY_REGISTRY.items()
            },
        )
    )


def settlement_placements(
    kinds: Mapping[str, str],
    cells: Mapping[str, tuple[int, int]],
    occupied_cells: Mapping[str, int],
) -> tuple[SettlementFootprint, ...]:
    """The automatic-source facts of every published wilderness entry.

    Pure projection over three read-only views: an anchor without a geographic
    cell or without an entry contributes no placement, so a partially published
    world never invents a source.
    """

    return tuple(
        SettlementFootprint(
            anchor_key=anchor_key,
            kind=kinds[anchor_key],
            cell=(int(cells[anchor_key][0]), int(cells[anchor_key][1])),
            occupied_cells=occupied_cells[anchor_key],
        )
        for anchor_key in sorted(occupied_cells)
        if anchor_key in kinds and anchor_key in cells
    )


def distant_sources(
    landmark_rows: Iterable[LandmarkSighting],
    placements: Iterable[SettlementFootprint],
    *,
    policy: SightPolicy | None = None,
) -> tuple[SightSource, ...]:
    """The merged sources of authored landmarks and automatic settlements."""

    return merge_sources(
        (
            *landmark_sources(landmark_rows),
            *settlement_sources(placements, policy=policy),
        )
    )


def _vantage_cell(landmark: Any, bindings: Any) -> tuple[int, int] | None:
    """The wilderness cell a ``vantage: true`` landmark actually stands on.

    Unlike a sighting source, which normalises a settlement-node landmark to
    the settlement's anchor cell, the widened-viewpoint eligibility belongs to
    the land the referenced node itself occupies: a vantage landmark on a
    non-anchor node widens sight there and follows the node when it moves.
    """

    if landmark.domain != "settlement_node":
        return _landmark_cell(landmark, bindings)
    projected = _settlement_node_position_m(landmark)
    if projected is None:
        return None
    from elosern_map_core.geometry import cell_of_position

    return cell_of_position(projected)


def _settlement_node_position_m(landmark: Any) -> tuple[float, float] | None:
    """One settlement node's current absolute continental position in metres."""

    from elosern_map_core.geometry import local_to_world_m
    from world.lore.anchors import anchor_geography
    from world.maps.map_data import current as settlements_current

    anchor_key = _location_ref_for_map_id(landmark.map_id)
    if anchor_key is None or anchor_key not in anchor_geography():
        return None
    snapshot = settlements_current()
    graph = snapshot.graphs.get(landmark.map_id)
    frame = snapshot.local_frame_anchors.get(anchor_key)
    if graph is None or frame is None:
        return None
    node = graph.nodes.get(landmark.object_id)
    if node is None:
        return None
    return local_to_world_m(
        anchor_geography()[anchor_key].cell, frame.local_anchor_m, node.coordinate
    )


def visible_distant_markers(
    character: Any,
    cell: tuple[int, int],
    calendar: Any,
) -> tuple[dict[str, Any], ...]:
    """Read-only distant markers for one character standing on ``cell``.

    Reads the character's map knowledge for lit districts only; it writes
    nothing, ticks no clock and never lights a district.
    """

    from world.lore.map_districts import current as districts_current
    from world.maps.wilderness_provider import WILDERNESS_KM_PER_CELL
    from world.rules.map_district_lighting import lit_district_keys

    registry = districts_current().districts
    return distant_markers(
        cell,
        calendar,
        published_distant_sources(),
        lit_district_keys(character, registry),
        inputs=published_ground_inputs(cell),
        cell_size_km=WILDERNESS_KM_PER_CELL,
        district_names={key: row.landmark_name_zh for key, row in registry.items()},
    )


def _landmark_cell(landmark: Any, bindings: Any) -> tuple[int, int] | None:
    """One qualified district landmark's wilderness cell, or ``None``.

    A wilderness-cell or location landmark is its own cell; a settlement-node
    landmark projects onto the settlement's geographic anchor cell, so a
    landmark that references a settlement and that settlement's automatic source
    name the same place.
    """

    from world.lore.anchors import anchor_geography
    from world.maps.static_references import resolve_static

    if landmark.domain in ("wilderness_cell", "location"):
        resolved = resolve_static(landmark, index=bindings)
        return None if resolved.cell is None else (resolved.cell[0], resolved.cell[1])
    if landmark.domain == "settlement_node":
        anchor_key = _location_ref_for_map_id(landmark.map_id)
        if anchor_key is None or anchor_key not in anchor_geography():
            return None
        geography = anchor_geography()[anchor_key]
        return (geography.cell[0], geography.cell[1])
    return None


def _published_landmark_rows() -> tuple[LandmarkSighting, ...]:
    """Every committed district landmark that may be a distant source."""

    from world.lore.anchors import anchors
    from world.lore.map_districts import current as districts_current
    from world.maps.static_references import map_reference_index

    bindings = map_reference_index()
    rows: list[LandmarkSighting] = []
    for key, district in districts_current().districts.items():
        cell = _landmark_cell(district.landmark, bindings)
        if cell is None:
            continue
        anchor_key = _landmark_anchor_key(district.landmark)
        hidden = bool(
            anchor_key
            and anchor_key in anchors()
            and anchors()[anchor_key].kind.value in HIDDEN_ANCHOR_KINDS
        )
        rows.append(
            LandmarkSighting(
                source_key=(
                    f"settlement:{anchor_key}"
                    if anchor_key is not None
                    else f"landmark:{key}"
                ),
                cell=cell,
                district_key=key,
                sight_km=float(district.sight_km or 0.0),
                light_km=float(district.light_km or 0.0),
                silhouette_zh=district.silhouette_zh or "",
                hidden=hidden,
            )
        )
    return tuple(rows)


def _landmark_anchor_key(landmark: Any) -> str | None:
    """The geographic anchor identity a district landmark names, if any."""

    if landmark.domain == "location":
        return landmark.object_id
    if landmark.domain == "settlement_node":
        return _location_ref_for_map_id(landmark.map_id)
    return None


def _location_ref_for_map_id(map_id: str | None) -> str | None:
    """The authored location the settlement map ``map_id`` is bound to."""

    if not map_id:
        return None
    from world.maps.map_data import current as settlements_current

    document = settlements_current().settlements.get(map_id)
    return None if document is None else document.location_ref


__all__ = [
    "BEARINGS",
    "DISTANCE_ROUNDING_KM",
    "HIDDEN_ANCHOR_KINDS",
    "MARKER_KEYS",
    "MAX_GROUND_SIGHT_RADIUS",
    "PHASE_COLUMNS",
    "POLICY",
    "SILHOUETTE_MAX_CODE_POINTS",
    "SUPPORTED_SETTLEMENT_KINDS",
    "GroundSightInputs",
    "LandmarkSighting",
    "SettlementFootprint",
    "SightPolicy",
    "SightRulebookError",
    "SightSource",
    "bearing_index",
    "bearing_label",
    "distant_markers",
    "distant_sources",
    "ground_radius",
    "ground_radius_at",
    "in_ground_disc",
    "landmark_sources",
    "light_phase",
    "load_policy",
    "merge_sources",
    "published_distant_sources",
    "published_ground_inputs",
    "published_settlement_sources",
    "published_vantage_cells",
    "rounded_distance_km",
    "settlement_placements",
    "settlement_sources",
    "sight_terrain_class",
    "validate_sight_region_coverage",
    "visible_distant_source_keys",
    "visible_distant_sources",
    "visible_distant_markers",
]
