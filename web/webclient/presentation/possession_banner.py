"""Exact schema-version-1 ``possession_banner`` panel and presenter."""

from typing import Any

from web.webclient.presentation.affordances import MAX_DISPLAY_NAME_CODE_POINTS
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError

POSSESSION_BANNER_SCHEMA_VERSION = 1

MAX_HOST_NAME_CODE_POINTS = MAX_DISPLAY_NAME_CODE_POINTS


class PossessionBannerError(ProtocolValidationError):
    """The available possession banner payload violates its exact bounded schema."""


def validate_possession_banner(payload: Any) -> dict[str, Any]:
    """Validate one exact available version-1 ``possession_banner`` payload."""
    if not isinstance(payload, dict):
        raise PossessionBannerError("possession banner payload must be an object")
    _require_exact_fields(
        payload,
        "possession_banner",
        {"schema_version", "available", "host_name", "since_tick"},
        {},
    )
    version = _require_int(payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER)
    if version != POSSESSION_BANNER_SCHEMA_VERSION:
        raise PossessionBannerError(
            f"schema_version must be {POSSESSION_BANNER_SCHEMA_VERSION}, got {version}"
        )
    available = _require_bool(payload, "available")
    if not available:
        raise PossessionBannerError("available must be True for available panel validator")
    host_name = _require_str(payload, "host_name", maximum=MAX_HOST_NAME_CODE_POINTS)
    if not host_name.strip():
        raise PossessionBannerError("host_name must not be empty")
    since_tick = _require_int(payload, "since_tick", minimum=0, maximum=MAX_SAFE_INTEGER)
    if json_byte_size(payload) > MAX_CANONICAL_JSON_BYTES:
        raise PossessionBannerError("possession banner exceeds protocol byte limit")
    return {
        "schema_version": POSSESSION_BANNER_SCHEMA_VERSION,
        "available": True,
        "host_name": host_name,
        "since_tick": since_tick,
    }


def possession_banner_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``possession_banner`` payload for a possessed actor."""
    actor = context.actor
    possessed_by = getattr(getattr(actor, "db", None), "possessed_by", None)
    if possessed_by is None:
        raise PanelUnavailableError

    from world.rules.possession import _resolve_live_object, current_possession

    player = _resolve_live_object(int(possessed_by))
    if player is None:
        raise PanelUnavailableError

    pos = current_possession(player)
    if pos is None or pos.get("npc_dbid") != getattr(actor, "pk", None):
        raise PanelUnavailableError

    host_name = str(getattr(actor, "key", "") or "同伴")[:MAX_HOST_NAME_CODE_POINTS]
    since_tick = int(pos.get("since_tick", 0))

    payload = {
        "schema_version": POSSESSION_BANNER_SCHEMA_VERSION,
        "available": True,
        "host_name": host_name,
        "since_tick": since_tick,
    }
    return validate_possession_banner(payload)


__all__ = [
    "MAX_HOST_NAME_CODE_POINTS",
    "POSSESSION_BANNER_SCHEMA_VERSION",
    "PossessionBannerError",
    "possession_banner_presenter",
    "validate_possession_banner",
]
