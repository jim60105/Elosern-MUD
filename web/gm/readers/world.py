"""Read-only authored world-data readers (gm-portal-s4-world-data §3/§5).

Every read goes through ``world.lore.registry_index``: the inventory, one
registry's entries, cross-registry search and one entry's fields with its
forward references and inverse referrers. The values are what the server
process loaded through each registry's own loader, never a fresh read of
source, and nothing here writes (the reader AST contract applies).

Entries are converted with the authored serialisation semantics of
``world/lore/sync.py`` ``_db_safe`` (enum to value, tuple to list) recursing
into nested dataclasses; a value JSON cannot carry becomes the shared
``$unserializable`` marker. Reference ``field_path`` strings use the same
shape as the converted JSON (``stages[0].objective.species_key``), so the
browser can attach a link to the exact leaf.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from enum import Enum
from typing import Any

from web.gm import pagination
from web.gm.readers._json import bounded_repr
from web.gm.readers.errors import EntryNotFound, InvalidQuery, RegistryNotFound

#: The longest accepted search text.
MAX_QUERY_CHARS = 200

#: Field names that carry an entry's display label, in preference order.
LABEL_FIELDS = ("display_name_zh", "display_name", "label", "room_name_zh", "name", "title")

#: Recursion bound for the conversion (authored data is shallow).
MAX_DEPTH = 24


def _index():
    from world.lore import registry_index

    return registry_index


def specs() -> tuple[Any, ...]:
    return _index().REGISTRY_INDEX


def spec_of(name: str) -> Any:
    spec = _index().spec_by_name(str(name), specs())
    if spec is None:
        raise RegistryNotFound()
    return spec


def entries_of(spec: Any) -> Mapping[str, Any]:
    return spec.loader()


# --- conversion ---------------------------------------------------------------


def _members(value: Any) -> list[Any]:
    return sorted(value, key=lambda item: (type(item).__name__, str(item)))


def authored_value(value: Any, depth: int = 0) -> Any:
    """One authored value as JSON (``_db_safe`` semantics, recursive)."""
    if depth > MAX_DEPTH:
        return {"$unserializable": type(value).__name__, "repr": bounded_repr(value)}
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, Enum):
        return authored_value(value.value, depth + 1)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return {"$unserializable": "float", "repr": bounded_repr(value)}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: authored_value(getattr(value, field.name), depth + 1)
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): authored_value(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return [authored_value(item, depth + 1) for item in _members(value)]
    if isinstance(value, (list, tuple)):
        return [authored_value(item, depth + 1) for item in value]
    return {"$unserializable": type(value).__name__, "repr": bounded_repr(value)}


def entry_label(entry: Any) -> str | None:
    """The entry's display name, when it declares one."""
    for name in LABEL_FIELDS:
        value = getattr(entry, name, None)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _path_value(entry: Any, path: str) -> Any:
    value = entry
    for part in path.split("."):
        value = getattr(value, part, None)
        if value is None:
            return None
    return value


def summary_fields(spec: Any, entries: Mapping[str, Any]) -> tuple[str, ...]:
    """Declared summary fields, else the first string field other than the key."""
    if spec.summary_fields:
        return tuple(spec.summary_fields)
    for entry in entries.values():
        if dataclasses.is_dataclass(entry):
            for field in dataclasses.fields(entry):
                if field.name != "key" and isinstance(getattr(entry, field.name), str):
                    return (field.name,)
        break
    return ()


def registry_meta(spec: Any, entries: Mapping[str, Any] | None = None) -> dict[str, Any]:
    loaded = entries if entries is not None else entries_of(spec)
    return {
        "name": spec.name,
        "label": spec.label,
        "group": spec.group,
        "entry_count": len(loaded),
        "source_path": spec.source_path,
        "summary_fields": list(summary_fields(spec, loaded)),
    }


# --- inventory and search -------------------------------------------------------


def inventory() -> dict[str, Any]:
    """Every indexed registry, grouped in navigation order."""
    groups = _index().GROUPS
    ordered = sorted(
        specs(),
        key=lambda spec: groups.index(spec.group) if spec.group in groups else len(groups),
    )
    return {"groups": list(groups), "items": [registry_meta(spec) for spec in ordered]}


def normalize_query(raw: Any) -> str:
    text = str(raw or "").strip()
    if len(text) > MAX_QUERY_CHARS:
        raise InvalidQuery(f"查詢文字超過 {MAX_QUERY_CHARS} 字元上限。")
    return text


