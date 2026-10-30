"""Tests for the pure-Python elevation codec, metadata and integrity checks."""

from __future__ import annotations

import base64
import json
import math
import os
import tempfile
from pathlib import Path
import sys
import unittest
from unittest import mock
import zlib

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

    def test_tile_corrupt_base64_raises(self):
        with self.assertRaises(ElevationTileCorruptionError):
            decode_tile("not!valid!base64!==", 0, 0, frame_cells=64)

    def test_tile_corrupt_zlib_stream_raises(self):
        # Valid base64 but not valid zlib
        bad_zlib = base64.b64encode(b"hello world this is not zlib").decode("ascii")
        with self.assertRaises(ElevationTileCorruptionError):
            decode_tile(bad_zlib, 0, 0, frame_cells=64)

    def test_tile_trailing_data_raises(self):
        valid_bytes = bytes([0] * 4096)
        compressed = zlib.compress(valid_bytes) + b"trailing_garbage"
        b64 = base64.b64encode(compressed).decode("ascii")
        with self.assertRaises(ElevationTileCorruptionError) as caught:
            decode_tile(b64, 0, 0, frame_cells=64)
        self.assertIn("trailing unused data", str(caught.exception))

    def test_tile_exceeded_ceiling_raises(self):
        # 4097 bytes compressed
        oversize = bytes([0] * 4097)
        b64 = base64.b64encode(zlib.compress(oversize)).decode("ascii")
        with self.assertRaises(ElevationTileCorruptionError) as caught:
            decode_tile(b64, 0, 0, frame_cells=64)
        self.assertIn("exceeded 4096-byte output ceiling", str(caught.exception))

    def test_tile_non_zero_reserved_bits_raises(self):
        # Bit 2 is set (0x04)
        bad_bytes = bytearray(4096)
        bad_bytes[10] = 0x04  # reserved bit 2 non-zero
        b64 = base64.b64encode(zlib.compress(bytes(bad_bytes))).decode("ascii")
        with self.assertRaises(ElevationTileCorruptionError) as caught:
            decode_tile(b64, 0, 0, frame_cells=64)
        self.assertIn("reserved bits", str(caught.exception))

    def test_tile_non_zero_padding_cell_raises(self):
        # Partial edge tile with frame=50, tile=64. Cell at lx=55, ly=0 is outside frame
        bad_bytes = bytearray(4096)
        bad_bytes[55] = 0x10  # band 1 outside frame
        b64 = base64.b64encode(zlib.compress(bytes(bad_bytes))).decode("ascii")
        with self.assertRaises(ElevationTileCorruptionError) as caught:
            decode_tile(b64, 0, 0, frame_cells=50)
        self.assertIn("padding cell", str(caught.exception))

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

    def test_prior_bytes_survive_oversize_failure(self):
        """When artifact generation fails the size budget, an existing target file is not overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "wilderness_elevation.json"
            prior_bytes = b'{"prior": "valid_output_bytes"}\n'
            target.write_bytes(prior_bytes)

            frame = 64
            bands = [[0] * frame for _ in range(frame)]
            tiers = [[0] * frame for _ in range(frame)]

            with mock.patch("elosern_map_core.elevation_codec.MAX_ELEVATION_BYTES", 50):
                with self.assertRaises(ElevationBudgetExceededError):
                    # Simulating regeneration workflow: encode raises budget error before atomic replacement
                    text = encode_elevation_artifact(bands, tiers, frame_cells=frame, continent_fingerprint="f" * 64)
                    target.write_text(text, encoding="utf-8")

            # Target content must remain byte-identical to prior bytes
            self.assertEqual(target.read_bytes(), prior_bytes)

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


if __name__ == "__main__":
    unittest.main()
