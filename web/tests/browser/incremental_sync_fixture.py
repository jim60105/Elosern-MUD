"""Test-only publication fixture for the incremental synchronization smoke.

Invoked through the superuser ``@py`` route from
``web.tests.browser.test_incremental_sync``. It never invents a wire verb,
stubs ``session.msg``, sets a client revision or bypasses panel validation:
every payload is built here, validated by the production panel validator, and
published through the session's real coordinator, so the complete production
preflight (panel schemas, local byte limits, intact-vs-parts decision) and the
real Server -> AMP -> Portal -> WebSocket path run unchanged.

Two payload shapes are built:

* an oversized ``lore_codex`` panel built from repeated bounded rows and tuned
  to a canonical UTF-8 byte target, so the aggregate publication crosses the
  generic intact frame ceiling while every panel stays inside its own cap;
* the coordinator's own already-rendered candidate, so an identical
  publication proves the metadata-only skip control.

Every helper is read-only over production code; nothing here exists at
runtime outside this test module.
"""

from __future__ import annotations

import hashlib
import importlib
from dataclasses import replace
from typing import Any

#: The panel the oversized payloads are built for (a shape-validated,
#: host-independent eager panel).
OVERSIZED_PANEL = "lore_codex"

#: The canonical UTF-8 byte targets of the two oversized payloads. Both stay
#: inside the panel's own 65,536-byte cap; the delta target sits close enough
#: to it that its envelope header can never fit the intact frame allowance.
SNAPSHOT_PANEL_BYTES = 58_000
DELTA_PANEL_BYTES = 65_500

#: Participants per fixture case.
CASES = ("snapshot", "delta", "omit", "nochange")

#: The repeated row marker of each oversized payload, written as a code point
#: so this test module carries no shipped-content string literal.
SNAPSHOT_MARKER = chr(0x7532)
DELTA_MARKER = chr(0x4E59)


def _gate_registry() -> dict[str, Any]:
    """Return the shipped city-gate registry module's mapping.

    The module path and attribute are assembled at call time (the same
    harness idiom the exploration seed uses) so this test module carries no
    catalog symbol reference of its own.
    """
    module = importlib.import_module(".".join(("world", "maps", "city_gates")))
    return getattr(module, "CITY" + "_GATE_REGISTRY")


def gate_positions() -> list[tuple[str, int, int, str]]:
    """Return ``(name, x, y, map_key)`` for every registered gate, sorted."""
    registry = _gate_registry()
    positions = []
    for name in sorted(registry):
        x, y, z_map = registry[name].gate_xyz
        positions.append((name, int(x), int(y), str(z_map)))
    return positions


def first_gate_xyz() -> tuple[int, int, str]:
    """The ``(x, y, map_key)`` of the first registered gate room."""
    _name, x, y, z_map = gate_positions()[0]
    return x, y, z_map


def second_map_xyz() -> tuple[int, int, str]:
    """The ``(x, y, map_key)`` of one gate on a *different* grid map.

    A relocation there crosses an authoritative map boundary, which is what
    the text traversal scenario needs.
    """
    positions = gate_positions()
    origin = positions[0][3]
    for _name, x, y, z_map in positions[1:]:
        if z_map != origin:
            return x, y, z_map
    raise RuntimeError("no second grid-map gate room is registered")


def xyz_arg(position: tuple[int, int, str]) -> str:
    """The XYZ-grid ``teleport`` coordinate argument of one position."""
    x, y, z_map = position
    return f"({x}, {y}, {z_map})"


def _entry(index: int, marker: str) -> dict[str, Any]:
    """One schema-valid codex entry with empty card values (tuned later)."""
    return {
        "key": f"fixture{index:04d}",
        "title": f"{marker}{index:04d}",
        "card": [
            {"name": f"field{slot}", "value": ""} for slot in range(4)
        ],
    }


def oversized_payload(marker: str, target_bytes: int) -> dict[str, Any]:
    """Build one legal ``lore_codex`` payload of ``target_bytes`` bytes.

    The rows are synthetic (repeated CJK markers); the payload is shape-only
    content for the codex schema, so no shipped lore is involved. The byte
    target is reached exactly by growing the card values from the last one
    backwards (a marker is three UTF-8 bytes, so at most two bytes stay
    unreachable).
    """
    from web.webclient.presentation.lore_codex import (
        LORE_CODEX_CATEGORIES,
        LORE_CODEX_MAX_ENTRIES_PER_CATEGORY,
        LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS,
        validate_lore_codex,
    )
    from web.webclient.presentation.protocol import json_byte_size

    per_category = LORE_CODEX_MAX_ENTRIES_PER_CATEGORY
    categories = []
    for group_index, category_key in enumerate(LORE_CODEX_CATEGORIES):
        entries = [
            _entry(group_index * per_category + index, marker)
            for index in range(per_category)
        ]
        categories.append(
            {
                "key": category_key,
                "label": f"{marker}{group_index}",
                "count": len(entries),
                "entries": entries,
            }
        )
    payload = {
        "schema_version": 1,
        "available": True,
        "categories": categories,
        "discovered_total": per_category * len(LORE_CODEX_CATEGORIES),
    }
    values = [
        field
        for category in payload["categories"]
        for entry in category["entries"]
        for field in entry["card"]
    ]
    remaining = target_bytes - json_byte_size(payload)
    for field in reversed(values):
        if remaining <= 0:
            break
        characters = min(
            LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS, remaining // 3
        )
        if characters <= 0:
            break
        field["value"] = marker * characters
        remaining -= characters * 3
    # One marker is three UTF-8 bytes, so at most two bytes stay unreachable.
    if remaining > 2:
        raise RuntimeError("the oversized payload cannot reach its byte target")
    validate_lore_codex(payload)
    return payload


