"""Data-contract test: bundled scene distribution and decode contract

The bundled terminal scene pack (``unified-scenes-terminal-art``) commits two
finished WebP illustrations under ``web/static/art/scenes/`` together with a
per-image provenance sidecar. This module is the pack's data contract: it
decodes the ACTUAL shipped bytes under the repository's existing bounded image
admission limits, pins the two owned keys to distinct full-bleed 16:9 content,
and cross-checks every sidecar's recorded source, distribution terms,
processing and SHA-256 against the file on disk. Nothing here regenerates,
downloads, or re-encodes artwork: the committed bytes are the subject.

Scene appropriateness itself is a human judgement and lives in each sidecar's
``visual_review`` record, not in a metadata echo — this contract only proves
the bytes decode, stay inside the resource limits, remain two distinct
images, and match what the repository published about them.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
SCENES_DIRECTORY = REPO_ROOT / "web/static/art/scenes"

# The two keys this pack owns and delivers (the archetype scene sentences
# live in world/lore/scene_archetypes.py; the artwork itself is authored here).
OWNED_SCENE_KEYS = ("forest_path", "city_street")

# The declared bound for one committed scene illustration. It is a repository
# media bound (the six built-in fallbacks use their own 400 KiB bound); the
# admission limits that bound decode are the shared ART_SD_MAX_IMAGE_*
# settings, read below rather than re-declared.
SCENE_ART_MAX_FILE_BYTES = 524_288

# Every provenance field this contract reads. The record is deliberately a
# plain JSON document (not a runtime consumer): the art-domain registry that
# resolves bundled scenes arrives with the scene-catalog change.
_PROVENANCE_SECTIONS = (
    "schema_version",
    "key",
    "asset",
    "file",
    "source",
    "license",
    "production",
    "processing",
    "visual_review",
)
_VISUAL_REVIEW_FIELDS = ("native_scale", "desktop_cover_crop", "contact_sheet")

# EXIF UserComment charset prefixes, the two-family rule world.art.formats
# writes (mirrored here rather than imported: the private encoder constants
# are not a public seam, and this decoder is the test-side counterpart).
_ASCII_PREFIX = b"ASCII\x00\x00\x00"
_UNICODE_PREFIX = b"UNICODE\x00"


class SceneArtContractError(AssertionError):
    """A shipped scene asset violates its data contract; always names the key."""


def _asset_path(key: str, directory: Path) -> Path:
    return directory / f"{key}.webp"


def _provenance_path(key: str, directory: Path) -> Path:
    return directory / f"{key}.provenance.json"


def _image_limits() -> tuple[int, int]:
    """The repository's existing bounded image admission limits."""
    from django.conf import settings

    return (
        int(settings.ART_SD_MAX_IMAGE_DIMENSIONS),
        int(settings.ART_SD_MAX_IMAGE_PIXELS),
    )


def _read_bytes(key: str, directory: Path) -> bytes:
    """The shipped payload for one key, bounded, or a keyed contract error."""
    path = _asset_path(key, directory)
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise SceneArtContractError(
            f"{key}: the bundled scene image is missing or unreadable ({error})"
        ) from error
    if not payload:
        raise SceneArtContractError(f"{key}: the bundled scene image is empty")
    if len(payload) >= SCENE_ART_MAX_FILE_BYTES:
        raise SceneArtContractError(
            f"{key}: {len(payload)} bytes reaches the "
            f"{SCENE_ART_MAX_FILE_BYTES} byte scene-art bound"
        )
    return payload


def _decode_bounded(key: str, payload: bytes) -> dict:
    """Fully decode one shipped payload under the existing admission limits.

    A full ``load()`` (not a header read) is deliberate: a truncated or
    corrupted payload must fail here, which is exactly what the corruption
    control asserts.
    """
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            mode, size = image.mode, image.size
    except Exception as error:  # noqa: BLE001 - any decoder failure is a contract failure
        raise SceneArtContractError(
            f"{key}: the bundled scene image does not decode ({error!r})"
        ) from error
    width, height = size
    if width <= 0 or height <= 0:
        raise SceneArtContractError(
            f"{key}: the bundled scene image decoded to non-positive "
            f"dimensions {size!r}"
        )
    max_dimension, max_pixels = _image_limits()
    if width > max_dimension or height > max_dimension or width * height > max_pixels:
        raise SceneArtContractError(
            f"{key}: {width}x{height} exceeds the image admission limits "
            f"({max_dimension}px per side, {max_pixels} pixels)"
        )
    return {"mode": mode, "width": width, "height": height}


def _embedded_parameters(key: str, payload: bytes) -> str:
    """The generation-parameters text the shipped bytes actually carry.

    Decodes the file's EXIF ``UserComment`` (the format-native location for
    WebP, per the art-output-format-pipeline contract) and returns its text.
    A missing, unreadable, or unknown-prefix comment is a keyed contract
    error: the provenance record's ``metadata: a1111_parameters`` claim is
    only true when this text exists.
    """
    import piexif

    try:
        comment = piexif.load(payload)["Exif"][piexif.ExifIFD.UserComment]
    except Exception as error:  # noqa: BLE001 - any EXIF failure is a contract failure
        raise SceneArtContractError(
            f"{key}: the shipped file carries no readable EXIF UserComment ({error!r})"
        ) from error
    if not isinstance(comment, bytes):
        comment = bytes(comment)
    if comment.startswith(_ASCII_PREFIX):
        return comment[len(_ASCII_PREFIX):].decode("ascii", "replace")
    if comment.startswith(_UNICODE_PREFIX):
        return comment[len(_UNICODE_PREFIX):].decode("utf-16-be", "replace")
    raise SceneArtContractError(
        f"{key}: the EXIF UserComment carries no known charset prefix "
        f"({comment[:8]!r})"
    )


