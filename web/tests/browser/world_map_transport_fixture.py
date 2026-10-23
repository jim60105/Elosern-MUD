"""Server-side fixture for the world-map transport browser test.

transport-world-map-panel proves that a measured continental ``world_map``
travels the real Evennia server -> AMP -> portal -> WebSocket path and is
adopted by the production browser store. No world presenter exists yet
(``publish-world-map-panel`` owns it) and ``map.view`` stays area-only, so
the browser test calls :func:`publish` through the superuser ``@py``
command. It registers a test-only on-demand ``world_map`` presenter on that
session's own coordinator registry (``attach_coordinator`` builds one
registry per session, so nothing leaks to other sessions), and publishes
through ``_publish_presentation`` exactly as the action dispatcher does after
a ``map.view`` request. The body is the real-geography payload from
``tools.world_map_payload``.

Not a test module (no ``test_`` prefix); it runs only inside the managed
browser server process.
"""

from __future__ import annotations

import hashlib
from typing import Any

_CASES = ("representative", "worst")
_active_case = {"name": "representative"}


def _presenter(context: Any) -> dict[str, Any]:
    from tools import world_map_payload

    if _active_case["name"] == "worst":
        return world_map_payload.worst_payload()
    return world_map_payload.representative_payload()


def publish(caller: Any, case: str) -> str:
    """Publish one measured world map to ``caller``'s live webclient session.

    Returns ``WORLD_MAP <case> <revision> <bytes> <sha256>`` for the
    browser test: the revision of the published frame and the length and
    digest of the canonical UTF-8 bytes of the validated body.
    """
    from web.webclient.presentation.ingress import build_presentation_context
    from web.webclient.presentation.map_panels import (
        WORLD_MAP_PANEL,
        WORLD_MAP_SCHEMA_VERSION,
        validate_world_map,
    )
    from web.webclient.presentation.map_parts import canonical_bytes
    from web.webclient.presentation.registry import PresenterSpec

    if case not in _CASES:
        raise ValueError(f"unknown world map case {case!r}")
    session = next(
        (s for s in caller.sessions.all() if getattr(s.ndb, "elosern_coordinator", None) is not None),
        None,
    )
    if session is None:
        raise RuntimeError("the caller has no live webclient presentation")
    coordinator = session.ndb.elosern_coordinator
    if WORLD_MAP_PANEL not in coordinator.registry.panel_names:
        coordinator.registry.register(
            PresenterSpec(
                name=WORLD_MAP_PANEL,
                schema_version=WORLD_MAP_SCHEMA_VERSION,
                unavailable_reason=("map_unavailable", "世界地圖目前無法顯示"),
                presenter=_presenter,
                on_demand=True,
            )
        )
    _active_case["name"] = case
    raw = canonical_bytes(validate_world_map(_presenter(None)))
    context = build_presentation_context(session, caller)
    revision = coordinator._publish_presentation(context, {WORLD_MAP_PANEL})
    return f"WORLD_MAP {case} {revision} {len(raw)} {hashlib.sha256(raw).hexdigest()}"
