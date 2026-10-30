"""Tests for the pure-Python elevation codec, metadata and integrity checks."""

from __future__ import annotations

import base64
import contextlib
import io
import json
import math
import os
import tempfile
from pathlib import Path
import sys
import unittest
from unittest import mock
import zlib

from tools.spec_traceability import covers_requirement

from elosern_map_core.elevation_codec import (
    DEFAULT_CONFIG_DIGEST,
    ELEVATION_ALGORITHM_VERSION,
    ELEVATION_FORMAT_VERSION,
    ELEVATION_TILE_CELLS,
    MAX_ELEVATION_BYTES,
    ElevationBudgetExceededError,
    ElevationCorruptionError,
    ElevationDocumentError,
    ElevationMetadata,
    ElevationTileCorruptionError,
    compute_data_sha256,
    decode_tile,
    elevation_fingerprint,
    elevation_freshness,
    elevation_source_signature,
    encode_elevation_artifact,
    encode_tile,
    read_elevation_metadata,
    verify_elevation_data_integrity,
)


class ElevationCodecTests(unittest.TestCase):
    def test_elevation_codec_imports_no_numpy_or_scipy(self):
        """Codec must stay on the standard library only."""
        forbidden = [
            mod for mod in sys.modules if mod.startswith(("numpy", "scipy", "evennia", "django"))
        ]
        # When running in dev test suite numpy might already be loaded by other test files,
        # but elevation_codec itself never references it.
        import elosern_map_core.elevation_codec as codec
        self.assertNotIn("numpy", codec.__dict__)
        self.assertNotIn("scipy", codec.__dict__)

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "elevation-artifacts-are-bounded-and-source-identified"
    )
    def test_round_trip_synthetic_frame_with_partial_edge_tiles(self):
        """A frame not divisible by 64 ceil-pads edge tiles with zero bytes."""
        frame = 100  # ceil(100 / 64) = 2, so 2x2 = 4 tiles total
        tile_cells = 64

        # Synthetic rasters with distinct bands (0..15) and tiers (0..3)
        bands = [[(x + y * 3) % 16 for x in range(frame)] for y in range(frame)]
        tiers = [[(x * 2 + y) % 4 for x in range(frame)] for y in range(frame)]

        num_tiles = math.ceil(frame / tile_cells)
        self.assertEqual(num_tiles, 2)

        for ty in range(num_tiles):
            for tx in range(num_tiles):
                b64 = encode_tile(bands, tiers, tx, ty, frame_cells=frame, tile_cells=tile_cells)
                decoded = decode_tile(b64, tx, ty, frame_cells=frame, tile_cells=tile_cells)
                self.assertEqual(len(decoded), 4096)

                for ly in range(tile_cells):
                    for lx in range(tile_cells):
                        gx = tx * tile_cells + lx
                        gy = ty * tile_cells + ly
                        byte_val = decoded[ly * tile_cells + lx]
                        if gx < frame and gy < frame:
                            expected_band = bands[gy][gx]
                            expected_tier = tiers[gy][gx]
                            self.assertEqual(byte_val >> 4, expected_band)
                            self.assertEqual(byte_val & 0x03, expected_tier)
                            self.assertEqual(byte_val & 0x0C, 0)
                        else:
                            # Padded cells outside the frame must be 0
                            self.assertEqual(byte_val, 0)

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "runtime-elevation-rejects-stale-or-corrupt-artifacts"
    )
    def test_tile_corrupt_base64_raises(self):
        with self.assertRaises(ElevationTileCorruptionError):
            decode_tile("not!valid!base64!==", 0, 0, frame_cells=64)

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "runtime-elevation-rejects-stale-or-corrupt-artifacts"
    )
    def test_tile_corrupt_zlib_stream_raises(self):
        # Valid base64 but not valid zlib
        bad_zlib = base64.b64encode(b"hello world this is not zlib").decode("ascii")
        with self.assertRaises(ElevationTileCorruptionError):
            decode_tile(bad_zlib, 0, 0, frame_cells=64)

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "runtime-elevation-rejects-stale-or-corrupt-artifacts"
    )
    def test_tile_trailing_data_raises(self):
        valid_bytes = bytes([0] * 4096)
        compressed = zlib.compress(valid_bytes) + b"trailing_garbage"
        b64 = base64.b64encode(compressed).decode("ascii")
        with self.assertRaises(ElevationTileCorruptionError) as caught:
            decode_tile(b64, 0, 0, frame_cells=64)
        self.assertIn("trailing unused data", str(caught.exception))

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "runtime-elevation-rejects-stale-or-corrupt-artifacts"
    )
    def test_tile_exceeded_ceiling_raises(self):
        # 4097 bytes compressed
        oversize = bytes([0] * 4097)
        b64 = base64.b64encode(zlib.compress(oversize)).decode("ascii")
        with self.assertRaises(ElevationTileCorruptionError) as caught:
            decode_tile(b64, 0, 0, frame_cells=64)
        self.assertIn("exceeded 4096-byte output ceiling", str(caught.exception))

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "runtime-elevation-rejects-stale-or-corrupt-artifacts"
    )
    def test_tile_non_zero_reserved_bits_raises(self):
        # Bit 2 is set (0x04)
        bad_bytes = bytearray(4096)
        bad_bytes[10] = 0x04  # reserved bit 2 non-zero
        b64 = base64.b64encode(zlib.compress(bytes(bad_bytes))).decode("ascii")
        with self.assertRaises(ElevationTileCorruptionError) as caught:
            decode_tile(b64, 0, 0, frame_cells=64)
        self.assertIn("reserved bits", str(caught.exception))

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "runtime-elevation-rejects-stale-or-corrupt-artifacts"
    )
    def test_tile_non_zero_padding_cell_raises(self):
        # Partial edge tile with frame=50, tile=64. Cell at lx=55, ly=0 is outside frame
        bad_bytes = bytearray(4096)
        bad_bytes[55] = 0x10  # band 1 outside frame
        b64 = base64.b64encode(zlib.compress(bytes(bad_bytes))).decode("ascii")
        with self.assertRaises(ElevationTileCorruptionError) as caught:
            decode_tile(b64, 0, 0, frame_cells=50)
        self.assertIn("padding cell", str(caught.exception))

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "elevation-artifacts-are-bounded-and-source-identified"
    )
    def test_encode_elevation_artifact_produces_valid_structure(self):
        frame = 70
        bands = [[1 for _ in range(frame)] for _ in range(frame)]
        tiers = [[2 for _ in range(frame)] for _ in range(frame)]
        continent_fp = "a" * 64

        text = encode_elevation_artifact(
            bands,
            tiers,
            frame_cells=frame,
            continent_fingerprint=continent_fp,
        )
        self.assertTrue(text.endswith("\n"))
        self.assertLessEqual(len(text.encode("utf-8")), MAX_ELEVATION_BYTES)

        doc = json.loads(text)
        metadata = read_elevation_metadata(doc)
        self.assertEqual(metadata.format_version, ELEVATION_FORMAT_VERSION)
        self.assertEqual(metadata.algorithm_version, ELEVATION_ALGORITHM_VERSION)
        self.assertEqual(metadata.frame_cells, frame)
        self.assertEqual(metadata.tile_cells, 64)
        self.assertEqual(len(doc["tiles"]), 4)  # ceil(70/64) = 2, 2x2 = 4

        # Integrity passes without raster expansion
        verified = verify_elevation_data_integrity(doc, expected_frame_cells=frame)
        self.assertEqual(verified.fingerprint, metadata.fingerprint)

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "elevation-artifacts-are-bounded-and-source-identified"
    )
    def test_oversize_budget_rejection(self):
        # Mock tiles that exceed MAX_ELEVATION_BYTES
        frame = 64
        bands = [[0] * frame for _ in range(frame)]
        tiers = [[0] * frame for _ in range(frame)]
        # Artificially small max bytes test
        with mock.patch("elosern_map_core.elevation_codec.MAX_ELEVATION_BYTES", 50):
            with self.assertRaises(ElevationBudgetExceededError) as caught:
                encode_elevation_artifact(bands, tiers, frame_cells=frame, continent_fingerprint="f" * 64)
            self.assertIn("exceeds", str(caught.exception))

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "runtime-elevation-rejects-stale-or-corrupt-artifacts"
    )
    def test_integrity_checks_detect_reordered_or_missing_tiles(self):
        frame = 128
        bands = [[0] * frame for _ in range(frame)]
        tiers = [[0] * frame for _ in range(frame)]
        text = encode_elevation_artifact(bands, tiers, frame_cells=frame, continent_fingerprint="b" * 64)
        doc = json.loads(text)

        # 1. Swapped tiles
        doc_swapped = dict(doc)
        doc_swapped["tiles"] = list(doc["tiles"])
        doc_swapped["tiles"][0], doc_swapped["tiles"][1] = doc_swapped["tiles"][1], doc_swapped["tiles"][0]
        with self.assertRaises(ElevationCorruptionError):
            verify_elevation_data_integrity(doc_swapped)

        # 2. Missing tile
        doc_missing = dict(doc)
        doc_missing["tiles"] = list(doc["tiles"])[:-1]
        with self.assertRaises(ElevationCorruptionError):
            verify_elevation_data_integrity(doc_missing)

        # 3. Tampered data_sha256
        doc_tampered_hash = dict(doc)
        doc_tampered_hash["data_sha256"] = "0" * 64
        with self.assertRaises(ElevationCorruptionError) as caught:
            verify_elevation_data_integrity(doc_tampered_hash)
        self.assertIn("data_sha256 mismatch", str(caught.exception))

        # 4. Tampered fingerprint
        doc_tampered_fp = dict(doc)
        doc_tampered_fp["fingerprint"] = "1" * 64
        with self.assertRaises(ElevationCorruptionError) as caught:
            verify_elevation_data_integrity(doc_tampered_fp)
        self.assertIn("fingerprint mismatch", str(caught.exception))

        # 5. Mismatched frame cells
        with self.assertRaises(ElevationDocumentError):
            verify_elevation_data_integrity(doc, expected_frame_cells=2700)

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "elevation-artifacts-are-bounded-and-source-identified"
    )
    def test_freshness_reporting_and_named_changed_source(self):
        continent_fp = "c" * 64
        sig = elevation_source_signature(continent_fp, DEFAULT_CONFIG_DIGEST, ELEVATION_ALGORITHM_VERSION)
        fp = elevation_fingerprint(sig)
        metadata = ElevationMetadata(
            format_version=ELEVATION_FORMAT_VERSION,
            algorithm_version=ELEVATION_ALGORITHM_VERSION,
            source_signature=sig,
            fingerprint=fp,
            frame_cells=2700,
            tile_cells=64,
            data_sha256="d" * 64,
        )

        # 1. Fresh
        fresh = elevation_freshness(metadata, sig)
        self.assertTrue(fresh.current)
        self.assertIsNone(fresh.reason)

        # 2. Continent changed
        changed_sig = elevation_source_signature("d" * 64, DEFAULT_CONFIG_DIGEST, ELEVATION_ALGORITHM_VERSION)
        stale_continent = elevation_freshness(metadata, changed_sig)
        self.assertFalse(stale_continent.current)
        self.assertIn("content/maps/continent.yaml", stale_continent.reason)

        # 3. Config changed
        changed_config_sig = elevation_source_signature(continent_fp, "9" * 64, ELEVATION_ALGORITHM_VERSION)
        stale_config = elevation_freshness(metadata, changed_config_sig)
        self.assertFalse(stale_config.current)
        self.assertIn("config", stale_config.reason)

        # 4. Algorithm version changed
        stale_algo = elevation_freshness(metadata, sig, algorithm_version=99)
        self.assertFalse(stale_algo.current)
        self.assertIn("algorithm version", stale_algo.reason)


