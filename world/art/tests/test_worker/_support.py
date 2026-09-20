"""File-local fakes and the store-isolation base for the ``test_worker`` slices.

Module-level fixtures moved verbatim from the original flat module (not a
collected test module).
"""
from contextlib import contextmanager
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from django.test import override_settings

from PIL import Image
from evennia.utils.test_resources import EvenniaTest

from world.art.fake_sd_client import DEFAULT_PNG, FakeSDWebUIClient
from world.art.fake_cutout import FakeCutoutBackend
from world.art.cutout import CutoutError
from world.art import gallery as gallery_api
from world.art.gallery import DEFAULT_FACE_RECT
from world.art.queue import (
    claim,
    ensure,
    enqueue_gallery_job,
    gallery_record_key,
    record_key,
    reclaim_expired_leases,
    requeue,
    settle,
    settle_generated,
)
from world.art.sd_worker import GeneratedImage, SDError
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import (
    _lease_timeout,
    _run_and_settle_batch,
    _write_temp,
    drain,
    drain_synchronous,
    expected_output_identity,
    output_identity_for,
)

from tools.spec_traceability import covers_requirement

class _MixedOutcomeClient:
    """A deterministic client whose outcome is scripted per description.

    ``None`` means a valid generation; any other value is raised verbatim, so
    tests can script named ``SDError``s and unexpected internal errors in one
    batch. Records every call like the fake client. A valid generation returns
    the default PNG with a scripted seed (default ``None``).
    """

    def __init__(self):
        self.calls: list[tuple[ArtSubject, str]] = []
        self.outcomes: dict[str, Exception | None] = {}
        self.seed: int | None = None

    def generate(self, subject: ArtSubject, description: str) -> GeneratedImage:
        self.calls.append((subject, description))
        error = self.outcomes.get(description)
        if error is not None:
            raise error
        return GeneratedImage(data=DEFAULT_PNG, seed=self.seed)


def _opaque_portrait_png(size=(16, 12)) -> bytes:
    """An OPAQUE multi-pixel PNG, LARGER than the fake's zeroed 8x8 region.

    ``fake_sd_client.DEFAULT_PNG`` is a 1x1 already-transparent image, so an
    alpha assertion driven by it passes with the stage disabled and proves
    nothing; a fixture no bigger than the zeroed region would make every pixel
    transparent. This fixture has a known opaque pixel at (10, 10) and a known
    RGB pattern per pixel, so a cutout run's stored bytes can never equal a
    disabled run's.
    """
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = (17 + x * 13, 29 + y * 7, (x * y * 5 + 3) % 256)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class WorkerStoreIsolation(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(self.root),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        super().tearDown()

    @contextmanager
    def _client(self, client):
        """Run a drain block with ``client`` injected through the seam."""
        with patch("world.art.worker.resolve_sd_client", return_value=client):
            yield

    def _subject(self, key="t_synth_forest", kind=ArtSubjectKind.SCENE):
        return ArtSubject(kind, key)

    def _record(self, subject, description="desc"):
        return ensure(subject, description)

    def _record_for(self, subject):
        return ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()

    def _assert_region_transparent(self, path: Path) -> None:
        """The fake zeroes the top-left 8x8; the standard fixture is 16x12."""
        with Image.open(path.open("rb")) as image:
            self.assertEqual(image.mode, "RGBA")
            pixels = image.load()
            self.assertEqual(pixels[0, 0][3], 0)
            self.assertEqual(pixels[7, 7][3], 0)
            self.assertEqual(pixels[10, 10][3], 255)
            self.assertEqual(pixels[15, 11][3], 255)

class _OpaqueClient:
    """Deterministic client replaying the OPAQUE multi-pixel portrait fixture.

    ``FakeSDWebUIClient``'s default PNG is a 1x1 ALREADY-TRANSPARENT image, so
    every cutout assertion in this module drives this client instead: an alpha
    assertion against the transparent default would pass with the stage
    disabled and prove nothing (design D7).
    """

    def __init__(self):
        self.calls: list[tuple[ArtSubject, str]] = []
        self.seed = 77

    def generate(self, subject: ArtSubject, description: str) -> GeneratedImage:
        self.calls.append((subject, description))
        return GeneratedImage(data=_opaque_portrait_png(), seed=self.seed)


class _ExplodingBackend:
    """A backend whose removal raises an arbitrary, unbounded exception."""

    def remove_background(self, png_bytes):
        raise RuntimeError("removal exploded arbitrarily")
