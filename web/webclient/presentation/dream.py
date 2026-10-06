"""Read-only server-authored dream panel, including offline escape."""

from web.webclient.presentation.registry import PanelUnavailableError


# Panel wire schema version, mirrored in the registry registration, the client
# PANEL_ALLOWLIST, and the client available-form re-check (parity contract).
# v2 adds the server-resolved ``scene_art`` official-media URL to the state.
DREAM_SCHEMA_VERSION = 2


def dream_presenter(context):
    from server.dream_service import dream_state
    if context.actor is None:
        raise PanelUnavailableError()
    state = dream_state(context.actor)
    return {"schema_version": DREAM_SCHEMA_VERSION, "available": True, "state": state}
