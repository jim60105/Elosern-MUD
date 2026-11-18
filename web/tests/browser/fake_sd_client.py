"""Browser-harness image-generation client doubles (injected via ART_SD_CLIENT).

The harness is fully offline: the default ``ART_SD_CLIENT`` is the deterministic
``world.art.fake_sd_client.FakeSDWebUIClient``, which never opens a socket. The
offline journey additionally points ``ELOSERN_BROWSER_SD_CLIENT`` at
``FailingSDWebUIClient`` so ``@art run`` produces a real ``failed`` record at
runtime with a bounded error code, exactly like an unreachable image service.
The creation portrait journeys point it at ``ControlledSDWebUIClient``, whose
probe and generation outcomes follow the runtime's ``sd_control`` mode file.
"""

from __future__ import annotations

import time

from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.sd_worker import GeneratedImage, SDError
from world.art.subjects import ArtSubject

from .sd_control import read_mode

# The longest a held generation waits for its release on the worker thread.
# Reaching it fails the generation loudly instead of passing as a success.
_HOLD_LIMIT_SECONDS = 300.0


class FailingSDWebUIClient:
    """Deterministic client that fails every generation like an unreachable server."""

    def generate(self, subject: ArtSubject, description: str) -> GeneratedImage:
        raise SDError(
            "sd_connection_error", "browser-harness simulated unreachable image service"
        )

    def probe_samplers(self, *, timeout_seconds: float) -> None:
        raise SDError(
            "sd_connection_error", "browser-harness simulated unreachable image service"
        )


class ControlledSDWebUIClient:
    """Deterministic client whose outcomes follow the ``sd_control`` mode file.

    ``probe``: ``ok`` answers, ``fail`` raises like an unreachable server.
    ``generate``: ``ok`` replays the deterministic fake image, ``fail`` raises,
    ``hold`` keeps the claimed job on the worker's background thread until the
    mode leaves ``hold`` (a test releases it after acting on the in-flight
    job). The mode is re-read on every call.
    """

    def probe_samplers(self, *, timeout_seconds: float) -> None:
        if read_mode("probe", "ok") == "fail":
            raise SDError(
                "sd_connection_error", "browser-harness simulated unreachable image service"
            )

    def generate(self, subject: ArtSubject, description: str) -> GeneratedImage:
        deadline = time.monotonic() + _HOLD_LIMIT_SECONDS
        while read_mode("generate", "ok") == "hold":
            if time.monotonic() >= deadline:
                raise SDError("sd_timeout", "browser-harness held generation was never released")
            time.sleep(0.05)
        if read_mode("generate", "ok") == "fail":
            raise SDError(
                "sd_connection_error", "browser-harness simulated unreachable image service"
            )
        return FakeSDWebUIClient().generate(subject, description)
