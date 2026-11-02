"""The repository adapter: authored sources in, explicit views out.

Everything above this module is a pure function of explicit inputs. This module
is where a checkout becomes those inputs: it loads the authored map sources
through the map core, joins the lore row for each location, and builds one
windowed terrain view per check. It reads only; nothing here writes a file.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from elosern_map_core import (
    AuthoringError,
    discover_source_documents,
    load_authoring_world,
)
from elosern_map_core.authoring import terrain_definition
from elosern_map_core.elevation_codec import decode_tile
from elosern_map_core.terrain import (
    is_inland_water_cell,
    is_land_cell,
    is_walkable_cell,
    rasterize_routes,
)

from tools.settlement_synthesis.geometry import Cell
from tools.settlement_synthesis.site import SettlementRef
from tools.settlement_synthesis.terrain_view import GridTerrain

#: The committed elevation tile bundle, relative to the workspace root.
ELEVATION_PATH = Path("content") / "maps" / "wilderness_elevation.json"

#: One 64x64 elevation tile edge, matching the map core's tile format.
TILE_CELLS = 64


class WorkspaceError(Exception):
    """The workspace or one requested identity cannot be read."""


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
