"""Composition root bridging the scene-flavor layer to instance-scene materialization.

``schedule_scene_flavor`` is the single production caller of
``world.ai.scene_flavor.generate_scene_flavor``. It lives in ``server/`` because
that directory is the one place where both import directions are legal under the
repository contract tests: the deterministic-path ban scans
``world/rules|maps|quests|art|commands`` and the transport boundary scans
``world/ai/``, and ``server/`` is scanned by neither — the same shape as
``ai_director_service.py`` for the scenario-director.

Every ``world.ai`` import is deferred into the call path so importing this module
at server startup cannot bind the guardrail's import-time ``None`` logger. The
call is fire-and-forget: ``CmdEnterScene`` registers it through
``transaction.on_commit`` (a nested outer rollback never fires a generation), the
scheduling never blocks arrival or raises to the caller — every synchronous step
(dict validation, client construction, context wrapping, obtaining the Deferred)
is wrapped and logged — and a failure (offline profile, transport, validation
exhaustion, vanished room) resolves to "no flavor" with no gameplay impact. On
success the deterministic core writes the flavor and the completion path pushes
it to the ``PlayerCharacter``s present in the room.
"""

from twisted.internet import defer
from typing import Any

from world.observability import log_warn


_SCENE_FLAVOR_KEYS = frozenset(("scene_sentence", "quest_context", "room_name", "region"))


class SceneFlavorContextError(ValueError):
    """Raised when the flavor context dict is not the exact four-string-key shape."""


class _OfflineStubClient:
    """A non-``None`` client injected when the ``scene_builder`` profile is disabled.

    The guardrail's degrade path resolves before any transport work when the
    profile is disabled, so this stub is never called; its ``get_response``
    fails loudly if it ever is, rather than silently half-opening a connection
    (mirrors ``ai_director_service._OfflineStubClient``).
    """

    def get_response(self, descriptor):
        raise AssertionError(
            "offline stub client must never be called; the scene_builder "
            "profile degrades before any transport work"
        )


def _build_scene_flavor_client() -> Any:
    """Build the injected ``scene_builder`` client for one scheduling call.

    Function-local, so a cold import of this module binds no guardrail logger
    and loads no transport: enabled profile → ``OpenAICompatClient``; disabled
    profile → the non-``None`` offline stub so the layer's required-client gate
    is satisfied while the degrade path never touches the client.
    """
    from world.ai.client import OpenAICompatClient
    from world.ai.profiles import get_profile

    profile = get_profile("scene_builder")
    if profile.enabled:
        return OpenAICompatClient(profile)
    return _OfflineStubClient()


def _validate_flavor_context(flavor_context: Any) -> dict[str, str]:
    """Validate the plain context dict at the adapter boundary.

    Exactly the four layer keys, every value a string — the shape the layer's
    frozen ``SceneFlavorContext`` requires. A malformed dict raises
    ``SceneFlavorContextError`` (the scheduling wrapper turns it into a bounded
    logged no-op).
    """
    if not isinstance(flavor_context, dict):
        raise SceneFlavorContextError(
            f"flavor context must be a dict, got {type(flavor_context).__name__}"
        )
    if set(flavor_context) != _SCENE_FLAVOR_KEYS:
        raise SceneFlavorContextError(
            f"flavor context must have exactly the keys "
            f"{sorted(_SCENE_FLAVOR_KEYS)}, got {sorted(flavor_context)}"
        )
    if not all(isinstance(value, str) for value in flavor_context.values()):
        raise SceneFlavorContextError(
            "every flavor context value must be a string"
        )
    return {key: flavor_context[key] for key in _SCENE_FLAVOR_KEYS}


def _push_flavor_to_present(room: Any, text: str) -> None:
    """Message every ``PlayerCharacter`` currently located in ``room``.

    Plain text push; players who left are not chased (a later ``look`` renders
    the flavor through the shared appearance layer).
    """
    from typeclasses.characters import PlayerCharacter

    for occupant in room.contents:
        if isinstance(occupant, PlayerCharacter):
            occupant.msg(text)


@defer.inlineCallbacks
def _run_scene_flavor(room: Any, flavor_context: dict[str, str], client: Any):
    """Run one guarded flavor generation and apply + push on success.

    Degrades (the layer resolves ``None``) and synchronous failures resolve to
    "no flavor"; the deterministic write and the present-player push happen
    only for an accepted flavor paragraph.
    """
    from world.ai.scene_flavor import SceneFlavorContext, generate_scene_flavor
    from world.quests.scene_builder import apply_scene_flavor

    context = SceneFlavorContext(**flavor_context)
    text = yield generate_scene_flavor(context, client)
    if text is None:
        return
    if apply_scene_flavor(room, text):
        _push_flavor_to_present(room, text)


def schedule_scene_flavor(room: Any, flavor_context: Any, *, client: Any = None) -> defer.Deferred | None:
    """Validate and fire one fire-and-forget scene-flavor generation.

    Args:
        room: The freshly spawned scene room to flavor on success.
        flavor_context: The deterministic four-string-key context dict produced
            by ``world.quests.scene_builder.build_flavor_context``.
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``), or ``None`` to build one from the
            ``scene_builder`` profile inside this call.

    The scheduling never raises to the caller: dict validation, client
    construction, context wrapping, and obtaining the Deferred are all wrapped,
    and any synchronous failure is logged as a bounded diagnostic and resolves
    to nothing (``None`` is returned). Otherwise the fire-and-forget Deferred
    is returned for the caller's (optional) inspection: its success path
    applies the flavor through the deterministic core and pushes it to present
    players; its failure path logs and resolves to nothing.
    """
    try:
        validated = _validate_flavor_context(flavor_context)
        if client is None:
            client = _build_scene_flavor_client()
        d = _run_scene_flavor(room, validated, client)
    except Exception as error:  # noqa: BLE001 - bounded, never propagates (design D5)
        log_warn(
            "scene_flavor_schedule_failed",
            exc=error,
            context={"room": getattr(room, "pk", 0) or 0},
        )
        return None

    def _log_failure(failure) -> None:
        log_warn(
            "scene_flavor_generation_failed",
            exc=failure.value,
            context={"room": room.pk, "reason": failure.getErrorMessage()},
        )

    d.addErrback(_log_failure)
    return d
