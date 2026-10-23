"""Publish actual production-assembled geometry through the managed socket.

Each invocation uses a session-local registry copy with one measurement
presenter. The body uses the same assembly, privacy filter and trail encoder
as world_map_presenter; only its synthetic exploration history is supplied
by tools.world_map_payload. No runtime presenter or global registry changes.
"""
from __future__ import annotations

import hashlib
from typing import Any


def publish(caller: Any, case: str) -> str:
    """Return WORLD_MAP <case> <revision> <bytes> <sha256> after publication."""
    from tools import world_map_payload
    from web.webclient.presentation.ingress import build_presentation_context
    from web.webclient.presentation.map_panels import WORLD_MAP_PANEL,WORLD_MAP_SCHEMA_VERSION
    from web.webclient.presentation.map_parts import canonical_bytes
    from web.webclient.presentation.registry import PresenterSpec,PresentationRegistry

    if case not in ("representative","worst"):
        raise ValueError(f"unknown world map case {case!r}")
    session=next((s for s in caller.sessions.all() if getattr(s.ndb,"elosern_coordinator",None) is not None),None)
    if session is None:
        raise RuntimeError("the caller has no live webclient presentation")
    body=(world_map_payload.worst_payload() if case == "worst" else world_map_payload.representative_payload())
    coordinator=session.ndb.elosern_coordinator
    original=coordinator.registry
    registry=PresentationRegistry("world_map_transport_fixture")
    for name in original.panel_names:
        if name != WORLD_MAP_PANEL:
            registry.register(original.spec(name))
    registry.register(PresenterSpec(name=WORLD_MAP_PANEL,schema_version=WORLD_MAP_SCHEMA_VERSION,
        unavailable_reason=("map_unavailable","世界地圖目前無法顯示"),presenter=lambda context:body,on_demand=True))
    coordinator.registry=registry
    try:
        revision=coordinator._publish_presentation(build_presentation_context(session,caller),{WORLD_MAP_PANEL})
    finally:
        coordinator.registry=original
    raw=canonical_bytes(body)
    return f"WORLD_MAP {case} {revision} {len(raw)} {hashlib.sha256(raw).hexdigest()}"
