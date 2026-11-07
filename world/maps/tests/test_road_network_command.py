"""The road network regeneration command, on synthetic input only.

Every test patches the Evennia bootstrap, the input builder and the artifact
text, so no shipped world is composed and no network is computed: the command's
own behaviour (check mode, failure handling and the explicit preview) is what
is established. Temporary output paths keep the committed artifact untouched.

Requirement annotations are added when the archive sync gives the change's
requirements canonical identifiers.
"""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

from elosern_map_core.roads import RoadGenerationError, RoadInput, RoadNode
from elosern_map_core.roads_codec import encode_road_document
from tools import road_network as command

SIZE = 9


def _input() -> RoadInput:
    walkable = np.ones((SIZE, SIZE), dtype=bool)
    walkable[0, :] = False
    region = np.ones((SIZE, SIZE), dtype=np.uint8)
    region[0, :] = 0  # one row of sea
    return RoadInput(
        size=SIZE,
        walkable=walkable,
        region=region,
        region_names=("region_plain",),
        bands=np.zeros((SIZE, SIZE), dtype=np.int16),
        region_speeds={"region_plain": 4000},
        nodes=(RoadNode("node_a", ((1, 4),)), RoadNode("node_b", ((7, 4),))),
        blocked=frozenset(),
        point_gateways={},
        forbidden_regions=(),
        slope_factor_per_band=0.0,
        noise_amplitude=0.0,
        noise_wavelength_cells=4.0,
        noise_seed=1,
        detour_limit=2.0,
        reuse_factor=1.0,
        source_signature="synthetic-signature",
    )


TEXT = encode_road_document(
    frame_cells=SIZE,
    source_signature="synthetic-signature",
    nodes=["node_a", "node_b"],
    roads=[("node_a", "node_b", tuple((x, 4) for x in range(1, 8)))],
)


class RoadNetworkCommandTests(unittest.TestCase):
    """The regeneration command reports stale artifacts."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def _run(self, *argv: str, text=TEXT) -> tuple[int, str]:
        generate = mock.Mock(side_effect=text) if isinstance(text, Exception) else mock.Mock(return_value=text)
        output = io.StringIO()
        with (
            mock.patch.object(command, "_bootstrap"),
            mock.patch.object(command, "build_input", return_value=_input()),
            mock.patch.object(command, "artifact_text", generate),
            mock.patch.object(command, "_ford_cells", return_value=frozenset({(4, 6)})),
            contextlib.redirect_stdout(output),
        ):
            status = command.main(list(argv))
        return status, output.getvalue()

    def test_check_mode_reports_a_stale_file_and_accepts_an_identical_one(self):
        stale = self.directory / "stale.json"
        stale.write_text("{}\n", encoding="utf-8")
        current = self.directory / "current.json"
        current.write_text(TEXT, encoding="utf-8")

        status, report = self._run("--check", "--output", str(stale))
        self.assertEqual(status, 1)
        self.assertIn(command.COMMAND, report)
        self.assertEqual(stale.read_text(encoding="utf-8"), "{}\n")

        status, _ = self._run("--check", "--output", str(current))
        self.assertEqual(status, 0)
        self.assertEqual(current.read_text(encoding="utf-8"), TEXT)

    def test_check_mode_reports_a_missing_file_without_writing_it(self):
        missing = self.directory / "missing.json"
        status, _ = self._run("--check", "--output", str(missing))
        self.assertEqual(status, 1)
        self.assertFalse(missing.exists())

    def test_generation_writes_the_artifact(self):
        target = self.directory / "roads.json"
        target.write_text("old\n", encoding="utf-8")
        status, _ = self._run("--output", str(target))
        self.assertEqual(status, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), TEXT)

    def test_failed_generation_leaves_the_artifact(self):
        target = self.directory / "roads.json"
        target.write_text("previous bytes\n", encoding="utf-8")
        failure = RoadGenerationError(["node node_a: has no road", "node node_b: has no road"])
        status, report = self._run("--output", str(target), text=failure)
        self.assertEqual(status, 1)
        self.assertIn("node node_a: has no road", report)
        self.assertIn("node node_b: has no road", report)
        self.assertEqual(target.read_text(encoding="utf-8"), "previous bytes\n")

    def test_preview_is_written_only_when_requested(self):
        target = self.directory / "roads.json"
        status, _ = self._run("--output", str(target))
        self.assertEqual(status, 0)
        self.assertEqual(sorted(path.name for path in self.directory.iterdir()), ["roads.json"])

        image_path = self.directory / "preview.png"
        status, _ = self._run("--output", str(target), "--preview", str(image_path))
        self.assertEqual(status, 0)
        with Image.open(image_path) as image:
            self.assertEqual(image.size, (SIZE, SIZE))
            pixels = image.convert("RGB")
            # North is up: the sea row y = 0 is the bottom image row, and the
            # road, ford and plain land cells keep their own colours.
            self.assertEqual(pixels.getpixel((0, SIZE - 1)), command._SEA)
            self.assertEqual(pixels.getpixel((4, SIZE - 1 - 4)), command._ROAD)
            self.assertEqual(pixels.getpixel((8, 0)), command._LAND)
            self.assertEqual(pixels.getpixel((4, SIZE - 1 - 6)), command._FORD)


class BandRasterTests(unittest.TestCase):
    def test_tiles_are_row_major_and_sliced_to_the_frame(self):
        tile = 4

        class Runtime:
            frame_cells = 6
            tile_cells = tile

            @staticmethod
            def get_tile(tx, ty):
                # Band = 4 * tile index + local row, tier bits set to prove masking.
                rows = [((tx + 2 * ty) * 4 + ly) << 4 | 0x3 for ly in range(tile)]
                return bytes(value for value in rows for _ in range(tile))

        bands = command.band_raster(Runtime())
        self.assertEqual(bands.shape, (6, 6))
        self.assertEqual(bands.dtype, np.int16)
        self.assertEqual(int(bands[0, 0]), 0)
        self.assertEqual(int(bands[3, 0]), 3)
        self.assertEqual(int(bands[1, 5]), 5)  # tile (1, 0), local row 1
        self.assertEqual(int(bands[5, 0]), 9)  # tile (0, 1), local row 1
        self.assertEqual(int(bands[5, 5]), 13)  # tile (1, 1), local row 1


if __name__ == "__main__":
    unittest.main()
