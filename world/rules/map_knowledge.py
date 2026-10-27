"""Sole writer of the player's visited-node map knowledge (map-knowledge-minimap).

This module owns ``character.db.map_knowledge``, a JSON-safe versioned record of
canonical node IDs the player has entered. It is the only module that writes or
prunes that attribute; presenters and adapters read exclusively through
:func:`parse_knowledge`.

Node IDs use strict per-layer grammar (design D2):

- ``grid:<z-map-key>:<x>:<y>`` for the Grid/Anchor layer, bounded by the
  declared sparse settlement graph's own coordinate extent.
- ``wild:<wilderness-name>:<x>:<y>`` for the Wilderness layer, bounded by
  ``WILDERNESS_MAX_X``/``WILDERNESS_MAX_Y``.
- ``room:<dbref>`` for Instance and ordinary interior rooms, where ``dbref``
  is a positive integer.

``record_arrival`` records discovery only after a successful arrival and never
raises from a movement hook; a corrupt pre-existing record is logged and left
untouched. ``prune_reclaimed_room`` removes a reclaimed ephemeral room's
``room:<dbref>`` from every affected player in one transaction with
snapshot/restore on failure.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from copy import deepcopy
from typing import Any

from world.observability import log_info, log_warn
from world.maps import wilderness_provider
from world.maps.wilderness_provider import WILDERNESS_NAME

# The persisted record schema version. All stored records carry this literal.
SCHEMA_VERSION = 1
KNOWLEDGE_ATTR = "map_knowledge"

# Node-ID bounds (mirrored by the D10a presentation payload table).
MAX_NODE_ID_CHARS = 128
MAX_COMPONENT_CHARS = 64

_GRID_PREFIX = "grid"
_WILD_PREFIX = "wild"
_ROOM_PREFIX = "room"


class KnowledgeError(ValueError):
    """A map-knowledge record is missing, malformed, or has invalid content."""


class NodeIDError(KnowledgeError):
    """A node ID violates the strict per-layer grammar or its bounds."""


class KnowledgePruneError(RuntimeError):
    """A reclaimed-room knowledge prune failed on a genuine persistence failure."""


@dataclass(frozen=True)
class NodeVisit:
    """One normalized, deterministic read view of a visited node.

    Attributes:
        node_id: The canonical node ID.
        first_seen_tick: The world tick of the first recorded arrival.
        last_seen_tick: The world tick of the most recent recorded arrival.
    """

    node_id: str
    first_seen_tick: int
    last_seen_tick: int


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validated_visits(record: Any) -> dict[str, dict[str, int]]:
    """Strictly parse a stored record's ``visited`` mapping, raising on corrupt.

    The returned dict is a plain copy so the caller never mutates the stored
    value through a shared reference. Node IDs must decode and ticks must be
    non-negative integers.
    """
    if not isinstance(record, Mapping):
        raise KnowledgeError("map-knowledge record is not an object")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise KnowledgeError(
            f"map-knowledge record has unknown schema version {record.get('schema_version')!r}"
        )
    visited = record.get("visited")
    if not isinstance(visited, Mapping):
        raise KnowledgeError("map-knowledge record has no visited mapping")
    result: dict[str, dict[str, int]] = {}
    for node_id, value in visited.items():
        decode_node(node_id)
        if not isinstance(value, Mapping) or set(value) != {"first_seen_tick", "last_seen_tick"}:
            raise KnowledgeError(f"visited entry {node_id!r} is not an observation pair")
        first = value.get("first_seen_tick")
        last = value.get("last_seen_tick")
        if not _is_non_negative_int(first) or not _is_non_negative_int(last):
            raise KnowledgeError(f"visited entry {node_id!r} has a non-integer tick")
        result[node_id] = {"first_seen_tick": first, "last_seen_tick": last}
    return result


def _registered_grid_bounds(z_map_key: str) -> tuple[int, int] | None:
    """Return ``(max_X, max_Y)`` for a registered grid map, or ``None``.

    Resolves through the declared sparse settlement graph, so the bounds are
    the authored node extent rather than a duplicated constant or a dense
    lattice's ``max_X``/``max_Y`` (design D2). The lookup is pure Python: a
    validation path can never write the database or depend on provisioning.
    """
    from world.maps.map_data import settlement_graph

    graph = settlement_graph(z_map_key)
    if graph is not None:
        return int(graph.max_x), int(graph.max_y)

    # Synthetic/builder grids are not authored settlements; they still resolve
    # their extent from the live xyzgrid without creating it on a pure read.
    try:
        from evennia.contrib.grid.xyzgrid.xyzgrid import XYZGrid, get_xyzgrid

        if not XYZGrid.objects.exists():
            return None
        xymap = get_xyzgrid().get_map(z_map_key)
    except Exception:  # observability: ignore R2: read-only grid probe; an unavailable grid is reported as None and handled by the caller
        return None
    if xymap is None:
        return None
    return int(xymap.max_X), int(xymap.max_Y)


def encode_grid(z_map_key: str, x: int, y: int) -> str:
    """Return the canonical ``grid:`` node ID, validating every component."""
    if not isinstance(z_map_key, str) or not z_map_key:
        raise NodeIDError("grid z-map-key must be a non-empty string")
    if ":" in z_map_key or len(z_map_key) > MAX_COMPONENT_CHARS:
        raise NodeIDError("grid z-map-key must be a bounded string without ':'")
    if not _is_non_negative_int(x) or not _is_non_negative_int(y):
        raise NodeIDError("grid coordinates must be non-negative integers")
    node_id = f"{_GRID_PREFIX}:{z_map_key}:{x}:{y}"
    if len(node_id) > MAX_NODE_ID_CHARS:
        raise NodeIDError("grid node ID exceeds the maximum node-ID length")
    return node_id


def encode_wild(name: str, x: int, y: int) -> str:
    """Return the canonical ``wild:`` node ID, validating every component."""
    if name != WILDERNESS_NAME:
        raise NodeIDError(
            f"wilderness-name must be the registered {WILDERNESS_NAME!r}"
        )
    if not _is_non_negative_int(x) or not _is_non_negative_int(y):
        raise NodeIDError("wilderness coordinates must be non-negative integers")
    if x > wilderness_provider.WILDERNESS_MAX_X or y > wilderness_provider.WILDERNESS_MAX_Y:
        raise NodeIDError("wilderness coordinates exceed the provider bounds")
    node_id = f"{_WILD_PREFIX}:{name}:{x}:{y}"
    if len(node_id) > MAX_NODE_ID_CHARS:
        raise NodeIDError("wilderness node ID exceeds the maximum node-ID length")
    return node_id


def encode_room(dbref: int) -> str:
    """Return the canonical ``room:`` node ID for a positive integer dbref."""
    if isinstance(dbref, bool) or not isinstance(dbref, int) or dbref <= 0:
        raise NodeIDError("room dbref must be a positive integer")
    node_id = f"{_ROOM_PREFIX}:{dbref}"
    if len(node_id) > MAX_NODE_ID_CHARS:
        raise NodeIDError("room node ID exceeds the maximum node-ID length")
    return node_id


def decode_node(node_id: Any) -> dict[str, Any]:
    """Strictly decode one canonical node ID into its components.

    Returns a dict with ``prefix`` and per-layer fields, or raises
    :class:`NodeIDError` for any malformed, unknown, or out-of-bounds value.
    """
    if not isinstance(node_id, str):
        raise NodeIDError("node ID must be a string")
    if len(node_id) > MAX_NODE_ID_CHARS:
        raise NodeIDError("node ID exceeds the maximum node-ID length")
    parts = node_id.split(":")
    prefix = parts[0]
    if prefix == _GRID_PREFIX:
        if len(parts) != 4:
            raise NodeIDError("grid node ID must have exactly z-map-key, x, y")
        z_map_key, x_raw, y_raw = parts[1], parts[2], parts[3]
        if not z_map_key or ":" in z_map_key or len(z_map_key) > MAX_COMPONENT_CHARS:
            raise NodeIDError("grid z-map-key must be a bounded string without ':'")
        if not x_raw.lstrip("-").isdigit() or not y_raw.lstrip("-").isdigit():
            raise NodeIDError("grid coordinates must be integers")
        x, y = int(x_raw), int(y_raw)
        if not _is_non_negative_int(x) or not _is_non_negative_int(y):
            raise NodeIDError("grid coordinates must be non-negative integers")
        bounds = _registered_grid_bounds(z_map_key)
        if bounds is None:
            raise NodeIDError(f"grid z-map-key {z_map_key!r} is not a registered map")
        max_x, max_y = bounds
        if x > max_x or y > max_y:
            raise NodeIDError("grid coordinates exceed the registered map bounds")
        return {"prefix": _GRID_PREFIX, "z_map_key": z_map_key, "x": x, "y": y}
    if prefix == _WILD_PREFIX:
        if len(parts) != 4:
            raise NodeIDError("wilderness node ID must have exactly name, x, y")
        name, x_raw, y_raw = parts[1], parts[2], parts[3]
        if name != WILDERNESS_NAME:
            raise NodeIDError(
                f"wilderness-name must be the registered {WILDERNESS_NAME!r}"
            )
        if not x_raw.lstrip("-").isdigit() or not y_raw.lstrip("-").isdigit():
            raise NodeIDError("wilderness coordinates must be integers")
        x, y = int(x_raw), int(y_raw)
        if not _is_non_negative_int(x) or not _is_non_negative_int(y):
            raise NodeIDError("wilderness coordinates must be non-negative integers")
        if x > wilderness_provider.WILDERNESS_MAX_X or y > wilderness_provider.WILDERNESS_MAX_Y:
            raise NodeIDError("wilderness coordinates exceed the provider bounds")
        return {"prefix": _WILD_PREFIX, "name": name, "x": x, "y": y}
    if prefix == _ROOM_PREFIX:
        if len(parts) != 2:
            raise NodeIDError("room node ID must have exactly one dbref")
        dbref_raw = parts[1]
        if not dbref_raw.isdigit():
            raise NodeIDError("room dbref must be a positive integer")
        dbref = int(dbref_raw)
        if dbref <= 0:
            raise NodeIDError("room dbref must be a positive integer")
        return {"prefix": _ROOM_PREFIX, "dbref": dbref}
    raise NodeIDError(f"unknown node-ID prefix {prefix!r}")


def validate_node(node_id: Any) -> bool:
    """Return ``True`` when ``node_id`` decodes, ``False`` otherwise."""
    try:
        decode_node(node_id)
    except NodeIDError:  # observability: ignore R2: the predicate's False return is the caller-visible result
        return False
    return True


def _derive_node_id(location: Any) -> str | None:
    """Return the canonical node ID for a location, or ``None`` when unrepresentable.

    Grid/Anchor rooms derive ``grid:`` from their live ``.xyz``; Terrain rooms
    derive ``wild:`` from their live coordinates; every other room (Instance,
    plain interior, Limbo) derives ``room:<dbref>``. Nothing else represents a
    canonical node.
    """
    if location is None:
        return None
    from typeclasses.rooms import GridRoom, TerrainRoom

    if isinstance(location, GridRoom):
        x, y, z = location.xyz
        return encode_grid(z, x, y)
    if isinstance(location, TerrainRoom):
        x, y = location.coordinates
        return encode_wild(WILDERNESS_NAME, x, y)
    if not getattr(location, "id", None):
        return None
    return encode_room(int(location.id))


def record_arrival(character: Any) -> None:
    """Record one successful arrival for a ``PlayerCharacter`` at its location.

    No-op (and never raises) for a non-``PlayerCharacter``, an unrepresentable
    location, or a corrupt pre-existing record -- which is logged with a safe
    diagnostic and never overwritten or reset. A fresh record is created on the
    first observation. The whole write path is exception-isolated so a genuine
    persistence or derivation failure from a movement hook can never bubble up
    into a successful traversal.
    """
    from typeclasses.characters import PlayerCharacter

    if not isinstance(character, PlayerCharacter):
        return
    try:
        node_id = _derive_node_id(character.location)
        if node_id is None:
            return
        current = character.attributes.get(KNOWLEDGE_ATTR)
        if current is None:
            record: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "visited": {}}
        else:
            try:
                visits = _validated_visits(current)
            except KnowledgeError as error:
                log_warn(
                    "map_knowledge_record_corrupt",
                    exc=error,
                    context={"obj": str(character), "key": KNOWLEDGE_ATTR},
                )
                return
            record = {"schema_version": SCHEMA_VERSION, "visited": visits}

        from world.rules.clock import get_world_clock

        tick = get_world_clock().tick
        entry = record["visited"].get(node_id)
        if entry is None:
            record["visited"][node_id] = {"first_seen_tick": tick, "last_seen_tick": tick}
        else:
            record["visited"][node_id] = {
                "first_seen_tick": entry["first_seen_tick"],
                "last_seen_tick": tick,
            }
        character.attributes.add(KNOWLEDGE_ATTR, record)
    except Exception as error:
        log_warn(
            "map_knowledge_record_arrival_failed",
            exc=error,
            context={"obj": str(character), "key": KNOWLEDGE_ATTR},
        )


def parse_knowledge(character: Any) -> list[NodeVisit]:
    """Return a normalized, deterministically ordered view of the knowledge.

    Raises :class:`KnowledgeError` (never resets the stored value) when the
    record is missing, malformed, has an unknown schema version, contains an
    invalid node ID, or has non-integer ticks. The returned list is ordered by
    ``node_id``, independent of dict insertion order.
    """
    current = character.attributes.get(KNOWLEDGE_ATTR)
    if current is None:
        raise KnowledgeError("character has no map-knowledge record")
    visits = _validated_visits(current)
    return sorted(
        (
            NodeVisit(
                node_id=node_id,
                first_seen_tick=entry["first_seen_tick"],
                last_seen_tick=entry["last_seen_tick"],
            )
            for node_id, entry in visits.items()
        ),
        key=lambda visit: visit.node_id,
    )


def _write_knowledge(character: Any, record: dict[str, Any]) -> None:
    """Persist ``record`` onto ``character`` (the injectable write seam)."""
    character.attributes.add(KNOWLEDGE_ATTR, record)


def _characters_with_knowledge() -> list[Any]:
    """Return every ``PlayerCharacter`` that already carries the attribute."""
    from typeclasses.characters import PlayerCharacter

    return list(
        PlayerCharacter.objects.all_family().filter(
            db_attributes__db_key=KNOWLEDGE_ATTR
        )
    )


def remap_grid_identities(
    map_id: str,
    bindings: Mapping[tuple[int, int], tuple[int, int]],
    *,
    journal: list | None = None,
) -> int:
    """Rewrite moved grid nodes' stored identities, preserving observation.

    ``bindings`` maps each old ``(x, y)`` binding to its new one for one
    settlement map. The knowledge owner is the sole writer of these records,
    so a coordinate cutover remaps the existing ``grid:`` ids here instead of
    letting the next arrival record a fresh observation. First/last seen ticks
    are preserved; an old and new id that collapse onto one node merge by the
    earliest first-seen and the latest last-seen tick.

    ``journal`` is the caller's mutation log: each character is registered
    BEFORE its write is attempted, so a failed transaction can invalidate the
    process-local attribute caches of every character whose durable record
    will roll back. Returns the number of characters written.
    """

    if not bindings:
        return 0
    mapping = {
        encode_grid(map_id, old[0], old[1]): encode_grid(map_id, new[0], new[1])
        for old, new in bindings.items()
        if tuple(old) != tuple(new)
    }
    if not mapping:
        return 0

    written = 0
    for character in _characters_with_knowledge():
        current = character.attributes.get(KNOWLEDGE_ATTR)
        try:
            visits = _validated_visits(current)
        except KnowledgeError as error:
            log_warn(
                "map_knowledge_remap_skipped_corrupt_record",
                exc=error,
                context={"obj": str(character), "key": KNOWLEDGE_ATTR, "map_id": map_id},
            )
            continue
        remapped: dict[str, dict[str, int]] = {}
        changed = False
        for node_id, entry in visits.items():
            target = mapping.get(node_id, node_id)
            if target != node_id:
                changed = True
            existing = remapped.get(target)
            if existing is None:
                remapped[target] = dict(entry)
            else:
                existing["first_seen_tick"] = min(
                    existing["first_seen_tick"], entry["first_seen_tick"]
                )
                existing["last_seen_tick"] = max(
                    existing["last_seen_tick"], entry["last_seen_tick"]
                )
        if not changed:
            continue
        if journal is not None and not any(
            entry_character is character for entry_character, _ in journal
        ):
            # The snapshot restores the durable value even if the failed
            # transaction's rollback is not observable through the handler.
            # Each character is journalled once, before its FIRST mutation: a
            # character observed in both settlements must roll back to its
            # pre-startup record, never to a partially remapped one.
            journal.append((character, deepcopy(current)))
        _write_knowledge(
            character, {"schema_version": SCHEMA_VERSION, "visited": remapped}
        )
        written += 1
    if written:
        log_info(
            "map_knowledge_coordinates_remapped",
            context={
                "map_id": map_id,
                "nodes": len(mapping),
                "characters": written,
            },
        )
    return written


def prune_reclaimed_room(room_id: int) -> bool:
    """Remove ``room:<room_id>`` from every affected player's record.

    Selects only characters already carrying the knowledge attribute, strictly
    parses each record (a corrupt one is left untouched with a diagnostic),
    writes back only records that actually contain the target node, snapshots
    every affected value before mutation, and restores every snapshot on any
    write failure. Returns a boolean success indicator and raises the dedicated
    :class:`KnowledgePruneError` only on a genuine persistence failure.
    """
    target = encode_room(room_id)
    touched: list[Any] = []
    snapshots: list[dict[str, Any]] = []
    for character in _characters_with_knowledge():
        current = character.attributes.get(KNOWLEDGE_ATTR)
        try:
            visits = _validated_visits(current)
        except KnowledgeError as error:
            log_warn(
                "map_knowledge_prune_skipped_corrupt_record",
                exc=error,
                context={"obj": str(character), "key": KNOWLEDGE_ATTR, "room_id": room_id},
            )
            continue
        if target not in visits:
            continue
        pruned = {
            node_id: entry for node_id, entry in visits.items() if node_id != target
        }
        touched.append(character)
        snapshots.append(deepcopy(current))
        try:
            _write_knowledge(character, {"schema_version": SCHEMA_VERSION, "visited": pruned})
        except Exception as error:
            for character_restore, snapshot in zip(touched, snapshots):
                try:
                    _write_knowledge(character_restore, snapshot)
                except Exception as restore_error:
                    log_warn(
                        "rollback_restore_failed",
                        exc=restore_error,
                        context={
                            "stage": "map_knowledge_prune_restore",
                            "obj": str(character_restore),
                            "key": KNOWLEDGE_ATTR,
                        },
                    )
            log_warn(
                "map_knowledge_prune_failed",
                exc=error,
                context={
                    "room_id": room_id,
                    "obj": str(character),
                    "key": KNOWLEDGE_ATTR,
                    "restored_count": len(touched),
                },
            )
            raise KnowledgePruneError(
                f"failed to prune reclaimed room {room_id}"
            ) from error
    return True
