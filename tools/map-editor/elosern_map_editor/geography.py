"""Named geography commands: continent, locations, districts and footprints.

Every handler here is a :class:`~elosern_map_editor.commands.DocumentCommand`
that replaces exactly one existing world document:

``content/maps/continent.yaml``
    ``move_control_point`` / ``insert_control_point`` / ``remove_control_point``
    ``{feature, index[, point]}``: one vertex of the mainland boundary
    (``point`` is ``[east_km, north_km]``, kilometre geometry), the forest
    edge, a waterway route or a waterway's fords (``point`` is
    ``[cell_x, cell_y]``, one-kilometre wilderness cell indices). ``feature``
    is ``{"kind": "mainland"}``, ``{"kind": "forest_edge"}``,
    ``{"kind": "waterway_route", "waterway_id": ...}`` or
    ``{"kind": "waterway_ford", "waterway_id": ...}``.
    ``set_terrain_parameter`` ``{field, value}``: a ridge parameter
    (``ridge.<name>``, cell units), ``coastal_y_max`` (cell row) or
    ``border_river_key`` (an existing waterway).
    ``add_ridge_pass`` ``{y_min, y_max}``, ``set_ridge_pass``
    ``{index, y_min, y_max}``, ``remove_ridge_pass`` ``{index}`` (cell rows).
    ``add_waterway`` ``{waterway_id, route}``, ``remove_waterway``
    ``{waterway_id}`` (never the border river).
    ``set_region_field`` ``{region_id, field, value}``: region prose and
    classifier fields of one of the core's fixed regions.
    ``add_site`` ``{site_id, display_name, role, cell}``, ``set_site_field``
    ``{site_id, field, value}``, ``remove_site`` ``{site_id}``: reserved
    geographic (harbour) sites.

``content/maps/locations.yaml``
    ``create_location`` (a new stable ID; no local map is created),
    ``set_location_field`` ``{location_id, field, value}`` and
    ``delete_location`` ``{location_id}``. Creating a local map is a separate
    settlement command.

``content/maps/districts.yaml``
    ``create_district`` and ``set_district_field`` ``{district_id, field,
    value}``; ``membership`` sets ``kind`` and ``region_key`` together and
    ``landmark`` a stable qualified landmark reference.

``content/maps/settlements/<settlement_id>.yaml``
    ``set_footprint_cell`` ``{settlement_id, cell, filled}`` toggles one
    absolute wilderness cell of the settlement-owned footprint mask (growing
    the mask with ``.`` when the cell lies outside it). The saved value is the
    mask's offset from the settlement's location cell, so the absolute-cell
    contract never leaks an origin into the document. There is no editable
    binding: the world frame comes from the location cell and the unique
    ``anchor_room`` node. Interior positions are never assigned metres.

Arguments are type-checked here; field values are then validated by the core
schema and the complete world by the authoring gate. Established IDs are
never renamed and nothing cascades into another document. Derived output
(terrain preview, national borders, the partition) is never written: a
committed change only makes the partition artifact stale.
"""

from __future__ import annotations

import re
from typing import Any

from elosern_map_core.schema import IDENTIFIER_PATTERN

from .commands import CommandError, DocumentCommand, refused_value

CONTINENT = "content/maps/continent.yaml"
LOCATIONS = "content/maps/locations.yaml"
DISTRICTS = "content/maps/districts.yaml"

#: Argument sanity bound for any integer coordinate or parameter.
MAX_MAGNITUDE = 10_000_000
#: Largest footprint mask side the cell control grows to.
MAX_MASK_SIDE = 64

_IDENTIFIER = re.compile(IDENTIFIER_PATTERN)


def settlement_document(settlement_id: str) -> str:
    return f"content/maps/settlements/{settlement_id}.yaml"


# -- argument typing ---------------------------------------------------------
def _invalid(message: str) -> CommandError:
    return CommandError(400, "invalid_command", message)


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value) or len(value) > 128:
        raise _invalid(f"{label} is an authored identifier")
    return value