def _load_provenance(key: str, directory: Path) -> dict:
    path = _provenance_path(key, directory)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SceneArtContractError(
            f"{key}: the provenance sidecar is missing or malformed ({error})"
        ) from error
    if not isinstance(record, dict):
        raise SceneArtContractError(f"{key}: the provenance sidecar is not an object")
    for section in _PROVENANCE_SECTIONS:
        if section not in record:
            raise SceneArtContractError(
                f"{key}: the provenance sidecar has no {section!r} section"
            )
    return record


class BundledTerminalSceneArtContractTests(unittest.TestCase):
    def test_every_owned_scene_decodes_within_the_admission_limits(self):
        """Each shipped file decodes to a bounded, full-bleed 16:9 landscape."""
        checksums = {}
        for key in OWNED_SCENE_KEYS:
            with self.subTest(key=key):
                payload = _read_bytes(key, SCENES_DIRECTORY)
                decoded = _decode_bounded(key, payload)
                self.assertGreater(decoded["width"], 0)
                self.assertGreater(decoded["height"], 0)
                # A full-bleed scene occupies the whole 16:9 stage canvas:
                # the stage cover-crops, so a non-16:9 asset would silently
                # lose composition the visual review signed off on.
                self.assertEqual(
                    decoded["width"] * 9,
                    decoded["height"] * 16,
                    f"{key}: the bundled scene must be a full-bleed 16:9 landscape",
                )
                checksums[key] = hashlib.sha256(payload).hexdigest()
        self.assertEqual(
            len(set(checksums.values())),
            len(OWNED_SCENE_KEYS),
            "the two bundled scenes must be two distinct images, never one "
            "file committed under several names",
        )

    def test_provenance_matches_the_shipped_bytes_and_licenses_distribution(self):
        """Every sidecar records real source/terms and the actual file bytes."""
        for key in OWNED_SCENE_KEYS:
            with self.subTest(key=key):
                payload = _read_bytes(key, SCENES_DIRECTORY)
                decoded = _decode_bounded(key, payload)
                record = _load_provenance(key, SCENES_DIRECTORY)

                self.assertEqual(record["key"], key)
                self.assertEqual(record["asset"], f"web/static/art/scenes/{key}.webp")

                file_facts = record["file"]
                self.assertEqual(file_facts["format"], "webp")
                self.assertEqual(file_facts["width"], decoded["width"])
                self.assertEqual(file_facts["height"], decoded["height"])
                self.assertEqual(file_facts["bytes"], len(payload))
                self.assertEqual(
                    file_facts["sha256"], hashlib.sha256(payload).hexdigest()
                )

                source = record["source"]
                self.assertTrue(source["kind"], f"{key}: source kind is not recorded")
                self.assertTrue(
                    source["model"] or source["author"],
                    f"{key}: neither a model nor an author is recorded",
                )
                self.assertIsInstance(source["seed"], int)

                license_terms = record["license"]
                self.assertEqual(license_terms["distribution"], "permitted")
                self.assertIn(
                    "redistribut",
                    license_terms["terms"].lower(),
                    f"{key}: distribution terms do not state redistribution",
                )

                production = record["production"]
                self.assertTrue(production["method"])
                self.assertTrue(production["description"])
                self.assertGreater(production["steps"], 0)

                processing = record["processing"]
                self.assertEqual(processing["output_format"], "webp")
                if processing["metadata"] == "a1111_parameters":
                    # The sidecar claims the generation parameters ride the
                    # shipped bytes. Decode that EXIF block and require it to
                    # name the recorded seed and canvas — a bare EXIF marker
                    # would not prove the claim, a matching block does.
                    parameters = _embedded_parameters(key, payload)
                    self.assertIn(
                        f"Seed: {source['seed']}",
                        parameters,
                        f"{key}: the embedded parameters do not carry the "
                        "recorded seed",
                    )
                    self.assertIn(
                        f"Size: {decoded['width']}x{decoded['height']}",
                        parameters,
                        f"{key}: the embedded parameters do not carry the "
                        "decoded canvas size",
                    )

                for field in _VISUAL_REVIEW_FIELDS:
                    self.assertTrue(
                        record["visual_review"][field].strip(),
                        f"{key}: the visual review records no {field}",
                    )

    def test_a_corrupt_payload_is_refused_naming_the_key(self):
        """Corruption control: the decode check must fail and name the key."""
        with tempfile.TemporaryDirectory() as scratch:
            directory = Path(scratch)
            _asset_path("forest_path", directory).write_bytes(
                b"this is not a webp image at all"
            )
            with self.assertRaises(SceneArtContractError) as caught:
                _decode_bounded(
                    "forest_path", _read_bytes("forest_path", directory)
                )
        self.assertIn("forest_path", str(caught.exception))

    def test_a_truncated_payload_is_refused_naming_the_key(self):
        """A half-written file (a real corruption shape) must not pass."""
        payload = _read_bytes("city_street", SCENES_DIRECTORY)
        with self.assertRaises(SceneArtContractError) as caught:
            _decode_bounded("city_street", payload[: len(payload) // 2])
        self.assertIn("city_street", str(caught.exception))

    def test_a_missing_payload_is_reported_naming_the_key(self):
        """Missing-file control: absence must fail and name the key."""
        with tempfile.TemporaryDirectory() as scratch:
            with self.assertRaises(SceneArtContractError) as caught:
                _read_bytes("forest_path", Path(scratch))
        self.assertIn("forest_path", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
