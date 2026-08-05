"""Free-form dialogue composition root (webclient-exploration-menu D6).

``build_dialogue_client`` is the single injection site for the ``npc_dialogue``
profile client used by the ``explore.talk_freeform`` adapter. It mirrors the
``server/ai_director_service.py`` pattern: the client is built **function-locally
and only when the profile is enabled**, so a cold import of this module (or of
the adapter importing it) cannot bind the guardrail's import-time logger or load
the live transport when the layer is disabled. When the profile is disabled a
non-``None`` offline stub is returned whose ``get_response`` fails loudly if it
ever is called -- the guardrail degrades before any transport work, so it never
is. Transport ownership stays in ``world/ai/client.py``; this module never
imports or constructs a transport at module scope.
"""

from typing import Any


class _OfflineStubClient:
    """A non-``None`` client injected when the ``npc_dialogue`` profile is
    disabled.

    The degrade path reaches the authored greeting/silence before any transport
    work, so this stub is never called; its ``get_response`` fails loudly if it
    ever is, rather than silently half-opening a connection.
    """

    def get_response(self, descriptor: Any):
        raise AssertionError(
            "offline stub client must never be called; the npc_dialogue layer "
            "degrades before any transport work"
        )


def build_dialogue_client() -> Any:
    """Return the injected ``npc_dialogue`` client for the free-form seam.

    Builds an ``OpenAICompatClient`` only when the ``npc_dialogue`` profile is
    enabled; otherwise returns the non-``None`` offline stub. All ``world.ai``
    imports are deferred into the enabled branch so importing this module (or
    calling it with the layer disabled) cannot bind the guardrail's import-time
    logger or load the live transport.
    """
    from world.ai.profiles import get_profile

    profile = get_profile("npc_dialogue")
    if profile.enabled:
        from world.ai.client import OpenAICompatClient

        return OpenAICompatClient(profile)
    return _OfflineStubClient()


__all__ = ["build_dialogue_client"]
