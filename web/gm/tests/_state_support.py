"""Shared fixed-fixture helpers for the runtime state reader tests.

Not a test module: it holds the small accessors every reader test uses to make
an assertion about the section vocabulary without re-implementing the payload
shape. ``section_of``/``row_value``/``column_values`` read the exact wire
contract the SPA consumes; ``link_kinds`` proves that every identifier the
payload displays is rendered as a link (design §3).
"""

from __future__ import annotations

from typing import Any


def open_synthetic_scope(case: Any, *logicals: str, extra: Any = None) -> Any:
    """Enter a synthetic catalog scope bound to one test case's lifecycle.

    A reader test builds its fixtures in ``setUp``, which runs *before* the
    decorated test method, so the scope must open in ``setUp`` itself (the
    documented ``world/art/tests/test_gallery_updates`` pattern).
    """
    from world.tests.synthetic_data import synthetic_registries

    scope = synthetic_registries(*logicals, extra=extra)
    scope.__enter__()
    case.addCleanup(scope.__exit__, None, None, None)
    return scope


def section_keys(detail: dict[str, Any]) -> list[str]:
    return [section["key"] for section in detail["sections"]]


def section_of(detail: dict[str, Any], key: str) -> dict[str, Any]:
    for section in detail["sections"]:
        if section["key"] == key:
            return section
    raise AssertionError(f"section {key!r} missing from {section_keys(detail)}")


def failed_sections(detail: dict[str, Any]) -> dict[str, str]:
    return {
        section["key"]: section["error"]["code"]
        for section in detail["sections"]
        if "error" in section
    }


def row_value(section: dict[str, Any], label: str) -> Any:
    for entry in section.get("rows", []):
        if entry.get("label") == label:
            return entry.get("value")
    raise AssertionError(f"row {label!r} missing from {sorted(r.get('label') for r in section.get('rows', []))}")


def row_by_key(section: dict[str, Any], key: str) -> dict[str, Any]:
    for entry in section.get("rows", []):
        if entry.get("key") == key:
            return entry
    raise AssertionError(f"row {key!r} missing from {[r.get('key') for r in section.get('rows', [])]}")


def column_values(section: dict[str, Any], column: str) -> list[Any]:
    return [
        row.get("cells", {}).get(column, {}).get("value")
        for row in section.get("rows", [])
    ]


def group_titles(section: dict[str, Any]) -> list[str]:
    return [group.get("title") for group in section.get("groups", [])]


def link_kinds(payload: Any) -> set[str]:
    """Every link kind appearing anywhere in a payload."""
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            target = node.get("link")
            if isinstance(target, dict) and isinstance(target.get("kind"), str):
                found.add(target["kind"])
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(payload)
    return found


def link_ids(payload: Any, kind: str) -> list[str]:
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            target = node.get("link")
            if isinstance(target, dict) and target.get("kind") == kind:
                found.append(str(target.get("id")))
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(payload)
    return found


def field_value(item: dict[str, Any], label: str) -> Any:
    for field in item.get("fields", []):
        if field.get("label") == label:
            return field.get("value")
    raise AssertionError(f"field {label!r} missing from {[f.get('label') for f in item.get('fields', [])]}")
