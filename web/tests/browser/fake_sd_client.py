"""Browser-harness image-generation client doubles (injected via ART_SD_CLIENT).

The harness is fully offline: the default ``ART_SD_CLIENT`` is the deterministic
``world.art.fake_sd_client.FakeSDWebUIClient``, which never opens a socket. The
offline journey additionally points ``ELOSERN_BROWSER_SD_CLIENT`` at
``FailingSDWebUIClient`` so ``@art run`` produces a real ``failed`` record at
runtime with a bounded error code, exactly like an unreachable image service.
"""

from __future__ import annotations

from world.art.sd_worker import GeneratedImage, SDError
from world.art.subjects import ArtSubject


class FailingSDWebUIClient:
    """Deterministic client that fails every generation like an unreachable server."""

    def generate(self, subject: ArtSubject, description: str) -> GeneratedImage:
        raise SDError(
            "sd_connection_error", "browser-harness simulated unreachable image service"
        )
