"""Transport client wrappers and the per-call client factory.

The offline stub for a disabled profile, the thin memo-discriminating
observation wrapper around the layer client, and the factory that resolves
the injected ``action_options`` client for one scheduling call. The
``world.ai`` imports stay function-local (this package stays cold
importable), and the factory itself is the test seam the trigger tests
patch on this module.
"""

from typing import Any


class _OfflineStubClient:
    """Non-``None`` client injected when the ``action_options`` profile is off.

    The layer's gate resolves the degrade before any transport work, so the
    stub is never called; its ``get_response`` fails loudly if it ever is,
    rather than silently half-opening a connection.
    """

    def get_response(self, descriptor):
        raise AssertionError(
            "offline stub client must never be called; the action_options "
            "profile degrades before any transport work"
        )


class _ObservingClient:
    """Thin wrapper that observes transport failures on the layer client.

    ``LLMTransportError`` — raised synchronously or errbacked on the returned
    Deferred — marks ``transport_failed``. This is the memo-discrimination
    signal: a degraded outcome with an observed transport failure is the
    memoized class; every other degrade (validation exhaustion, prompt
    unavailability, a disabled profile that never reaches the client) is not.
    The wrapper forwards the descriptor and every result untouched to the
    wrapped client, so the layer and its test doubles see no difference.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.transport_failed = False

    def get_response(self, descriptor: Any):
        from world.ai.errors import LLMTransportError

        try:
            result = self._inner.get_response(descriptor)
        except LLMTransportError:
            self.transport_failed = True
            raise
        if hasattr(result, "addErrback"):
            result = result.addErrback(self._observe)
        return result

    def _observe(self, failure: Any) -> Any:
        from world.ai.errors import LLMTransportError

        if failure.check(LLMTransportError):
            self.transport_failed = True
        return failure


def _build_action_options_client() -> Any:
    """Build the injected ``action_options`` client for one scheduling call."""
    from world.ai.client import OpenAICompatClient
    from world.ai.profiles import get_profile

    profile = get_profile("action_options")
    if profile.enabled:
        return OpenAICompatClient(profile)
    return _OfflineStubClient()
