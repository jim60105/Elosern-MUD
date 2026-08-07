"""Deterministic sd-webui client test double; never opens a socket.

``FakeSDWebUIClient`` mirrors the ``SDWebUIClient`` interface
(``generate(subject, description) -> bytes``) and is injected through the
``ART_SD_CLIENT`` dotted-path setting by tests and the browser harness. It
replays a fixed valid PNG by default, can be scripted to raise any named
``SDError``, and records every request it received so callers can assert what
was (or was not) generated. No network access is ever attempted.
"""

from __future__ import annotations

import base64
from collections.abc import Callable

from world.art.sd_worker import SDError
from world.art.subjects import ArtSubject

# A deterministic 1x1 transparent PNG so the fake's default output is a real,
# servable image rather than a mislabelled text file.
DEFAULT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class FakeSDWebUIClient:
    """Replay double with the same ``generate`` interface as the real client."""

    def __init__(self):
        self.calls: list[tuple[ArtSubject, str]] = []
        self._failures: list[tuple[Callable[[ArtSubject, str], bool] | None, SDError]] = []

    def fail_every_call(self, error: SDError) -> None:
        """Script every subsequent ``generate`` to raise ``error``."""
        self._failures.append((None, error))

    def add_failure(self, matcher: Callable[[ArtSubject, str], bool], error: SDError) -> None:
        """Raise ``error`` for requests matching ``matcher(subject, description)``."""
        self._failures.append((matcher, error))

    def generate(self, subject: ArtSubject, description: str) -> bytes:
        """Record the request and replay the first matching scripted failure."""
        self.calls.append((subject, description))
        for matcher, error in self._failures:
            if matcher is None or matcher(subject, description):
                raise error
        return DEFAULT_PNG
