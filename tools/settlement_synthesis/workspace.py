"""The repository adapter: authored sources in, explicit views out.

Everything above this module is a pure function of explicit inputs. This module
is where a checkout becomes those inputs: it loads the authored map sources
through the map core, joins the lore row for each location, and builds one
windowed terrain view per check. It reads only; nothing here writes a file.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from elosern_map_core import (
    AuthoringError,
    discover_source_documents,
    load_authoring_world,
)
from elosern_map_core.authoring import gate_approach_cell, terrain_definition
from elosern_map_core.elevation_codec import decode_tile
from elosern_map_core.reference_context import (
    ReferenceContextError,
    check_workspace_freshness,
    decode_reference_context,
)
from elosern_map_core.terrain import (
    is_inland_water_cell,
    is_land_cell,
    is_walkable_cell,
    rasterize_routes,
)

from tools.settlement_synthesis.budget import size_budget
from tools.settlement_synthesis.generate import (
    GenerationConfig,
    GenerationInput,
)
from tools.settlement_synthesis.geometry import Cell
from tools.settlement_synthesis.roles import DEFAULT_CATALOGUE
from tools.settlement_synthesis.site import SettlementRef, analyse_site
from tools.settlement_synthesis.terrain_view import GridTerrain

#: The committed elevation tile bundle, relative to the workspace root.
ELEVATION_PATH = Path("content") / "maps" / "wilderness_elevation.json"

#: The committed external reference index, relative to the workspace root.
REFERENCE_CONTEXT_PATH = Path("content") / "map-reference-context.json"

#: One 64x64 elevation tile edge, matching the map core's tile format.
TILE_CELLS = 64


class WorkspaceError(Exception):
    """The workspace or one requested identity cannot be read."""


def settlement_path(root: Path, map_id: str) -> Path:
    """The settlement source a generator writes for one map identity."""

    return Path(root) / "content" / "maps" / "settlements" / f"{map_id}.yaml"


def write_atomic(path: Path, text: str) -> None:
    """Write one source atomically: a sibling temporary file, then a replace."""

    path = Path(path)
    temporary = path.with_suffix(".yaml.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def load_lore(path: Path | None) -> Mapping[str, tuple[str | None, int | None]]:
    """Nation and population per location, from lore or one JSON override."""

    if path is None:
        from world.lore.anchors import ANCHOR_LORE

        return {
            location_id: (row.nation_key, row.population)
            for location_id, row in ANCHOR_LORE.items()
        }
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WorkspaceError(f"{path}: {error}") from error
    if not isinstance(data, dict):
        raise WorkspaceError(f"{path}: the lore override must be a JSON object")
    rows: dict[str, tuple[str | None, int | None]] = {}
    for location_id, row in data.items():
        if not isinstance(row, dict):
            raise WorkspaceError(f"{path}: {location_id} is not an object")
        nation = row.get("nation")
        population = row.get("population")
        rows[str(location_id)] = (
            None if nation is None else str(nation),
            None if population is None else int(population),
        )
    return rows


@dataclass(frozen=True)
class WorkspaceView:
    """A loaded workspace: the authored world, its roster and its terrain."""

    root: Path
    world: Any
    roster: tuple[SettlementRef, ...]
    _definition: Any = field(init=False, repr=False, compare=False)
    _route_cells: Mapping[str, frozenset[Cell]] = field(
        init=False, repr=False, compare=False
    )
    _elevation_tiles: Mapping[tuple[int, int], str] = field(
        init=False, repr=False, compare=False
    )
    _decoded_tiles: dict[tuple[int, int], bytes] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        definition = terrain_definition(self.world.continent)
        object.__setattr__(self, "_definition", definition)
        object.__setattr__(
            self,
            "_route_cells",
            {
                name: rasterize_routes({name: route})
                for name, route in definition.waterway_routes.items()
            },
        )
        object.__setattr__(self, "_elevation_tiles", self._load_elevation())
        object.__setattr__(self, "_decoded_tiles", {})

    def _load_elevation(self) -> Mapping[tuple[int, int], str]:
        path = self.root / ELEVATION_PATH
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise WorkspaceError(f"{path}: {error}") from error
        return {
            (int(tile["x"]), int(tile["y"])): str(tile["data"])
            for tile in data.get("tiles", ())
        }

    def _band(self, cell: Cell) -> int:
        tile_x, tile_y = cell[0] // TILE_CELLS, cell[1] // TILE_CELLS
        decoded = self._decoded_tiles.get((tile_x, tile_y))
        if decoded is None:
            data = self._elevation_tiles.get((tile_x, tile_y))
            if data is None:
                return 0
            try:
                decoded = decode_tile(
                    data, tile_x, tile_y, self._definition.frame_cells, TILE_CELLS
                )
            except ValueError as error:
                raise WorkspaceError(str(error)) from error
            self._decoded_tiles[(tile_x, tile_y)] = decoded
        offset = (cell[1] % TILE_CELLS) * TILE_CELLS + (cell[0] % TILE_CELLS)
        return decoded[offset] >> 4

    def location(self, location_id: str) -> SettlementRef:
        """The roster row with this identity, or a ``WorkspaceError``."""

        for ref in self.roster:
            if ref.location_id == location_id:
                return ref
        raise WorkspaceError(f"unknown location {location_id!r}")

    def terrain_window(self, centre: Cell, radius: int) -> GridTerrain:
        """The terrain facts for the inclusive square around ``centre``."""

        definition = self._definition
        frame = definition.frame_cells
        min_x = max(0, centre[0] - radius)
        max_x = min(frame - 1, centre[0] + radius)
        min_y = max(0, centre[1] - radius)
        max_y = min(frame - 1, centre[1] + radius)
        cells = [
            (x, y)
            for y in range(min_y, max_y + 1)
            for x in range(min_x, max_x + 1)
        ]
        land = frozenset(
            cell for cell in cells if is_land_cell(definition, cell)
        )
        inland_water = frozenset(
            cell for cell in cells if is_inland_water_cell(definition, cell)
        )
        impassable = frozenset(
            cell
            for cell in land
            if cell not in inland_water and not is_walkable_cell(definition, cell)
        )
        window_cells = frozenset(cells)
        waterway_cells: dict[str, frozenset[Cell]] = {}
        for name in sorted(self._route_cells):
            fords = frozenset(definition.waterway_fords.get(name, ()))
            waterway_cells[name] = frozenset(
                cell
                for cell in self._route_cells[name]
                if cell not in fords and cell in window_cells
            )
        bands: dict[Cell, int] = {}
        for cell in cells:
            band = self._band(cell)
            if band:
                bands[cell] = band
        return GridTerrain(
            window=(min_x, min_y, max_x, max_y),
            land=land,
            inland_water=inland_water,
            impassable=impassable,
            waterway_routes={
                name: tuple(route)
                for name, route in definition.waterway_routes.items()
            },
            waterway_cells=waterway_cells,
            waterway_fords={
                name: tuple(fords)
                for name, fords in definition.waterway_fords.items()
            },
            bands=bands,
            harbours={
                site_id: tuple(site.cell)
                for site_id, site in self.world.continent.harbor_sites.items()
            },
        )

    def blocked_cells(self, map_id: str) -> frozenset[Cell]:
        """Cells no generated footprint of ``map_id`` may use.

        The union holds every other settlement's mask and gate approaches, every
        location cell that is not this map's own, every harbour site and every
        wilderness district landmark. The own location row is excluded by
        identity, never by subtracting its coordinate afterwards: another source
        may legitimately reserve the same cell.
        """

        locations = self.world.locations.locations
        document = self.world.settlements.get(map_id)
        own_location: str | None = None
        if document is not None:
            own_location = document.location_ref
        elif map_id in locations:
            own_location = map_id

        blocked: set[Cell] = set()
        for location_id, declaration in locations.items():
            if location_id == own_location:
                continue
            blocked.add(tuple(declaration.cell))
        for site in self.world.continent.harbor_sites.values():
            blocked.add(tuple(site.cell))
        for district in self.world.districts.districts.values():
            landmark = district.landmark
            if landmark.domain == "wilderness_cell" and landmark.cell is not None:
                blocked.add(tuple(landmark.cell))
        for settlement_id, other in self.world.settlements.items():
            if settlement_id == map_id:
                continue
            location = locations.get(other.location_ref)
            if location is None:
                continue
            geometry = other.wilderness_geometry(tuple(location.cell))
            if geometry is None:
                continue
            blocked.update(geometry.mask_cells)
            for gate in geometry.gates:
                approach = gate_approach_cell(geometry, gate.return_direction)
                if approach is not None:
                    blocked.add(approach)
        return frozenset(blocked)


def _roster(
    world: Any, lore: Mapping[str, tuple[str | None, int | None]]
) -> tuple[SettlementRef, ...]:
    rows = []
    for location_id, declaration in sorted(world.locations.locations.items()):
        nation, population = lore.get(location_id, (None, None))
        rows.append(
            SettlementRef(
                location_id=location_id,
                kind=declaration.kind,
                nation=nation,
                population=population,
                cell=tuple(declaration.cell),
            )
        )
    return tuple(rows)


def incoming_reference_keys(root: Path) -> frozenset[str] | None:
    """The qualified ids a current reference index names, or ``None``.

    ``None`` means no index is present, or the present one cannot prove which
    external declarations exist: it is stale or incompatible with the current
    external sources. The caller must then protect every existing identity.
    """

    path = Path(root) / REFERENCE_CONTEXT_PATH
    if not path.is_file():
        return None
    try:
        document = decode_reference_context(path.read_text(encoding="utf-8"))
    except (OSError, ReferenceContextError) as error:
        raise WorkspaceError(f"{path}: {error}") from error
    if not check_workspace_freshness(document, root).current:
        return None
    return frozenset(document.incoming_references)


def analysis_input(
    view: WorkspaceView,
    location: SettlementRef,
    *,
    forced_gates: tuple[str, ...] = (),
    map_id: str | None = None,
) -> GenerationInput:
    """The generator input one view yields for one roster row."""

    budget = size_budget(location)
    reach = math.ceil(math.sqrt(budget.footprint_cells) / 2) + 1
    radius = max(
        reach + 6,
        math.ceil(1.5 * budget.envelope_radius_m / 1000) + 6,
        10,
    )
    terrain = view.terrain_window(location.cell, radius)
    site = analyse_site(location, terrain, view.roster)
    identity = location.location_id if map_id is None else map_id
    return GenerationInput(
        map_id=identity,
        location=location,
        site=site,
        budget=budget,
        terrain=terrain,
        blocked=view.blocked_cells(identity),
        catalogue=DEFAULT_CATALOGUE,
        forced_gates=forced_gates,
        config=GenerationConfig(),
    )


def load_workspace(root: Path, lore: Path | None = None) -> WorkspaceView:
    """Load one checkout's authored world, with the lore join applied."""

    root_path = Path(root)
    try:
        world = load_authoring_world(discover_source_documents(root_path))
    except AuthoringError as error:
        raise WorkspaceError(str(error)) from error
    return WorkspaceView(
        root=root_path,
        world=world,
        roster=_roster(world, load_lore(lore)),
    )
