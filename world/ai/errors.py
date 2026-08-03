"""Named errors shared by the generative transport and the guardrail.

``LLMTransportError`` is the one failure signature every client-level failure
(connection, HTTP status, malformed body, timeout) resolves to, so the guardrail
and the deterministic replay double can treat identical failures identically.
"""


class LLMTransportError(Exception):
    """A client-level transport failure: connection, HTTP, malformed, or timeout."""

    def __init__(self, kind: str, message: str):
        self.kind = kind
        super().__init__(message)
