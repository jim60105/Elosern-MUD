"""Read-only server-authored dream panel, including offline escape."""

from web.webclient.presentation.registry import PanelUnavailableError


def dream_presenter(context):
    from server.dream_service import dream_state
    if context.actor is None:
        raise PanelUnavailableError()
    state = dream_state(context.actor)
    return {"schema_version": 1, "available": True, "state": state}
