"""Transactional one-object repair exception, deliberately bypassing game rules."""

import math
from django.db import transaction

from server.console.errors import ConsoleError
from server.console.validation import resolve_target
from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort

FIELDS = {
    "set_attr": ({"op", "key", "value"}, {"category"}),
    "del_attr": ({"op", "key"}, {"category"}),
    "add_tag": ({"op", "key", "category"}, set()),
    "remove_tag": ({"op", "key", "category"}, set()),
    "set_location": ({"op", "value"}, set()),
}


def _invalid():
    raise ConsoleError("raw_edit_invalid")


def decode(value):
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            _invalid()
        return value
    if type(value) is list:
        return [decode(entry) for entry in value]
    if type(value) is not dict or any(not isinstance(key, str) for key in value):
        _invalid()
    if "$unserializable" in value:
        _invalid()
    if "$ref" in value:
        if set(value) - {"$ref", "typeclass", "key"}:
            _invalid()
        try:
            return resolve_target(value["$ref"])
        except ConsoleError as error:
            raise ConsoleError("raw_edit_invalid") from error
    return {key: decode(entry) for key, entry in value.items()}


def _prepare(operations):
    if not isinstance(operations, list):
        _invalid()
    prepared = []
    for operation in operations:
        if not isinstance(operation, dict) or not isinstance(operation.get("op"), str) or operation["op"] not in FIELDS:
            _invalid()
        required, optional = FIELDS[operation["op"]]
        if not required <= set(operation) or set(operation) - required - optional:
            _invalid()
        entry = dict(operation)
        if "key" in required and (not isinstance(entry["key"], str) or not entry["key"]):
            _invalid()
        if "category" in required | optional:
            entry.setdefault("category", None)
            if entry["category"] is not None and not isinstance(entry["category"], str):
                _invalid()
        if entry["op"] == "set_location":
            if entry["value"] is not None and (not isinstance(entry["value"], dict) or "$ref" not in entry["value"]):
                _invalid()
        if "value" in entry:
            entry["value"] = decode(entry["value"])
        prepared.append(entry)
    return prepared


def _refresh_handlers(entity):
    """Rebind mounted handlers only: raw must never provision default state."""
    traits = entity.__dict__.get("traits")
    if traits is not None:
        traits.trait_data = entity.attributes.get("traits", category="traits", default={}) or {}
        traits._cache.clear()
    sexual = entity.__dict__.get("sexual")
    if sexual is not None:
        handler = sexual._traits
        handler.trait_data = entity.attributes.get("sexual_traits", category="traits", default={}) or {}
        handler._cache.clear()


def apply_raw(target, operations):
    entity = resolve_target(target)
    prepared = _prepare(operations)
    attrs = {(entry["key"], entry["category"]): attribute_snapshot(entity, entry["key"], entry["category"]) for entry in prepared if entry["op"] in {"set_attr", "del_attr"}}
    location = entity.location
    containers = {obj for obj in (location, *(entry["value"] for entry in prepared if entry["op"] == "set_location")) if obj is not None}
    try:
        with transaction.atomic():
            for entry in prepared:
                op = entry["op"]
                if op == "set_attr":
                    entity.attributes.add(entry["key"], entry["value"], category=entry["category"])
                elif op == "del_attr":
                    entity.attributes.remove(entry["key"], category=entry["category"])
                elif op == "add_tag":
                    entity.tags.add(entry["key"], category=entry["category"])
                elif op == "remove_tag":
                    entity.tags.remove(entry["key"], category=entry["category"])
                else:
                    entity.location = entry["value"]
            _refresh_handlers(entity)
    except Exception:
        for (key, category), before in attrs.items():
            restore_attribute_best_effort(entity, key, before, category)
        entity.tags.reset_cache()
        entity.location = location
        _refresh_handlers(entity)
        for container in containers:
            container.contents_cache.init()
        raise
    return {"target": target}
