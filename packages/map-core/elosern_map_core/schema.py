"""The machine-readable version-1 schema of the authored map documents.

The schema is the single description of every supported document kind, every
nested field (including room prototype fields), the typed value each field
accepts, and the cross-field rules the loader enforces. Consumers -- the game
adapter, the editor service and its frontend -- read :func:`schema` instead of
maintaining a second domain description.

The format is a custom JSON-compatible domain schema, not JSON Schema:

* ``document_kinds`` maps a kind to its source location, identity rule,
  ``fields`` tree and ``rules`` list.
* A field spec has ``type`` (``str``, ``int``, ``bool``, ``enum``, ``mapping``,
  ``list``), ``required`` (default true), ``nullable``, and type-specific keys
  (``values``, ``min``, ``max``, ``pattern``, ``fields``, ``items``,
  ``key_pattern``, ``min_items``, ``max_items``, ``constant``, ``reference``).
* A list spec may carry ``identity``: the field names that identify one object
  of the list across edits (used by the round-trip serializer to retain that
  object's comments).
* A mapping spec may carry ``unique_values``: sibling field names whose value
  tuple must be unique across the mapping's object values.
* ``rules`` entries are: ``required_when_equals``, ``forbidden_when_equals``,
  ``required_when_in``, ``forbidden_when_in``, ``unique_sequence``,
  ``unique_outgoing`` and ``mask``.

``schema()`` returns a deep copy, so a consumer can never mutate the core's
description.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .diagnostics import (
    STRUCTURE,
    Diagnostic,
    SourceLocation,
    sorted_diagnostics,
)
from .terrain import REGION_KEYS

SCHEMA_VERSION = 1
IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_]*$"
COMPASS_DIRECTIONS = ("n", "ne", "e", "se", "s", "sw", "w", "nw")
LOCATION_KINDS = ("capital", "elven_village", "dungeon")
DISTRICT_KINDS = ("voronoi", "region")
QUALIFIED_REF_DOMAINS = (
    "settlement_node",
    "interior_room",
    "location",
    "wilderness_cell",
)

MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_DOCUMENT_DEPTH = 32
MAX_COLLECTION_ITEMS = 100_000


def _int(*, required: bool = True, min_value: int | None = None, **extra: Any) -> dict:
    spec: dict[str, Any] = {"type": "int", "required": required}
    if min_value is not None:
        spec["min"] = min_value
    spec.update(extra)
    return spec


def _str(*, required: bool = True, **extra: Any) -> dict:
    return {"type": "str", "required": required, **extra}


def _bool(*, required: bool = True) -> dict:
    return {"type": "bool", "required": required}


def _enum(values, *, required: bool = True) -> dict:
    return {"type": "enum", "required": required, "values": list(values)}


def _nullable(spec: dict) -> dict:
    spec = dict(spec)
    spec["nullable"] = True
    return spec


def _mapping(fields: Mapping[str, dict], *, required: bool = True, **extra: Any) -> dict:
    return {
        "type": "mapping",
        "required": required,
        "fields": {name: dict(spec) for name, spec in fields.items()},
        **extra,
    }


def _list(items: dict, *, required: bool = True, **extra: Any) -> dict:
    return {"type": "list", "required": required, "items": dict(items), **extra}


def _cell(*, required: bool = True) -> dict:
    """One wilderness cell index: explicit ``cell_x``/``cell_y`` names."""

    return _mapping(
        {
            "cell_x": _int(min_value=0),
            "cell_y": _int(min_value=0),
        },
        required=required,
    )


def _point_m(*, required: bool = True) -> dict:
    """One settlement-local metre point: explicit ``east_m``/``north_m``."""

    return _mapping(
        {
            "east_m": _int(),
            "north_m": _int(),
        },
        required=required,
    )


def _bend() -> dict:
    return _mapping({"x_m": _int(), "y_m": _int()})


_QUALIFIED_REF = _mapping(
    {
        "domain": _enum(QUALIFIED_REF_DOMAINS),
        "map_id": _nullable(_str()),
        "object_id": _nullable(_str()),
        "cell": _nullable(_cell()),
    },
    rules=[
        {
            "rule": "required_when_in",
            "field": "map_id",
            "other": "domain",
            "values": ["settlement_node", "interior_room"],
        },
        {
            "rule": "forbidden_when_in",
            "field": "map_id",
            "other": "domain",
            "values": ["location", "wilderness_cell"],
        },
        {
            "rule": "required_when_in",
            "field": "object_id",
            "other": "domain",
            "values": ["settlement_node", "interior_room", "location"],
        },
        {
            "rule": "forbidden_when_in",
            "field": "object_id",
            "other": "domain",
            "values": ["wilderness_cell"],
        },
        {
            "rule": "required_when_in",
            "field": "cell",
            "other": "domain",
            "values": ["wilderness_cell"],
        },
        {
            "rule": "forbidden_when_in",
            "field": "cell",
            "other": "domain",
            "values": [
                "settlement_node",
                "interior_room",
                "location",
            ],
        },
    ],
)

_NODE = _mapping(
    {
        "x_m": _int(),
        "y_m": _int(),
        "prototype_parent": _enum(("grid_room", "anchor_room")),
        "key": _str(min_length=1),
        "desc": _str(),
        "anchor_key": _nullable(_str()),
        "typeclass": _nullable(_str()),
        "scene_archetype": _nullable(_str()),
    },
    rules=[
        {
            "rule": "required_when_equals",
            "field": "anchor_key",
            "other": "prototype_parent",
            "value": "anchor_room",
        },
        {
            "rule": "forbidden_when_equals",
            "field": "anchor_key",
            "other": "prototype_parent",
            "value": "grid_room",
        },
    ],
)

_ROAD = _mapping(
    {
        "source": _str(pattern=IDENTIFIER_PATTERN, reference="settlement_nodes"),
        "destination": _str(pattern=IDENTIFIER_PATTERN, reference="settlement_nodes"),
        "direction": _enum(COMPASS_DIRECTIONS),
        "bends": _list(_bend(), required=False, max_items=MAX_COLLECTION_ITEMS),
    },
)

_GATE = _mapping(
    {
        "return_direction": _enum(COMPASS_DIRECTIONS),
        "destination_node": _str(
            pattern=IDENTIFIER_PATTERN,
            reference="settlement_nodes",
        ),
    },
)

_WILDERNESS_ENTRY = _mapping(
    {
        "shape": _list(_str(min_length=1), mask=True, min_items=1),
        "origin": _cell(),
        "gates": _list(_GATE, min_items=1),
    },
)

_REGION = _mapping(
    {
        "display_name_zh": _str(min_length=1),
        "nation_key": _nullable(_str()),
        "terrain_flavor_zh": _list(_str(), min_items=1),
        "nominal_nation_keys": _list(_str(), required=False),
        "scene_archetype": _nullable(_str()),
    },
)

_HARBOR_SITE = _mapping(
    {
        "display_name": _str(min_length=1),
        "cell": _cell(),
        "role": _str(),
    },
)

_RIDGE = _mapping(
    {
        "base_x": _int(),
        "period": _int(min_value=1),
        "step": _int(min_value=1),
        "min_x": _int(),
        "max_x": _int(),
        "north_limit_y": _int(),
        "mountain_corridor_half_width": _int(min_value=0),
        "passes": _list(
            _mapping({"y_min": _int(), "y_max": _int()}),
            min_items=1,
        ),
    },
)

_WATERWAY = _mapping(
    {
        "route": _list(_cell(), min_items=2),
        "fords": _list(_cell(), required=False),
    },
)

_TERRAIN = _mapping(
    {
        "forest_edge": _list(_cell(), min_items=2),
        "ridge": _RIDGE,
        "coastal_y_max": _int(),
        "waterways": _mapping(
            {}, key_pattern=IDENTIFIER_PATTERN, items=_WATERWAY
        ),
        "border_river_key": _str(pattern=IDENTIFIER_PATTERN),
    },
)

_LOCATION = _mapping(
    {
        "kind": _enum(LOCATION_KINDS),
        "display_name_zh": _str(min_length=1),
        "description": _str(),
        "cell": _cell(),
        "geographic_constraint": _str(),
        "scene_archetype": _nullable(_str()),
    },
)

_DISTRICT = _mapping(
    {
        "district_name_zh": _str(min_length=1),
        "landmark_name_zh": _str(min_length=1),
        "landmark": deepcopy(_QUALIFIED_REF),
        "kind": _enum(DISTRICT_KINDS),
        "region_key": _nullable(_str(reference="continent_regions")),
    },
    rules=[
        {
            "rule": "required_when_equals",
            "field": "region_key",
            "other": "kind",
            "value": "region",
        },
        {
            "rule": "forbidden_when_equals",
            "field": "region_key",
            "other": "kind",
            "value": "voronoi",
        },
    ],
)

_INTERIOR_ROOM = _mapping(
    {
        "name_zh": _str(min_length=1),
        "desc_zh": _str(),
        "scene_archetype": _nullable(_str()),
    },
)

_CONNECTION = _mapping(
    {
        "source": _str(pattern=IDENTIFIER_PATTERN, reference="interior_rooms"),
        "destination": _str(pattern=IDENTIFIER_PATTERN, reference="interior_rooms"),
        "label": _str(min_length=1),
    },
)

_INTERIOR_LINK = _mapping(
    {
        "source_room": _str(pattern=IDENTIFIER_PATTERN, reference="interior_rooms"),
        "target_interior": _str(pattern=IDENTIFIER_PATTERN, reference="interiors"),
        "target_room": _str(pattern=IDENTIFIER_PATTERN, reference="interior_rooms"),
        "label": _str(min_length=1),
        "return_label": _nullable(_str(min_length=1)),
    },
)

_EXTERIOR = _mapping(
    {
        "settlement": _str(pattern=IDENTIFIER_PATTERN, reference="settlements"),
        "node": _str(pattern=IDENTIFIER_PATTERN, reference="settlement_nodes_of"),
        "room": _str(pattern=IDENTIFIER_PATTERN, reference="interior_rooms"),
        "doorway_key": _str(min_length=1),
        "doorway_aliases": _list(_str(), required=False),
    },
)

_DOCUMENT_KINDS: dict[str, dict[str, Any]] = {
    "continent": {
        "description": "Continental frame, terrain inputs, regions and sites.",
        "source": "content/maps/continent.yaml",
        "identity": "fixed",
        "fixed_id": "continent",
        "fields": {
            "version": _int(constant=SCHEMA_VERSION),
            "kind": _enum(("continent",)),
            "id": _str(pattern=IDENTIFIER_PATTERN, constant="continent"),
            "frame_cells": _int(min_value=1),
            "cell_size_km": _int(min_value=1),
            "mainland_boundary_km": _list(
                _mapping({"east_km": _int(), "north_km": _int()}),
                min_items=3,
            ),
            "regions": _mapping(
                {}, key_pattern=IDENTIFIER_PATTERN, items=_REGION
            ),
            "harbor_sites": _mapping(
                {}, key_pattern=IDENTIFIER_PATTERN, items=_HARBOR_SITE
            ),
            "terrain": _TERRAIN,
        },
        "rules": [],
        "document_rules": [
            {
                "rule": "required_keys",
                "field": "regions",
                "values": sorted(REGION_KEYS),
            }
        ],
    },
    "locations": {
        "description": "Static geographic locations and their map-facing data.",
        "source": "content/maps/locations.yaml",
        "identity": "fixed",
        "fixed_id": "locations",
        "fields": {
            "version": _int(constant=SCHEMA_VERSION),
            "kind": _enum(("locations",)),
            "id": _str(pattern=IDENTIFIER_PATTERN, constant="locations"),
            "locations": _mapping(
                {}, key_pattern=IDENTIFIER_PATTERN, items=_LOCATION
            ),
        },
        "rules": [],
    },
    "districts": {
        "description": "Map districts and their stable discovery landmarks.",
        "source": "content/maps/districts.yaml",
        "identity": "fixed",
        "fixed_id": "districts",
        "fields": {
            "version": _int(constant=SCHEMA_VERSION),
            "kind": _enum(("districts",)),
            "id": _str(pattern=IDENTIFIER_PATTERN, constant="districts"),
            "districts": _mapping(
                {}, key_pattern=IDENTIFIER_PATTERN, items=_DISTRICT
            ),
        },
        "rules": [],
    },
    "settlement": {
        "description": "One settlement local map: binding, nodes, roads and entrances.",
        "source": "content/maps/settlements/<id>.yaml",
        "identity": "file_stem",
        "fields": {
            "version": _int(constant=SCHEMA_VERSION),
            "kind": _enum(("settlement",)),
            "id": _str(pattern=IDENTIFIER_PATTERN),
            "location_ref": _str(
                pattern=IDENTIFIER_PATTERN,
                reference="locations",
            ),
            "binding": _mapping(
                {
                    "anchor_cell": _cell(),
                    "local_anchor_m": _point_m(),
                }
            ),
            "options": _mapping(
                {
                    "map_visual_range": _int(min_value=1),
                    "map_mode": _str(min_length=1),
                },
                required=False,
            ),
            "exit_prototype": _mapping(
                {
                    "prototype_parent": _enum(("xyz_exit",)),
                    "typeclass": _nullable(_str()),
                },
                required=False,
            ),
            "nodes": _mapping(
                {},
                key_pattern=IDENTIFIER_PATTERN,
                unique_values=["x_m", "y_m"],
                items=_NODE,
            ),
            "roads": _list(
                _ROAD,
                identity=["source", "destination"],
                rules=[
                    {"rule": "unique_sequence", "fields": ["source", "destination"]},
                    {"rule": "unique_outgoing", "field": "source", "other": "direction"},
                ],
            ),
            "wilderness_entry": _nullable(_WILDERNESS_ENTRY),
            "city_gate": _nullable(
                _mapping(
                    {
                        "node": _str(
                            pattern=IDENTIFIER_PATTERN,
                            reference="settlement_nodes",
                        ),
                        "exit_key": _str(min_length=1),
                        "exit_aliases": _list(_str(), required=False),
                    }
                )
            ),
        },
        "rules": [],
        "document_rules": [
            {"rule": "reference", "field": "location_ref", "target": "locations"},
        ],
    },
    "interior": {
        "description": "One permanent coordinate-free interior room graph.",
        "source": "content/maps/interiors/<id>.yaml",
        "identity": "file_stem",
        "fields": {
            "version": _int(constant=SCHEMA_VERSION),
            "kind": _enum(("interior",)),
            "id": _str(pattern=IDENTIFIER_PATTERN),
            "rooms": _mapping(
                {}, key_pattern=IDENTIFIER_PATTERN, items=_INTERIOR_ROOM
            ),
            "connections": _list(
                _CONNECTION,
                identity=["source", "destination", "label"],
                rules=[
                    {
                        "rule": "unique_sequence",
                        "fields": ["source", "destination", "label"],
                    }
                ],
            ),
            "interior_links": _list(
                _INTERIOR_LINK,
                required=False,
                identity=["source_room", "target_interior", "target_room", "label"],
            ),
            "exterior": _nullable(_EXTERIOR),
        },
        "rules": [],
        "document_rules": [],
    },
    "layout": {
        "description": "Editor-only room layout positions; never world geometry.",
        "source": "content/map-editor-layouts/<id>.yaml",
        "identity": "file_stem",
        "fields": {
            "version": _int(constant=SCHEMA_VERSION),
            "kind": _enum(("layout",)),
            "id": _str(pattern=IDENTIFIER_PATTERN),
            "positions": _mapping(
                {},
                key_pattern=IDENTIFIER_PATTERN,
                items=_mapping({"x": _int(), "y": _int()}),
            ),
        },
        "rules": [],
        "document_rules": [],
    },
}

_SCHEMA: dict[str, Any] = {
    "version": SCHEMA_VERSION,
    "identifier_pattern": IDENTIFIER_PATTERN,
    "document_kinds": _DOCUMENT_KINDS,
    "qualified_ref": deepcopy(_QUALIFIED_REF),
    "yaml_policy": {
        "version": [1, 2],
        "max_document_bytes": MAX_DOCUMENT_BYTES,
        "max_document_depth": MAX_DOCUMENT_DEPTH,
        "max_collection_items": MAX_COLLECTION_ITEMS,
        "rejected": [
            "duplicate_keys",
            "custom_tags",
            "anchors",
            "aliases",
            "merge_keys",
            "timestamps",
            "non_finite_numbers",
            "non_decimal_integers",
            "unsupported_scalars",
            "multiple_documents",
        ],
    },
    "gates": {
        "structure": "load and write are blocked",
        "semantic": "saveable unfinished map work; runtime adoption blocked",
        "external": "authoritative game-side external result unusable",
        "freshness": "required generated artifact does not describe this world",
    },
}

DOCUMENT_KINDS = tuple(_DOCUMENT_KINDS)
SOURCE_FILES = {
    meta["source"]: kind
    for kind, meta in _DOCUMENT_KINDS.items()
    if meta["identity"] == "fixed"
}


def schema() -> dict[str, Any]:
    """Return a deep copy of the complete machine-readable domain schema."""

    return deepcopy(_SCHEMA)


def document_meta(kind: str) -> Mapping[str, Any] | None:
    return _DOCUMENT_KINDS.get(kind)


def _join(path: str, name: str) -> str:
    return f"{path}.{name}" if path else name


def _provenance_location(
    provenance: Mapping[str, SourceLocation] | None,
    path: str,
) -> SourceLocation | None:
    if provenance is None:
        return None
    return provenance.get(path)


def _problem(
    diagnostics: list[Diagnostic],
    code: str,
    message: str,
    *,
    relative_path: str | None,
    field_path: str,
    provenance: Mapping[str, SourceLocation] | None,
    object_id: str | None = None,
) -> None:
    location = _provenance_location(provenance, field_path)
    diagnostics.append(
        Diagnostic(
            code=code,
            category=STRUCTURE,
            message=message,
            relative_path=relative_path,
            field_path=field_path,
            line=location.line if location else None,
            column=location.column if location else None,
            object_id=object_id,
        )
    )


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _hashable_identity(values) -> tuple | None:
    """The identity tuple, or ``None`` when a value cannot key a uniqueness check.

    Malformed values already produce their own type diagnostics; a uniqueness
    check must never raise on them.
    """

    identity = tuple(values)
    try:
        hash(identity)
    except TypeError:
        return None
    return identity


def _value_type_name(value: Any) -> str:
    return type(value).__name__


def _check_scalar(
    spec: Mapping[str, Any],
    value: Any,
    path: str,
    diagnostics: list[Diagnostic],
    *,
    relative_path: str | None,
    provenance: Mapping[str, SourceLocation] | None,
) -> None:
    kind = spec["type"]
    valid = True
    if kind == "str":
        valid = isinstance(value, str)
        if valid and "min_length" in spec:
            valid = len(value) >= spec["min_length"]
    elif kind == "int":
        valid = _is_int(value)
        if valid and "min" in spec:
            valid = value >= spec["min"]
        if valid and "max" in spec:
            valid = value <= spec["max"]
        if valid and "constant" in spec:
            valid = value == spec["constant"]
    elif kind == "bool":
        valid = isinstance(value, bool)
    elif kind == "enum":
        valid = isinstance(value, str) and value in spec["values"]
    if not valid:
        _problem(
            diagnostics,
            "invalid_field_value",
            f"{path or '<document>'} expects {kind}"
            + (f" {spec['values']!r}" if kind == "enum" else "")
            + f", not {_value_type_name(value)} {value!r}",
            relative_path=relative_path,
            field_path=path,
            provenance=provenance,
        )
        return
    if kind == "str" and "pattern" in spec:
        import re

        if not re.match(spec["pattern"], value):
            _problem(
                diagnostics,
                "invalid_field_value",
                f"{path} {value!r} does not match {spec['pattern']}",
                relative_path=relative_path,
                field_path=path,
                provenance=provenance,
            )
            return
    if kind == "str" and "constant" in spec and value != spec["constant"]:
        _problem(
            diagnostics,
            "invalid_field_value",
            f"{path} must be {spec['constant']!r}, not {value!r}",
            relative_path=relative_path,
            field_path=path,
            provenance=provenance,
        )


def _apply_rules(
    spec: Mapping[str, Any],
    value: Mapping[str, Any],
    path: str,
    diagnostics: list[Diagnostic],
    *,
    relative_path: str | None,
    provenance: Mapping[str, SourceLocation] | None,
) -> None:
    for rule in spec.get("rules", ()):
        name = rule["rule"]
        if name in ("required_when_equals", "forbidden_when_equals"):
            other = value.get(rule["other"])
            if other != rule["value"]:
                continue
            field = rule["field"]
            present = value.get(field) is not None
            if name == "required_when_equals" and not present:
                _problem(
                    diagnostics,
                    "missing_field",
                    f"{_join(path, field)} is required when "
                    f"{rule['other']} is {rule['value']!r}",
                    relative_path=relative_path,
                    field_path=_join(path, field),
                    provenance=provenance,
                )
            elif name == "forbidden_when_equals" and present:
                _problem(
                    diagnostics,
                    "invalid_field_value",
                    f"{_join(path, field)} is not allowed when "
                    f"{rule['other']} is {rule['value']!r}",
                    relative_path=relative_path,
                    field_path=_join(path, field),
                    provenance=provenance,
                )
        elif name in ("required_when_in", "forbidden_when_in"):
            other = value.get(rule["other"])
            if other not in rule["values"]:
                continue
            field = rule["field"]
            present = value.get(field) is not None
            if name == "required_when_in" and not present:
                _problem(
                    diagnostics,
                    "missing_field",
                    f"{_join(path, field)} is required when "
                    f"{rule['other']} is {other!r}",
                    relative_path=relative_path,
                    field_path=_join(path, field),
                    provenance=provenance,
                )
            elif name == "forbidden_when_in" and present:
                _problem(
                    diagnostics,
                    "invalid_field_value",
                    f"{_join(path, field)} is not allowed when "
                    f"{rule['other']} is {other!r}",
                    relative_path=relative_path,
                    field_path=_join(path, field),
                    provenance=provenance,
                )


def _validate_mask(
    value: list,
    path: str,
    diagnostics: list[Diagnostic],
    *,
    relative_path: str | None,
    provenance: Mapping[str, SourceLocation] | None,
) -> None:
    if not value:
        _problem(
            diagnostics,
            "invalid_mask",
            f"{path} is empty",
            relative_path=relative_path,
            field_path=path,
            provenance=provenance,
        )
        return
    width = len(value[0]) if isinstance(value[0], str) else 0
    if width == 0:
        _problem(
            diagnostics,
            "invalid_mask",
            f"{path} has an empty row",
            relative_path=relative_path,
            field_path=path,
            provenance=provenance,
        )
        return
    hash_cells = 0
    for index, row in enumerate(value):
        if not isinstance(row, str):
            continue
        if len(row) != width:
            _problem(
                diagnostics,
                "invalid_mask",
                f"{path}[{index}] is {len(row)} cells wide, expected {width}",
                relative_path=relative_path,
                field_path=f"{path}[{index}]",
                provenance=provenance,
            )
        for cell in row:
            if cell not in "#.":
                _problem(
                    diagnostics,
                    "invalid_mask",
                    f"{path}[{index}] contains {cell!r}; only '#' and '.' are allowed",
                    relative_path=relative_path,
                    field_path=f"{path}[{index}]",
                    provenance=provenance,
                )
            elif cell == "#":
                hash_cells += 1
    if hash_cells == 0:
        _problem(
            diagnostics,
            "invalid_mask",
            f"{path} contains no '#' cell",
            relative_path=relative_path,
            field_path=path,
            provenance=provenance,
        )


def _validate_list_rules(
    spec: Mapping[str, Any],
    value: list,
    path: str,
    diagnostics: list[Diagnostic],
    *,
    relative_path: str | None,
    provenance: Mapping[str, SourceLocation] | None,
) -> None:
    for rule in spec.get("rules", ()):
        if rule["rule"] == "unique_sequence":
            seen: dict[tuple, int] = {}
            for index, item in enumerate(value):
                if not isinstance(item, Mapping):
                    continue
                key = _hashable_identity(
                    item.get(name) for name in rule["fields"]
                )
                if key is None:
                    continue
                if key in seen:
                    _problem(
                        diagnostics,
                        "duplicate_identity",
                        f"{path}[{index}] repeats {path}[{seen[key]}] ({key!r})",
                        relative_path=relative_path,
                        field_path=f"{path}[{index}]",
                        provenance=provenance,
                    )
                else:
                    seen[key] = index
        elif rule["rule"] == "unique_outgoing":
            seen_direction: dict[tuple, int] = {}
            for index, item in enumerate(value):
                if not isinstance(item, Mapping):
                    continue
                key = _hashable_identity(
                    (item.get(rule["field"]), item.get(rule["other"]))
                )
                if key is None:
                    continue
                if key in seen_direction:
                    _problem(
                        diagnostics,
                        "duplicate_outgoing_direction",
                        f"{path}[{index}] repeats outgoing {rule['other']} "
                        f"{key[1]!r} from {key[0]!r} (conflicts with "
                        f"{path}[{seen_direction[key]}])",
                        relative_path=relative_path,
                        field_path=f"{path}[{index}]",
                        object_id=key[0] if isinstance(key[0], str) else None,
                        provenance=provenance,
                    )
                else:
                    seen_direction[key] = index


def _validate_value(
    spec: Mapping[str, Any],
    value: Any,
    path: str,
    diagnostics: list[Diagnostic],
    *,
    relative_path: str | None,
    provenance: Mapping[str, SourceLocation] | None,
    seen: set[int],
    depth: int,
) -> None:
    if depth > MAX_DOCUMENT_DEPTH:
        _problem(
            diagnostics,
            "invalid_document_depth",
            f"{path or '<document>'} exceeds {MAX_DOCUMENT_DEPTH} nested values",
            relative_path=relative_path,
            field_path=path,
            provenance=provenance,
        )
        return
    if value is None:
        if spec.get("nullable"):
            return
        _problem(
            diagnostics,
            "invalid_field_type",
            f"{path or '<document>'} is null",
            relative_path=relative_path,
            field_path=path,
            provenance=provenance,
        )
        return
    kind = spec["type"]
    if kind in ("str", "int", "bool", "enum"):
        _check_scalar(
            spec,
            value,
            path,
            diagnostics,
            relative_path=relative_path,
            provenance=provenance,
        )
        return
    if isinstance(value, (Mapping, list, tuple)):
        marker = id(value)
        if marker in seen:
            _problem(
                diagnostics,
                "cyclic_value",
                f"{path or '<document>'} contains a cyclic collection",
                relative_path=relative_path,
                field_path=path,
                provenance=provenance,
            )
            return
        seen.add(marker)
    if kind == "mapping":
        if not isinstance(value, Mapping):
            _problem(
                diagnostics,
                "invalid_field_type",
                f"{path} expects a mapping, not {_value_type_name(value)}",
                relative_path=relative_path,
                field_path=path,
                provenance=provenance,
            )
            return
        if len(value) > MAX_COLLECTION_ITEMS:
            _problem(
                diagnostics,
                "invalid_collection_size",
                f"{path} has {len(value)} entries, limit {MAX_COLLECTION_ITEMS}",
                relative_path=relative_path,
                field_path=path,
                provenance=provenance,
            )
            return
        fields = spec.get("fields", {})
        key_pattern = spec.get("key_pattern")
        for key, item in value.items():
            if not isinstance(key, str):
                _problem(
                    diagnostics,
                    "invalid_field_type",
                    f"{path} has a non-string key {key!r}",
                    relative_path=relative_path,
                    field_path=path,
                    provenance=provenance,
                )
                continue
            if fields:
                child_spec = fields.get(key)
                if child_spec is None:
                    _problem(
                        diagnostics,
                        "unknown_field",
                        f"{_join(path, key)} is not a supported field",
                        relative_path=relative_path,
                        field_path=_join(path, key),
                        provenance=provenance,
                    )
                    continue
            else:
                if key_pattern is not None:
                    import re

                    if not re.match(key_pattern, key):
                        _problem(
                            diagnostics,
                            "invalid_identifier",
                            f"{_join(path, key)} does not match {key_pattern}",
                            relative_path=relative_path,
                            field_path=_join(path, key),
                            provenance=provenance,
                        )
                        continue
                # A dynamic mapping of objects uses the object spec under
                # ``items``; a bare mapping has no per-value fields.
                child_spec = spec.get("items", {})
            _validate_value(
                child_spec,
                item,
                _join(path, key),
                diagnostics,
                relative_path=relative_path,
                provenance=provenance,
                seen=seen,
                depth=depth + 1,
            )
        for name, child_spec in fields.items():
            if child_spec.get("required", True) and name not in value:
                _problem(
                    diagnostics,
                    "missing_field",
                    f"{_join(path, name)} is required",
                    relative_path=relative_path,
                    field_path=_join(path, name),
                    provenance=provenance,
                )
        _apply_rules(
            spec,
            value,
            path,
            diagnostics,
            relative_path=relative_path,
            provenance=provenance,
        )
        unique = spec.get("unique_values")
        if unique and value:
            seen_values: dict[tuple, str] = {}
            for key, item in value.items():
                if not isinstance(item, Mapping):
                    continue
                identity = _hashable_identity(
                    item.get(name) for name in unique
                )
                if identity is None:
                    continue
                if identity in seen_values:
                    _problem(
                        diagnostics,
                        "duplicate_coordinate",
                        f"{path}.{key} repeats coordinate {identity!r} of "
                        f"{path}.{seen_values[identity]}",
                        relative_path=relative_path,
                        field_path=f"{path}.{key}",
                        object_id=key if isinstance(key, str) else None,
                        provenance=provenance,
                    )
                else:
                    seen_values[identity] = key
        seen.discard(marker)
        return
    if kind == "list":
        if not isinstance(value, (list, tuple)):
            _problem(
                diagnostics,
                "invalid_field_type",
                f"{path} expects a list, not {_value_type_name(value)}",
                relative_path=relative_path,
                field_path=path,
                provenance=provenance,
            )
            return
        if len(value) > spec.get("max_items", MAX_COLLECTION_ITEMS):
            _problem(
                diagnostics,
                "invalid_collection_size",
                f"{path} has {len(value)} entries",
                relative_path=relative_path,
                field_path=path,
                provenance=provenance,
            )
            return
        if len(value) < spec.get("min_items", 0):
            _problem(
                diagnostics,
                "invalid_collection_size",
                f"{path} has {len(value)} entries, minimum "
                f"{spec.get('min_items')}",
                relative_path=relative_path,
                field_path=path,
                provenance=provenance,
            )
        for index, item in enumerate(value):
            _validate_value(
                spec.get("items", {}),
                item,
                f"{path}[{index}]",
                diagnostics,
                relative_path=relative_path,
                provenance=provenance,
                seen=seen,
                depth=depth + 1,
            )
        if spec.get("mask"):
            _validate_mask(
                list(value),
                path,
                diagnostics,
                relative_path=relative_path,
                provenance=provenance,
            )
        _validate_list_rules(
            spec,
            list(value),
            path,
            diagnostics,
            relative_path=relative_path,
            provenance=provenance,
        )
        seen.discard(marker)
        return
    _problem(
        diagnostics,
        "invalid_field_type",
        f"{path} has an unsupported value type {_value_type_name(value)}",
        relative_path=relative_path,
        field_path=path,
        provenance=provenance,
    )


def validate_document(
    kind: str,
    data: Mapping[str, Any],
    *,
    relative_path: str | None = None,
    expected_identity: str | None = None,
    provenance: Mapping[str, SourceLocation] | None = None,
) -> tuple[Diagnostic, ...]:
    """Validate one parsed document value against the version-1 schema."""

    diagnostics: list[Diagnostic] = []
    meta = _DOCUMENT_KINDS.get(kind)
    if meta is None:
        diagnostics.append(
            Diagnostic(
                code="unsupported_kind",
                category=STRUCTURE,
                message=f"unsupported document kind {kind!r}",
                relative_path=relative_path,
                field_path="kind",
            )
        )
        return sorted_diagnostics(diagnostics)
    if not isinstance(data, Mapping):
        _problem(
            diagnostics,
            "invalid_field_type",
            "the document root must be a mapping",
            relative_path=relative_path,
            field_path="",
            provenance=None,
        )
        return sorted_diagnostics(diagnostics)
    meta = _DOCUMENT_KINDS[kind]
    _validate_value(
        {"type": "mapping", "fields": meta["fields"], "rules": meta.get("rules", ())},
        data,
        "",
        diagnostics,
        relative_path=relative_path,
        provenance=provenance,
        seen=set(),
        depth=0,
    )
    declared_kind = data.get("kind")
    if declared_kind != kind:
        _problem(
            diagnostics,
            "identity_mismatch",
            f"document kind {declared_kind!r} does not match the source {kind!r}",
            relative_path=relative_path,
            field_path="kind",
            provenance=provenance,
        )
        return sorted_diagnostics(diagnostics)
    declared_version = data.get("version")
    if declared_version != SCHEMA_VERSION:
        _problem(
            diagnostics,
            "unsupported_version",
            f"unsupported schema version {declared_version!r}; expected "
            f"{SCHEMA_VERSION}",
            relative_path=relative_path,
            field_path="version",
            provenance=provenance,
        )
    declared_identity = data.get("id")
    if expected_identity is not None and declared_identity != expected_identity:
        _problem(
            diagnostics,
            "identity_mismatch",
            f"document id {declared_identity!r} does not match the file "
            f"identity {expected_identity!r}",
            relative_path=relative_path,
            field_path="id",
            provenance=provenance,
        )
    return sorted_diagnostics(diagnostics)
