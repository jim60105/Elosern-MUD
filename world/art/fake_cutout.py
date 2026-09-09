"""Deterministic background-removal test double; never loads a model.

``FakeCutoutBackend`` mirrors the ``RembgCutoutBackend`` interface
(``remove_background(png_bytes) -> bytes``) and is injected through the
``ART_REMBG_BACKEND`` dotted-path setting by tests and the browser harness.
It records every call, replays scripted ``CutoutError`` failures, and
otherwise returns a REAL PNG whose alpha channel has been zeroed over a fixed
top-left region — never a passthrough of its input, so an alpha assertion
against its output is a real assertion. Imports neither ``rembg`` nor
``onnxruntime``, reads no model file, and opens no socket.
"""

from __future__ import annotations

import io
from collections.abc import Callable

from PIL import Image

from world.art.cutout import CutoutError

# The fixed region whose alpha the fake zeroes (design D7: a partial, spatial
# proof — an alpha assertion that only holds because EVERY pixel went
# transparent proves nothing). Worker-test fixtures must be larger than this
# region and assert a known opaque pixel outside it.
_FAKE_ZEROED_REGION = (8, 8)


def _zeroed_alpha_png(png_bytes: bytes) -> bytes:
    """Return the input PNG re-encoded with a zeroed top-left alpha region."""
    with Image.open(io.BytesIO(png_bytes)) as opened:
        opened.load()
        image = opened.convert("RGBA")
    width, height = image.size
    zero_w = min(_FAKE_ZEROED_REGION[0], width)
    zero_h = min(_FAKE_ZEROED_REGION[1], height)
    alpha = image.getchannel("A")
    for y in range(zero_h):
        for x in range(zero_w):
            alpha.putpixel((x, y), 0)
    image.putalpha(alpha)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class FakeCutoutBackend:
    """Replay double with the same interface as the real backend."""

    def __init__(self) -> None:
        self.calls: list[bytes] = []
        self._failures: list[
            tuple[Callable[[bytes], bool] | None, CutoutError]
        ] = []

    def fail_every_call(self, error: CutoutError) -> None:
        """Script every subsequent ``remove_background`` to raise ``error``."""
        self._failures.append((None, error))

    def add_failure(
        self, matcher: Callable[[bytes], bool], error: CutoutError
    ) -> None:
        """Raise ``error`` for calls matching ``matcher(png_bytes)``."""
        self._failures.append((matcher, error))

    def remove_background(self, png_bytes: bytes) -> bytes:
        """Record the call and replay the first matching scripted failure."""
        self.calls.append(png_bytes)
        for matcher, error in self._failures:
            if matcher is None or matcher(png_bytes):
                raise error
        return _zeroed_alpha_png(png_bytes)
