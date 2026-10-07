"""Non-creating entity reads shared by the runtime readers.

Every helper here reads existing state only. ``AttributeProperty`` descriptors
autocreate on access (``world/rules/status_query`` documents the same trap), so
the readers read stored Attributes through ``attributes.get(..., default=...)``
and never through a descriptor, and they read the component registry from the
stored ``component_names`` attribute rather than ``host.components.db_names``
(which materializes an empty list). Missing stored state therefore stays
missing (design §2).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Set as AbstractSet
from typing import Any

from web.gm.readers._json import entity_ref, json_value

#: Curated Evennia kinds in resolution order (most specific first).
_CURATED_KINDS = ("monsters", "npcs", "characters", "rooms")


def read_attr(entity: Any, key: str, default: Any = None, category: str | None = None) -> Any:
    """Read one stored Attribute without creating it."""
    attributes = getattr(entity, "attributes", None)
    if attributes is None or not hasattr(attributes, "get"):
        return default
    return attributes.get(key, default=default, category=category)


def dbref_of(entity: Any) -> int | None:
    pk = getattr(entity, "pk", None)
    return int(pk) if isinstance(pk, int) and not isinstance(pk, bool) else None


def key_of(entity: Any) -> str:
    key = getattr(entity, "key", None)
    return str(key) if isinstance(key, str) and key else ""


def label_of(entity: Any) -> str:
    """The display label of an entity: its key, else its dbref reference."""
    key = key_of(entity)
    if key:
        return key
    dbref = dbref_of(entity)
    return f"#{dbref}" if dbref is not None else "?"


def typeclass_of(entity: Any) -> str:
    return str(getattr(entity, "db_typeclass_path", "") or "")


def ref_of(entity: Any) -> dict[str, Any] | None:
    """The ``$ref`` payload for an entity, or ``None`` for a non-entity."""
    return entity_ref(entity)


def attributes_of(entity: Any) -> list[Any]:
    attributes = getattr(entity, "attributes", None)
    if attributes is None or not hasattr(attributes, "all"):
        return []
    return list(attributes.all())


def attribute_rows(entity: Any) -> list[dict[str, Any]]:
    """Every stored Attribute as ``{key, category, value}`` (sorted)."""
    rows = [
        {
            "key": str(getattr(attribute, "key", "")),
            "category": str(getattr(attribute, "category", "") or ""),
            "value": json_value(getattr(attribute, "value", None)),
        }
        for attribute in attributes_of(entity)
    ]
    rows.sort(key=lambda row: (row["category"], row["key"]))
    return rows


def tag_rows(entity: Any) -> list[dict[str, Any]]:
    """Every Tag as ``{key, category}`` (sorted)."""
    tags = getattr(entity, "tags", None)
    if tags is None or not hasattr(tags, "all"):
        return []
    rows = [
        {
            "key": str(getattr(tag, "db_key", "")),
            "category": str(getattr(tag, "db_category", "") or ""),
        }
        for tag in tags.all()
    ]
    rows.sort(key=lambda row: (row["category"], row["key"]))
    return rows


def component_names(entity: Any) -> list[str]:
    """The stored component registry, read without provisioning anything."""
    stored = read_attr(entity, "component_names", default=None)
    names = sequence_values(stored)
    if names is None:
        return []
    return [str(name) for name in names if isinstance(name, str)]


def sequence_values(value: Any) -> list[Any] | None:
    """The items of a stored sequence, or ``None`` when the value is not one.

    Evennia returns stored containers as ``dbserialize`` wrappers
    (``MutableSequence``/``MutableSet``), never the concrete builtins, so the
    abstract base classes are the only correct test: a concrete ``isinstance``
    would report every stored list as absent (or malformed).
    """
    if value is None or isinstance(value, (str, bytes, bytearray, Mapping)):
        return None
    if not isinstance(value, (Sequence, AbstractSet)):
        return None
    return list(value)


def mapping_values(value: Any) -> dict[Any, Any] | None:
    """The entries of a stored mapping, or ``None`` when it is not one."""
    if not isinstance(value, Mapping):
        return None
    return dict(value)


def component_rows(entity: Any) -> list[dict[str, Any]]:
    """Existing components with the field Attributes they own on this host.

    Component DBFields are stored on the host under ``<slot>::<field>``
    (evennia's components contrib), so the fields are grouped out of the same
    attribute inventory the raw tab already lists — no handler is constructed.
    """
    names = component_names(entity)
    if not names:
        return []
    rows: list[dict[str, Any]] = []
    fields_by_slot: dict[str, dict[str, Any]] = {name: {} for name in names}
    for attribute in attributes_of(entity):
        key = str(getattr(attribute, "key", ""))
        if "::" not in key:
            continue
        slot, _, field = key.partition("::")
        if slot in fields_by_slot and field:
            fields_by_slot[slot][field] = json_value(getattr(attribute, "value", None))
    for name in names:
        rows.append({"name": name, "fields": fields_by_slot[name]})
    return rows


def stored_attribute_keys(entity: Any) -> set[tuple[str, str]]:
    """``(key, category)`` pairs of every stored Attribute (test/parity aid)."""
    return {
        (str(getattr(attribute, "key", "")), str(getattr(attribute, "category", "") or ""))
        for attribute in attributes_of(entity)
    }


def object_kind(entity: Any) -> str | None:
    """The curated kind of an Evennia entity, or ``None`` when uncurated."""
    from typeclasses.characters import PlayerCharacter
    from typeclasses.monsters import Monster
    from typeclasses.npcs import NPC
    from typeclasses.rooms import Room

    if isinstance(entity, Monster):
        return "monsters"
    if isinstance(entity, NPC):
        return "npcs"
    if isinstance(entity, PlayerCharacter):
        return "characters"
    if isinstance(entity, Room):
        return "rooms"
    from evennia.accounts.models import AccountDB

    if isinstance(entity, AccountDB):
        return "accounts"
    return None


def identity_text(entity: Any) -> str:
    """The identifier the UI shows in monospace: ``#<dbref>`` when there is one."""
    dbref = dbref_of(entity)
    return f"#{dbref}" if dbref is not None else ""


__all__ = [
    "attribute_rows",
    "attributes_of",
    "component_names",
    "component_rows",
    "dbref_of",
    "identity_text",
    "key_of",
    "label_of",
    "mapping_values",
    "object_kind",
    "read_attr",
    "ref_of",
    "sequence_values",
    "stored_attribute_keys",
    "tag_rows",
    "typeclass_of",
]