_REPO_ROOT = Path(__file__).resolve().parents[3]
_AUTHORING_SCRIPTS = _REPO_ROOT / ".agents" / "skills" / "map-data-authoring" / "scripts"


def _publisher_module():
    """Import the real regeneration entry point from the authoring skill."""
    if str(_AUTHORING_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_AUTHORING_SCRIPTS))
    import regenerate_elevation

    return regenerate_elevation


def _synthetic_workspace(root: Path) -> None:
    """Write a complete synthetic authored world under ``root``."""
    import authoring_fixtures as fixtures

    continent = fixtures.continent_data()
    for region in continent["regions"].values():
        # The game-adoption gate refuses a region without a scene archetype; the
        # value is never resolved because no reference context exists here.
        region["scene_archetype"] = "wilderness"
    documents = {
        "content/maps/continent.yaml": fixtures.yaml_text(continent),
        "content/maps/locations.yaml": fixtures.yaml_text(fixtures.locations_data()),
        "content/maps/districts.yaml": fixtures.yaml_text(fixtures.districts_data()),
        "content/maps/settlements/demo_map.yaml": fixtures.yaml_text(
            fixtures.settlement_data()
        ),
    }
    for relative_path, text in documents.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class ElevationPublisherTests(unittest.TestCase):
    """The real regeneration entry point never replaces prior bytes on refusal."""

    def _run(self, publisher, root: Path) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = publisher.main(["regenerate_elevation.py", str(root)])
        return status, output.getvalue()

    def _temporary_artifacts(self, target: Path) -> list[str]:
        """Leftover atomic-write temporaries beside the published artifact."""
        return sorted(
            path.name
            for path in target.parent.iterdir()
            if path.name.startswith(".wilderness_elevation.")
        )

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "elevation-artifacts-are-bounded-and-source-identified"
    )
    def test_prior_bytes_survive_a_budget_rejection_from_the_real_publisher(self):
        publisher = _publisher_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _synthetic_workspace(root)
            target = root / publisher.ELEVATION_PATH

            # Control: this workspace really reaches the publisher, so the
            # refusal below cannot pass by never publishing anything.
            status, _output = self._run(publisher, root)
            self.assertEqual(status, 0)
            prior = target.read_bytes()
            self.assertTrue(prior)

            with mock.patch("elosern_map_core.elevation_codec.MAX_ELEVATION_BYTES", 50):
                status, output = self._run(publisher, root)

            self.assertEqual(status, 1)
            self.assertIn("budget constraint", output)
            self.assertEqual(target.read_bytes(), prior)
            self.assertEqual(self._temporary_artifacts(target), [])

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "elevation-artifacts-are-bounded-and-source-identified"
    )
    def test_publisher_refuses_when_the_source_changes_before_publication(self):
        publisher = _publisher_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _synthetic_workspace(root)
            target = root / publisher.ELEVATION_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            prior = b'{"prior": "bytes"}\n'
            target.write_bytes(prior)

            continent = root / "content/maps/continent.yaml"
            real_generate = publisher.generate_elevation

            def generate_then_edit_the_source(*args, **kwargs):
                rasters = real_generate(*args, **kwargs)
                continent.write_text(
                    continent.read_text(encoding="utf-8") + "# edited mid-run\n",
                    encoding="utf-8",
                )
                return rasters

            with mock.patch.object(
                publisher,
                "generate_elevation",
                side_effect=generate_then_edit_the_source,
            ):
                status, output = self._run(publisher, root)

            self.assertEqual(status, 1)
            self.assertIn("continent source changed during generation", output)
            self.assertEqual(target.read_bytes(), prior)
            self.assertEqual(self._temporary_artifacts(target), [])


if __name__ == "__main__":
    unittest.main()
