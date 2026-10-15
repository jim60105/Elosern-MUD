"""Read-only server-authored dream panel, including offline escape."""

from web.webclient.presentation.artwork import validate_artwork
from web.webclient.presentation.protocol import ProtocolValidationError
from web.webclient.presentation.registry import PanelUnavailableError


# Panel wire schema version, mirrored in the registry registration, the client
# PANEL_ALLOWLIST, and the client available-form re-check (parity contract).
# v3 replaces the raw ``scene_art`` URL with the canonical scene descriptor the
# shared artwork validator (and the client's own mirror of it) accepts, so the
# dream stage resolves and renders its artwork exactly like every other scene
# surface. No old-shape field survives: a raw URL string fails the wire.
DREAM_SCHEMA_VERSION = 3


def dream_presenter(context):
    from server.dream_service import dream_state
    from world.narrative.dream_surface import scene_subject_id

    if context.actor is None:
        raise PanelUnavailableError()
    state = dream_state(context.actor)
    if state is not None:
        # The descriptor is validated and bound to THIS actor's own logical
        # dream subject: the dream stage's artwork belongs to the owner's
        # active sleep session, so a descriptor describing any other subject is
        # refused rather than presented as this player's stage.
        descriptor = validate_artwork(state["scene_art"])
        if descriptor["subject_id"] != scene_subject_id(context.actor):
            raise ProtocolValidationError("dream scene descriptor names another subject")
    return {"schema_version": DREAM_SCHEMA_VERSION, "available": True, "state": state}