def _integer(value: Any, label: str, *, minimum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise _invalid(f"{label} is an integer")
    if abs(value) > MAX_MAGNITUDE:
        raise _invalid(f"{label} is outside ±{MAX_MAGNITUDE}")
    if minimum is not None and value < minimum:
        raise _invalid(f"{label} is at least {minimum}")
    return value


def _pair(value: Any, label: str, *, minimum: int | None = None) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise _invalid(f"{label} is a two-integer list")
    return _integer(value[0], f"{label}[0]", minimum=minimum), _integer(value[1], f"{label}[1]", minimum=minimum)


def _cell(value: Any, label: str) -> dict[str, int]:
    x, y = _pair(value, label, minimum=0)
    return {"cell_x": x, "cell_y": y}


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise _invalid(f"{label} is a string")
    return value


def _optional_text(value: Any, label: str) -> str | None:
    return None if value is None else _text(value, label)


def _texts(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _invalid(f"{label} is a list of strings")
    return list(value)


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise _invalid(f"{label} is a boolean")
    return value


def _index(value: Any, length: int, label: str, *, insert: bool = False) -> int:
    index = _integer(value, label, minimum=0)
    limit = length if insert else length - 1
    if index > limit:
        raise refused_value("index_out_of_range", f"{label} {index} is outside 0..{limit}", label)
    return index


def _unknown(kind: str, identity: str, field_path: str) -> CommandError:
    return refused_value(f"unknown_{kind}", f"there is no {kind} {identity!r}", field_path)


def _duplicate(identity: str, field_path: str) -> CommandError:
    return refused_value("duplicate_identifier", f"{identity!r} already exists", field_path)


# -- continent ---------------------------------------------------------------
_FEATURE_KINDS = ("mainland", "forest_edge", "waterway_route", "waterway_ford")


def _feature(arguments: dict[str, Any]) -> dict[str, str]:
    feature = arguments["feature"]
    if not isinstance(feature, dict) or feature.get("kind") not in _FEATURE_KINDS:
        raise _invalid(f"feature.kind is one of {', '.join(_FEATURE_KINDS)}")
    if feature["kind"].startswith("waterway"):
        if set(feature) != {"kind", "waterway_id"}:
            raise _invalid("a waterway feature carries exactly kind and waterway_id")
        _identifier(feature["waterway_id"], "feature.waterway_id")
    elif set(feature) != {"kind"}:
        raise _invalid("this feature carries exactly kind")
    return feature


def _point(feature: dict[str, str], value: Any) -> dict[str, int]:
    if feature["kind"] == "mainland":
        east, north = _pair(value, "point")
        return {"east_km": east, "north_km": north}
    return _cell(value, "point")


def _waterway(data: dict[str, Any], waterway_id: str) -> dict[str, Any]:
    waterway = data["terrain"]["waterways"].get(waterway_id)
    if waterway is None:
        raise _unknown("waterway", waterway_id, "arguments.feature.waterway_id")
    return waterway


def _points(data: dict[str, Any], feature: dict[str, str]) -> list[dict[str, int]]:
    kind = feature["kind"]
    if kind == "mainland":
        return data["mainland_boundary_km"]
    if kind == "forest_edge":
        return data["terrain"]["forest_edge"]
    waterway = _waterway(data, feature["waterway_id"])
    if kind == "waterway_route":
        return waterway["route"]
    return waterway.setdefault("fords", [])


class _Continent(DocumentCommand):
    def owner(self, arguments: dict[str, Any]) -> str:
        return CONTINENT


class MoveControlPoint(_Continent):
    name = "move_control_point"
    keys = frozenset({"feature", "index", "point"})

    def check(self, world, arguments):
        _point(_feature(arguments), arguments["point"])
        _integer(arguments["index"], "index", minimum=0)

    def mutate(self, data, arguments):
        feature = _feature(arguments)
        points = _points(data, feature)
        points[_index(arguments["index"], len(points), "index")] = _point(feature, arguments["point"])


class InsertControlPoint(_Continent):
    name = "insert_control_point"
    keys = frozenset({"feature", "index", "point"})

    def check(self, world, arguments):
        _point(_feature(arguments), arguments["point"])
        _integer(arguments["index"], "index", minimum=0)

    def mutate(self, data, arguments):
        feature = _feature(arguments)
        points = _points(data, feature)
        points.insert(_index(arguments["index"], len(points), "index", insert=True), _point(feature, arguments["point"]))


class RemoveControlPoint(_Continent):
    name = "remove_control_point"
    keys = frozenset({"feature", "index"})

    def check(self, world, arguments):
        _feature(arguments)
        _integer(arguments["index"], "index", minimum=0)

    def mutate(self, data, arguments):
        feature = _feature(arguments)
        points = _points(data, feature)
        del points[_index(arguments["index"], len(points), "index")]


_RIDGE_FIELDS = ("base_x", "period", "step", "min_x", "max_x", "north_limit_y", "mountain_corridor_half_width")
_TERRAIN_FIELDS = (*(f"ridge.{name}" for name in _RIDGE_FIELDS), "coastal_y_max", "border_river_key")


class SetTerrainParameter(_Continent):
    name = "set_terrain_parameter"
    keys = frozenset({"field", "value"})

    def check(self, world, arguments):
        field = arguments["field"]
        if field not in _TERRAIN_FIELDS:
            raise _invalid(f"field is one of {', '.join(_TERRAIN_FIELDS)}")
        if field == "border_river_key":
            _identifier(arguments["value"], "value")
        else:
            _integer(arguments["value"], "value")

    def mutate(self, data, arguments):
        field, value = arguments["field"], arguments["value"]
        terrain = data["terrain"]
        if field == "border_river_key":
            if value not in terrain["waterways"]:
                raise _unknown("waterway", value, "arguments.value")
            terrain["border_river_key"] = value
        elif field == "coastal_y_max":
            terrain["coastal_y_max"] = value
        else:
            terrain["ridge"][field.removeprefix("ridge.")] = value


def _window(arguments: dict[str, Any]) -> dict[str, int]:
    return {"y_min": _integer(arguments["y_min"], "y_min"), "y_max": _integer(arguments["y_max"], "y_max")}


class AddRidgePass(_Continent):
    name = "add_ridge_pass"
    keys = frozenset({"y_min", "y_max"})

    def check(self, world, arguments):
        _window(arguments)

    def mutate(self, data, arguments):
        data["terrain"]["ridge"]["passes"].append(_window(arguments))


class SetRidgePass(_Continent):
    name = "set_ridge_pass"
    keys = frozenset({"index", "y_min", "y_max"})

    def check(self, world, arguments):
        _window(arguments)
        _integer(arguments["index"], "index", minimum=0)

    def mutate(self, data, arguments):
        passes = data["terrain"]["ridge"]["passes"]
        passes[_index(arguments["index"], len(passes), "index")] = _window(arguments)


class RemoveRidgePass(_Continent):
    name = "remove_ridge_pass"
    keys = frozenset({"index"})

    def check(self, world, arguments):
        _integer(arguments["index"], "index", minimum=0)

    def mutate(self, data, arguments):
        passes = data["terrain"]["ridge"]["passes"]
        del passes[_index(arguments["index"], len(passes), "index")]


class AddWaterway(_Continent):
    name = "add_waterway"
    keys = frozenset({"waterway_id", "route"})

    def check(self, world, arguments):
        _identifier(arguments["waterway_id"], "waterway_id")
        route = arguments["route"]
        if not isinstance(route, list):
            raise _invalid("route is a list of cells")
        for index, cell in enumerate(route):
            _cell(cell, f"route[{index}]")

    def mutate(self, data, arguments):
        waterways = data["terrain"]["waterways"]
        waterway_id = arguments["waterway_id"]
        if waterway_id in waterways:
            raise _duplicate(waterway_id, "arguments.waterway_id")
        waterways[waterway_id] = {
            "route": [_cell(cell, "route") for cell in arguments["route"]],
            "fords": [],
        }


class RemoveWaterway(_Continent):
    name = "remove_waterway"
    keys = frozenset({"waterway_id"})

    def check(self, world, arguments):
        _identifier(arguments["waterway_id"], "waterway_id")

    def mutate(self, data, arguments):
        waterway_id = arguments["waterway_id"]
        _waterway(data, waterway_id)
        if data["terrain"]["border_river_key"] == waterway_id:
            raise CommandError(
                409,
                "deletion_refused",
                "the border river is named by terrain.border_river_key; choose another border river first",
                guard="internal",
                internal_references=[
                    {"target": waterway_id, "kind": "border_river_key", "source": CONTINENT,
                     "object_id": waterway_id, "field_path": "terrain.border_river_key"}
                ],
                removed=[waterway_id],
            )
        del data["terrain"]["waterways"][waterway_id]


_REGION_FIELDS = {
    "display_name_zh": _text,
    "nation_key": _optional_text,
    "terrain_flavor_zh": _texts,
    "nominal_nation_keys": _texts,
    "scene_archetype": _optional_text,
}


def _field_value(fields: dict[str, Any], arguments: dict[str, Any]) -> Any:
    field = arguments["field"]
    if field not in fields:
        raise _invalid(f"field is one of {', '.join(fields)}")
    return fields[field](arguments["value"], "value")


class SetRegionField(_Continent):
    name = "set_region_field"
    keys = frozenset({"region_id", "field", "value"})

    def check(self, world, arguments):
        _identifier(arguments["region_id"], "region_id")
        _field_value(_REGION_FIELDS, arguments)

    def mutate(self, data, arguments):
        region = data["regions"].get(arguments["region_id"])
        if region is None:
            raise _unknown("region", arguments["region_id"], "arguments.region_id")
        region[arguments["field"]] = _field_value(_REGION_FIELDS, arguments)


_SITE_FIELDS = {"display_name": _text, "role": _text, "cell": _cell}


class AddSite(_Continent):
    name = "add_site"
    keys = frozenset({"site_id", "display_name", "role", "cell"})

    def check(self, world, arguments):
        _identifier(arguments["site_id"], "site_id")
        for field, typed in _SITE_FIELDS.items():
            typed(arguments[field], field)

    def mutate(self, data, arguments):
        sites = data["harbor_sites"]
        if arguments["site_id"] in sites:
            raise _duplicate(arguments["site_id"], "arguments.site_id")
        sites[arguments["site_id"]] = {
            "display_name": arguments["display_name"],
            "cell": _cell(arguments["cell"], "cell"),
            "role": arguments["role"],
        }


class SetSiteField(_Continent):
    name = "set_site_field"
    keys = frozenset({"site_id", "field", "value"})

    def check(self, world, arguments):
        _identifier(arguments["site_id"], "site_id")
        _field_value(_SITE_FIELDS, arguments)

    def mutate(self, data, arguments):
        site = data["harbor_sites"].get(arguments["site_id"])
        if site is None:
            raise _unknown("site", arguments["site_id"], "arguments.site_id")
        site[arguments["field"]] = _field_value(_SITE_FIELDS, arguments)


class RemoveSite(_Continent):
    name = "remove_site"
    keys = frozenset({"site_id"})

    def check(self, world, arguments):
        _identifier(arguments["site_id"], "site_id")

    def mutate(self, data, arguments):
        if data["harbor_sites"].pop(arguments["site_id"], None) is None:
            raise _unknown("site", arguments["site_id"], "arguments.site_id")


# -- locations ---------------------------------------------------------------
_LOCATION_FIELDS = {
    "kind": _text,
    "display_name_zh": _text,
    "description": _text,
    "geographic_constraint": _text,
    "scene_archetype": _optional_text,
    "cell": _cell,
}


class _Locations(DocumentCommand):
    def owner(self, arguments: dict[str, Any]) -> str:
        return LOCATIONS


class CreateLocation(_Locations):
    name = "create_location"
    keys = frozenset({"location_id", *_LOCATION_FIELDS})

    def check(self, world, arguments):
        _identifier(arguments["location_id"], "location_id")
        for field, typed in _LOCATION_FIELDS.items():
            typed(arguments[field], field)

    def mutate(self, data, arguments):
        locations = data["locations"]
        location_id = arguments["location_id"]
        if location_id in locations:
            raise _duplicate(location_id, "arguments.location_id")
        locations[location_id] = {
            field: typed(arguments[field], field) for field, typed in _LOCATION_FIELDS.items()
        }


class SetLocationField(_Locations):
    name = "set_location_field"
    keys = frozenset({"location_id", "field", "value"})

    def check(self, world, arguments):
        _identifier(arguments["location_id"], "location_id")
        _field_value(_LOCATION_FIELDS, arguments)

    def mutate(self, data, arguments):
        location = data["locations"].get(arguments["location_id"])
        if location is None:
            raise _unknown("location", arguments["location_id"], "arguments.location_id")
        location[arguments["field"]] = _field_value(_LOCATION_FIELDS, arguments)


class DeleteLocation(_Locations):
    """Remove one location; never cascades.

    The published projection gives an early, explained refusal; the
    authority is the execution-time guard on the fresh disk baseline
    (map-internal references) plus the external reference context.
    """

    name = "delete_location"
    keys = frozenset({"location_id"})

    def check(self, world, arguments):
        location_id = _identifier(arguments["location_id"], "location_id")
        rows = []
        for settlement in world.get("settlements", []):
            if settlement["location_ref"] == location_id:
                rows.append({"kind": "location_ref", "source": settlement["relative_path"], "object_id": settlement["id"]})
            for node in settlement["nodes"]:
                if node.get("anchor_key") == location_id:
                    rows.append({"kind": "anchor_key", "source": settlement["relative_path"], "object_id": node["id"]})
        for district in world.get("districts", []):
            landmark = district.get("landmark") or {}
            if landmark.get("domain") == "location" and landmark.get("object_id") == location_id:
                rows.append({"kind": "landmark", "source": district["relative_path"], "object_id": district["id"]})
        if rows:
            raise CommandError(
                409,
                "deletion_refused",
                "other map documents still refer to this location",
                guard="internal",
                internal_references=[{"target": f"location:{location_id}", **row} for row in rows],
                removed=[f"location:{location_id}"],
            )

    def mutate(self, data, arguments):
        if data["locations"].pop(arguments["location_id"], None) is None:
            raise _unknown("location", arguments["location_id"], "arguments.location_id")


# -- districts ---------------------------------------------------------------
def _membership(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"kind", "region_key"}:
        raise _invalid(f"{label} carries exactly kind and region_key")
    return {"kind": _text(value["kind"], f"{label}.kind"), "region_key": _optional_text(value["region_key"], f"{label}.region_key")}


def _landmark(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"domain", "map_id", "object_id", "cell"}:
        raise _invalid(f"{label} carries exactly domain, map_id, object_id and cell")
    return {
        "domain": _text(value["domain"], f"{label}.domain"),
        "map_id": None if value["map_id"] is None else _identifier(value["map_id"], f"{label}.map_id"),
        "object_id": None if value["object_id"] is None else _identifier(value["object_id"], f"{label}.object_id"),
        "cell": None if value["cell"] is None else _cell(value["cell"], f"{label}.cell"),
    }


_DISTRICT_FIELDS = {
    "district_name_zh": _text,
    "landmark_name_zh": _text,
    "membership": _membership,
    "landmark": _landmark,
}


class _Districts(DocumentCommand):
    def owner(self, arguments: dict[str, Any]) -> str:
        return DISTRICTS


def _apply_district(district: dict[str, Any], field: str, value: Any) -> None:
    if field == "membership":
        district["kind"] = value["kind"]
        district["region_key"] = value["region_key"]
    else:
        district[field] = value


class CreateDistrict(_Districts):
    name = "create_district"
    keys = frozenset({"district_id", *_DISTRICT_FIELDS})

    def check(self, world, arguments):
        _identifier(arguments["district_id"], "district_id")
        for field, typed in _DISTRICT_FIELDS.items():
            typed(arguments[field], field)

    def mutate(self, data, arguments):
        districts = data["districts"]
        district_id = arguments["district_id"]
        if district_id in districts:
            raise _duplicate(district_id, "arguments.district_id")
        district: dict[str, Any] = {}
        for field in ("district_name_zh", "landmark_name_zh", "landmark", "membership"):
            _apply_district(district, field, _DISTRICT_FIELDS[field](arguments[field], field))
        districts[district_id] = district


class SetDistrictField(_Districts):
    name = "set_district_field"
    keys = frozenset({"district_id", "field", "value"})

    def check(self, world, arguments):
        _identifier(arguments["district_id"], "district_id")
        _field_value(_DISTRICT_FIELDS, arguments)

    def mutate(self, data, arguments):
        district = data["districts"].get(arguments["district_id"])
        if district is None:
            raise _unknown("district", arguments["district_id"], "arguments.district_id")
        _apply_district(district, arguments["field"], _field_value(_DISTRICT_FIELDS, arguments))


# -- settlement-owned footprint ----------------------------------------------
class _Settlement(DocumentCommand):
    def owner(self, arguments: dict[str, Any]) -> str:
        return settlement_document(arguments["settlement_id"])


def _location_cell(world: dict[str, Any] | None, location_ref: str) -> tuple[int, int] | None:
    """The authored cell of ``location_ref`` in the published projection."""

    for row in (world or {}).get("locations", []):
        if row.get("id") == location_ref:
            return (int(row["cell"][0]), int(row["cell"][1]))
    return None


def toggled_mask(
    entry: dict[str, Any],
    cell: tuple[int, int],
    filled: bool,
    *,
    location_cell: tuple[int, int],
) -> tuple[list[str], dict[str, int]]:
    """The mask and location-relative offset with one absolute cell set or cleared.

    Mask row ``r`` / column ``c`` is the absolute cell ``location_cell +
    entry offset + (c, r)``. A filled cell outside the mask grows it with ``.``
    (moving the offset west/south as needed); clearing a cell outside it
    changes nothing. The saved offset is always relative to ``location_cell``,
    so existing ``#`` cells keep their absolute positions and a later location
    move translates the whole mask. Gates are directions and nodes, not cells,
    so growth never moves them.
    """

    shape = [str(row) for row in entry["shape"]]
    origin_x = location_cell[0] + int(entry["offset"]["dx"])
    origin_y = location_cell[1] + int(entry["offset"]["dy"])
    width, height = len(shape[0]), len(shape)
    x, y = cell
    inside = origin_x <= x < origin_x + width and origin_y <= y < origin_y + height
    if not inside:
        if not filled:
            return shape, dict(entry["offset"])
        west, south = min(origin_x, x), min(origin_y, y)
        east, north = max(origin_x + width - 1, x), max(origin_y + height - 1, y)
        new_width, new_height = east - west + 1, north - south + 1
        if new_width > MAX_MASK_SIDE or new_height > MAX_MASK_SIDE:
            raise refused_value(
                "footprint_too_large",
                f"the footprint mask would grow beyond {MAX_MASK_SIDE}x{MAX_MASK_SIDE} cells",
                "wilderness_entry.shape",
            )
        grown = [["."] * new_width for _ in range(new_height)]
        for row, line in enumerate(shape):
            for column, character in enumerate(line):
                grown[origin_y - south + row][origin_x - west + column] = character
        shape = ["".join(line) for line in grown]
        origin_x, origin_y = west, south
    row, column = y - origin_y, x - origin_x
    line = list(shape[row])
    line[column] = "#" if filled else "."
    shape[row] = "".join(line)
    return shape, {
        "dx": origin_x - location_cell[0],
        "dy": origin_y - location_cell[1],
    }


class SetFootprintCell(_Settlement):
    name = "set_footprint_cell"
    keys = frozenset({"settlement_id", "cell", "filled"})

    def dependencies(self, world, arguments):
        # The absolute-cell contract converts through the published location
        # cell, so a location document that changed after the snapshot must be
        # reread before this command can be admitted.
        locations = (world or {}).get("locations") or ()
        return tuple({row["relative_path"] for row in locations})

    def check(self, world, arguments):
        _identifier(arguments["settlement_id"], "settlement_id")
        _pair(arguments["cell"], "cell", minimum=0)
        _bool(arguments["filled"], "filled")

    def mutate_with_world(self, data, arguments, world):
        entry = data.get("wilderness_entry")
        if entry is None:
            raise refused_value(
                "no_footprint",
                "this settlement declares no wilderness entry footprint",
                "wilderness_entry",
            )
        location_cell = _location_cell(world, data["location_ref"])
        if location_cell is None:
            raise refused_value(
                "unknown_location",
                f"the location {data['location_ref']!r} of this settlement is not in the published world",
                "location_ref",
            )
        shape, offset = toggled_mask(
            entry,
            _pair(arguments["cell"], "cell", minimum=0),
            arguments["filled"],
            location_cell=location_cell,
        )
        entry["shape"] = shape
        entry["offset"] = offset


GEOGRAPHY_HANDLERS = (
    MoveControlPoint(),
    InsertControlPoint(),
    RemoveControlPoint(),
    SetTerrainParameter(),
    AddRidgePass(),
    SetRidgePass(),
    RemoveRidgePass(),
    AddWaterway(),
    RemoveWaterway(),
    SetRegionField(),
    AddSite(),
    SetSiteField(),
    RemoveSite(),
    CreateLocation(),
    SetLocationField(),
    DeleteLocation(),
    CreateDistrict(),
    SetDistrictField(),
    SetFootprintCell(),
)

__all__ = ["GEOGRAPHY_HANDLERS", "MAX_MASK_SIDE", "settlement_document", "toggled_mask"]