def _string_leaves(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _string_leaves(item)
    elif isinstance(value, list):
        for item in value:
            yield from _string_leaves(item)


def matches(key: str, entry: Any, needle: str) -> bool:
    """Case-insensitive substring match on the key and every string leaf."""
    if needle in str(key).casefold():
        return True
    return any(needle in leaf.casefold() for leaf in _string_leaves(authored_value(entry)))


def search(raw_query: Any) -> dict[str, Any]:
    """All matching ``{registry, key}`` identities across every registry."""
    query = normalize_query(raw_query)
    if not query:
        raise InvalidQuery("請輸入查詢文字。")
    needle = query.casefold()
    found = [
        {"registry": spec.name, "key": str(key)}
        for spec in specs()
        for key, entry in entries_of(spec).items()
        if matches(str(key), entry, needle)
    ]
    found.sort(key=lambda item: (item["registry"], item["key"]))
    return {"items": found}


# --- entry list -----------------------------------------------------------------


def list_item(spec: Any, key: str, entry: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        "key": str(key),
        "label": entry_label(entry),
        "summary": [
            {"field": name, "value": authored_value(_path_value(entry, name))} for name in fields
        ],
    }


def build_list(name: str, params: Any) -> dict[str, Any]:
    """One registry's entries in stable key order, query-filtered and paged."""
    spec = spec_of(name)
    limit = pagination.parse_limit(params.get("limit"))
    query = normalize_query(params.get("q"))
    filters = {"registry": spec.name, "q": query}
    offset = pagination.decode_cursor(params.get("cursor"), filters) if params.get("cursor") else 0
    entries = entries_of(spec)
    fields = summary_fields(spec, entries)
    needle = query.casefold()
    keys = sorted(str(key) for key in entries)
    rows = [
        list_item(spec, key, entries[key], fields)
        for key in keys
        if not needle or matches(key, entries[key], needle)
    ]
    data = pagination.envelope(rows, offset, limit, filters)
    data["registry"] = registry_meta(spec, entries)
    data["q"] = query
    data["total"] = len(rows)
    return data


# --- detail ---------------------------------------------------------------------


def _target_label(registry: str, key: Any) -> tuple[bool, str | None, str | None]:
    """``(exists, entry label, registry label)`` of one reference target."""
    spec = _index().spec_by_name(registry, specs())
    if spec is None:
        return False, None, None
    entries = entries_of(spec)
    if not isinstance(key, str) or key not in entries:
        return False, None, spec.label
    return True, entry_label(entries[key]), spec.label


def detail(name: str, key: str) -> dict[str, Any]:
    """One entry: converted fields, references by field path, grouped referrers."""
    spec = spec_of(name)
    entries = entries_of(spec)
    if key not in entries:
        raise EntryNotFound()
    entry = entries[key]
    index = _index().build_reference_index(specs())
    references = []
    for reference in index.forward.get((spec.name, key), ()):
        exists, label, registry_label = _target_label(reference.target_registry, reference.target_key)
        references.append(
            {
                "field_path": reference.field_path,
                "registry": reference.target_registry,
                "registry_label": registry_label,
                "key": None if reference.target_key is None else str(reference.target_key),
                "label": label,
                "exists": exists,
                "inverse": reference.inverse,
            }
        )
    referrers = []
    for inverse_name, items in sorted(index.inverse.get((spec.name, key), {}).items()):
        rows = []
        for reference in sorted(items, key=lambda item: (item.registry, item.key, item.field_path)):
            _exists, label, registry_label = _target_label(reference.registry, reference.key)
            rows.append(
                {
                    "registry": reference.registry,
                    "registry_label": registry_label,
                    "key": reference.key,
                    "label": label,
                    "field_path": reference.field_path,
                }
            )
        referrers.append({"inverse": inverse_name, "items": rows})
    return {
        "registry": registry_meta(spec, entries),
        "key": key,
        "label": entry_label(entry),
        "type": type(entry).__name__,
        "fields": authored_value(entry),
        "references": references,
        "referrers": referrers,
    }


def authored_link(registry: str, key: Any, label: str | None = None) -> dict[str, Any] | None:
    """A runtime-page link to one authored entry, or ``None`` when absent.

    S3 runtime readers attach this to fields that hold registry keys (race,
    species, variant, quest definition, ...). A key the authored index does not
    hold (for example a runtime-generated quest definition) gets no link.
    """
    if key is None or key == "":
        return None
    try:
        spec = spec_of(registry)
        present = str(key) in entries_of(spec)
    except Exception:  # observability: ignore R2: a broken loader degrades to an unlinked value; the world-data page reports it
        return None
    if not present:
        return None
    value: dict[str, Any] = {"kind": "registry", "registry": spec.name, "id": str(key)}
    if label:
        value["label"] = str(label)
    return value


__all__ = [
    "LABEL_FIELDS",
    "MAX_QUERY_CHARS",
    "authored_link",
    "authored_value",
    "build_list",
    "detail",
    "entry_label",
    "inventory",
    "matches",
    "normalize_query",
    "registry_meta",
    "search",
    "spec_of",
    "summary_fields",
]