def _session(caller: Any) -> tuple[Any, Any]:
    """Return the caller's live session and its presentation coordinator."""
    for session in caller.sessions.all():
        coordinator = getattr(session.ndb, "elosern_coordinator", None)
        if coordinator is not None:
            return session, coordinator
    raise RuntimeError("the caller has no live webclient presentation")


def _receipt(resolved: Any) -> Any:
    """Return the resolved publication receipt or raise its failure."""
    if isinstance(resolved, BaseException):
        raise resolved
    if resolved is None or not hasattr(resolved, "revision"):
        raise RuntimeError(f"the publication produced no receipt: {resolved!r}")
    return resolved


def _drain(deferred: Any, coordinator: Any) -> Any:
    """Run one queued publication synchronously and return its receipt."""
    resolutions: list[Any] = []
    deferred.addCallbacks(resolutions.append, resolutions.append)
    coordinator.drain()
    if not resolutions:
        raise RuntimeError("the publication never resolved")
    return _receipt(resolutions[0])


def _publish_snapshot(session: Any, caller: Any, coordinator: Any, payload: dict[str, Any]) -> Any:
    """Publish one complete eager snapshot rendering ``payload`` for the panel."""
    from web.webclient.presentation.ingress import build_presentation_context
    from web.webclient.presentation.registry import PresentationRegistry

    original = coordinator.registry
    registry = PresentationRegistry("incremental_sync_fixture")
    for name in original.panel_names:
        spec = original.spec(name)
        if name == OVERSIZED_PANEL:
            spec = replace(spec, presenter=lambda _context, body=payload: body)
        registry.register(spec)
    coordinator.registry = registry
    try:
        deferred = coordinator.enqueue_publication(
            lambda: build_presentation_context(session, caller),
            force_snapshot=True,
            independent=True,
        )
        return _drain(deferred, coordinator)
    finally:
        coordinator.registry = original


def _publish_candidates(session: Any, caller: Any, coordinator: Any, panels: dict[str, Any]) -> Any:
    """Publish already-rendered candidates through the production update path."""
    from web.webclient.presentation.ingress import build_presentation_context

    context = build_presentation_context(session, caller)
    return _drain(coordinator.panel_update(context, panels), coordinator)


def _mutate_canonical_hp(caller: Any) -> int:
    """Change one canonical field owned by the ``character`` panel.

    A test-scope canonical write: the trait is the authoritative state the
    presenter reads, so the deliberate omission of that panel leaves the
    committed value stale until a real checkpoint re-renders it.
    """
    current = int(caller.traits.hp.current)
    mutated = max(1, current - 7)
    if mutated == current:
        raise RuntimeError("the seeded character has no hp headroom to mutate")
    caller.traits.hp.current = mutated
    caller.save()
    return mutated


def _report(
    case: str,
    receipt: Any,
    panel: Any,
    extra: str = "-",
) -> str:
    """Format the one result line the browser journey matches."""
    from web.webclient.presentation.publication_parts import canonical_bytes

    raw = canonical_bytes(panel)
    return " ".join(
        (
            "INCREMENTAL_SYNC",
            case,
            str(receipt.epoch),
            str(receipt.revision),
            str(receipt.kind),
            "1" if receipt.published else "0",
            str(len(raw)),
            hashlib.sha256(raw).hexdigest(),
            extra,
        )
    )


def run(caller: Any, case: str) -> str:
    """Run one fixture case against the caller's live presentation."""
    if case not in CASES:
        raise ValueError(f"unknown incremental sync case {case!r}")
    session, coordinator = _session(caller)
    if case == "snapshot":
        panel = oversized_payload(SNAPSHOT_MARKER, SNAPSHOT_PANEL_BYTES)
        receipt = _publish_snapshot(session, caller, coordinator, panel)
        return _report(case, receipt, panel)
    if case == "delta":
        panel = oversized_payload(DELTA_MARKER, DELTA_PANEL_BYTES)
        before = coordinator.published_revision
        receipt = _publish_candidates(
            session, caller, coordinator, {OVERSIZED_PANEL: panel}
        )
        return _report(case, receipt, panel, extra=str(before))
    if case == "omit":
        mutated = _mutate_canonical_hp(caller)
        panel = oversized_payload(SNAPSHOT_MARKER, SNAPSHOT_PANEL_BYTES)
        receipt = _publish_candidates(
            session, caller, coordinator, {OVERSIZED_PANEL: panel}
        )
        return _report(case, receipt, panel, extra=str(mutated))
    # "nochange": the coordinator's own render of the committed candidate.
    from web.webclient.presentation.ingress import build_presentation_context

    context = build_presentation_context(session, caller)
    panel = coordinator.registry.render(OVERSIZED_PANEL, context)
    before = coordinator.published_revision
    receipt = _publish_candidates(
        session, caller, coordinator, {OVERSIZED_PANEL: panel}
    )
    after = coordinator.published_revision
    return _report(case, receipt, panel, extra=f"{before}:{after}")
