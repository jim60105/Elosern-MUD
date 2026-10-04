"""Read-only server-authored dream panel, including offline escape."""

from web.webclient.presentation.registry import PanelUnavailableError


# Panel wire schema version, mirrored in the registry registration, the client
# PANEL_ALLOWLIST, and the client available-form re-check (parity contract).
DREAM_SCHEMA_VERSION = 1


def dream_presenter(context):
    from server.dream_service import dream_state
    if context.actor is None:
        raise PanelUnavailableError()
    state = dream_state(context.actor)
    return {"schema_version": DREAM_SCHEMA_VERSION, "available": True, "state": state}
