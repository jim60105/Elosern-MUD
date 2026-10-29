"""The capture command, executed from the source workspace as a real invocation.

Every case runs ``.agents/skills/map-data-authoring/scripts/capture_map.py`` in
the editor's own locked capture environment, with a scrubbed environment and
no editor service: the command reads a temporary synthetic workspace, renders
the local page in headless Chromium and publishes an image. The assertions read
the published bytes (decoded through the same environment), the single success
object and the refusals, and they compare workspace digests around every run.

Nothing here starts the service, a dev server or Node, and nothing reads
shipped map content.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"
PROJECT = REPO_ROOT / "tools" / "map-editor"
SCRIPT = REPO_ROOT / ".agents" / "skills" / "map-data-authoring" / "scripts" / "capture_map.py"
ARTIFACT = "world/maps/data/district_partition.json"
SETTLEMENT = f"content/maps/settlements/{'synthetic_town'}.yaml"
DOCUMENTS = (
    "content/maps/continent.yaml",
    "content/maps/locations.yaml",
    "content/maps/districts.yaml",
)
RESULT_KEYS = {
    "image_path",
    "view",
    "map_id",
    "format",
    "width",
    "height",
    "bounds",
    "units",
    "axes",
    "hidden_layers",
    "diagnostics",
}


def _load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, EDITOR_TESTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


harness = _load("process_harness")
synthetic = _load("synthetic_workspace")

_DECODE = """
import hashlib
import json
import sys

from PIL import Image

rows = {}
for path in json.loads(sys.argv[1]):
    with Image.open(path) as image:
        image.load()
        rgb = image.convert("RGB")
        extrema = rgb.getextrema()
        rows[path] = {
            "size": list(image.size),
            "format": image.format,
            "digest": hashlib.sha256(rgb.tobytes()).hexdigest(),
            "varied": any(low != high for low, high in extrema),
        }
print(json.dumps(rows))
"""

_PYTHON: Path | None = None
_READY = False

_IMPORT_PROBE = "import playwright, PIL.features"
_LAUNCH_PROBE = """
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    browser.close()
"""


def _probe(python: Path, code: str) -> bool:
    return (
        subprocess.run(
            [str(python), "-I", "-c", code],
            env=harness.scrubbed_env(),
            capture_output=True,
            timeout=180,
        ).returncode
        == 0
    )


def capture_python() -> Path:
    """The editor interpreter with the optional capture group installed.

    Preparing it is this suite's job, exactly like the sibling wrapper modules:
    the command itself never installs anything at runtime.
    """

    global _PYTHON, _READY
    uv = shutil.which("uv")
    if uv is None:
        raise harness.EditorUnavailable("uv is not installed")
    if _PYTHON is not None and _probe(_PYTHON, _IMPORT_PROBE):
        if _READY or _probe(_PYTHON, _LAUNCH_PROBE):
            _READY = True
            return _PYTHON
    sync = subprocess.run(
        [uv, "sync", "--locked", "--project", str(PROJECT), "--group", "capture"],
        cwd=PROJECT,
        env=harness.scrubbed_env(),
        capture_output=True,
        text=True,
        timeout=900,
    )
    if sync.returncode != 0:
        raise harness.EditorUnavailable(f"uv sync --group capture failed:\n{sync.stderr[-2000:]}")
    python = PROJECT / ".venv" / "bin" / "python"
    if not python.exists():
        raise harness.EditorUnavailable(f"{python} is missing after uv sync")
    if not _probe(python, _LAUNCH_PROBE):
        install = subprocess.run(
            [str(python), "-m", "playwright", "install", "chromium"],
            env=harness.scrubbed_env(),
            capture_output=True,
            text=True,
            timeout=900,
        )
        if install.returncode != 0:
            raise harness.EditorUnavailable(
                f"playwright install chromium failed:\n{install.stderr[-2000:]}"
            )
        if not _probe(python, _LAUNCH_PROBE):
            raise harness.EditorUnavailable(
                "Chromium still cannot launch in the editor environment; "
                "install its system dependencies (playwright install --with-deps chromium)"
            )
    _PYTHON = python
    _READY = True
    return python


def _artifact(root: Path) -> str:
    from elosern_map_core import discover_source_documents, load_authoring_world
    from elosern_map_core.partition import generate_partition, partition_input, world_snapshot

    world = load_authoring_world(discover_source_documents(root))
    return generate_partition(partition_input(world_snapshot(world)))


def install_partition(root: Path) -> str:
    text = _artifact(root)
    target = root / ARTIFACT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return text


def decode_images(*paths: Path) -> dict[str, dict]:
    result = subprocess.run(
        [str(capture_python()), "-I", "-c", _DECODE, json.dumps([str(path) for path in paths])],
        cwd=REPO_ROOT,
        env=harness.scrubbed_env(),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise AssertionError(f"decoding the capture output failed:\n{result.stderr[-4000:]}")
    return json.loads(result.stdout)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _CaptureCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            capture_python()
        except harness.EditorUnavailable as error:
            if not harness.skip_allowed():
                raise
            raise unittest.SkipTest(f"standalone editor capture environment unavailable: {error}") from error

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="map-image-capture-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.output = self.root / "out"
        self.output.mkdir()

    def out(self, name: str) -> str:
        """An absolute destination inside this test's own output directory."""

        return str(self.output / name)

    def plain(self) -> Path:
        return synthetic.write_workspace(self.workspace)

    def partitioned(self) -> Path:
        root = synthetic.write_partitionable_workspace(self.workspace)
        install_partition(root)
        return root

    def run_capture(self, *arguments: str, cwd: Path | None = None, env=None):
        environment = harness.scrubbed_env() if env is None else env
        return subprocess.run(
            [str(capture_python()), "-I", str(SCRIPT), *arguments],
            cwd=cwd or self.workspace,
            env=environment,
            capture_output=True,
            text=True,
            timeout=300,
        )

    def succeeded(self, *arguments: str, cwd: Path | None = None, env=None) -> dict:
        result = self.run_capture(*arguments, cwd=cwd, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1, f"one success object, not {lines}")
        document = json.loads(lines[0])
        self.assertEqual(set(document), RESULT_KEYS)
        return document

    def refused(self, *arguments: str, code: str | None = None, contains: str = "") -> str:
        result = self.run_capture(*arguments)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout.strip(), "", "a refusal publishes no success object")
        if code is not None:
            self.assertIn(code, result.stderr)
        if contains:
            self.assertIn(contains, result.stderr)
        return result.stderr

    def assert_image(self, path: Path, document: dict, *, image_format: str) -> dict:
        self.assertTrue(path.is_file(), f"{path} was not published")
        self.assertEqual(document["image_path"], str(path))
        decoded = decode_images(path)[str(path)]
        self.assertEqual(decoded["size"], [document["width"], document["height"]])
        self.assertEqual(decoded["format"], image_format.upper())
        self.assertTrue(decoded["varied"], "the captured map is not a blank image")
        return decoded


# -- one validated view, lossless publication --------------------------------


class CaptureInvocationTests(_CaptureCase):
    def test_continent_defaults_publish_one_lossless_image_with_camera_metadata(self):
        root = self.partitioned()
        before = synthetic.tree_digest(root)

        document = self.succeeded("--view", "continent", "--output", self.out("overview.webp"))

        self.assertEqual(document["view"], "continent")
        self.assertIsNone(document["map_id"])
        self.assertEqual((document["format"], document["width"], document["height"]), ("webp", 1280, 960))
        self.assertEqual(document["hidden_layers"], [])
        self.assertEqual(document["units"], "km")
        self.assertEqual(document["axes"], {"x": "east", "y": "north"})
        self.assertTrue(Path(document["image_path"]).is_absolute())
        bounds = document["bounds"]
        self.assertEqual(len(bounds), 4)
        self.assertLess(bounds[0], bounds[2])
        self.assertLess(bounds[1], bounds[3])
        # The synthetic continent is 40 km square; a fitted camera covers it.
        self.assertLessEqual(bounds[0], 0)
        self.assertLessEqual(bounds[1], 0)
        self.assertGreaterEqual(bounds[2], 40)
        self.assertGreaterEqual(bounds[3], 40)
        self.assertIsInstance(document["diagnostics"], list)
        self.assert_image(self.output / "overview.webp", document, image_format="webp")
        self.assertEqual(synthetic.tree_digest(root), before)
        self.assertEqual([path.name for path in self.output.iterdir()], ["overview.webp"])

    def test_settlement_and_interior_report_their_own_frames(self):
        root = self.plain()
        before = synthetic.tree_digest(root)

        settlement = self.succeeded(
            "--view", "settlement", "--map", synthetic.SETTLEMENT_ID, "--output", self.out("town.webp")
        )
        self.assertEqual((settlement["units"], settlement["axes"]), ("m", {"x": "east", "y": "north"}))
        self.assertEqual(settlement["map_id"], synthetic.SETTLEMENT_ID)

        interior = self.succeeded(
            "--view", "interior", "--map", synthetic.INTERIOR_ID, "--output", self.out("hall.webp")
        )
        self.assertEqual((interior["units"], interior["axes"]), ("layout", {"x": "right", "y": "down"}))
        self.assertEqual(interior["map_id"], synthetic.INTERIOR_ID)
        self.assertNotEqual(settlement["bounds"], interior["bounds"])
        self.assert_image(self.output / "town.webp", settlement, image_format="webp")
        self.assert_image(self.output / "hall.webp", interior, image_format="webp")
        self.assertEqual(synthetic.tree_digest(root), before)

    def test_explicit_regions_expand_to_each_output_aspect_ratio(self):
        self.partitioned()

        wide = self.succeeded(
            "--view", "continent", "--bounds", "0", "0", "10", "10",
            "--width", "200", "--height", "100", "--output", self.out("wide.png"), "--format", "png",
        )
        # One uniform scale about the requested centre: the narrower axis grows.
        self.assertEqual(wide["bounds"], [-5, 0, 15, 10])
        self.assert_image(self.output / "wide.png", wide, image_format="png")

        tall = self.succeeded(
            "--view", "continent", "--bounds", "0", "0", "10", "10",
            "--width", "100", "--height", "200", "--output", self.out("tall.png"), "--format", "png",
        )
        self.assertEqual(tall["bounds"], [0, -5, 10, 15])
        self.assert_image(self.output / "tall.png", tall, image_format="png")

        interior = self.succeeded(
            "--view", "interior", "--map", synthetic.INTERIOR_ID,
            "--bounds", "1", "2", "5", "8", "--width", "100", "--height", "100",
            "--output", self.out("region.png"), "--format", "png",
        )
        # Interior bounds are layout units with y growing down; the reported
        # rectangle comes back in the same frame.
        self.assertEqual(interior["bounds"], [0, 2, 6, 8])
        self.assertEqual((interior["units"], interior["axes"]), ("layout", {"x": "right", "y": "down"}))
        self.assert_image(self.output / "region.png", interior, image_format="png")

    def test_both_formats_decode_to_the_same_lossless_pixels(self):
        self.plain()
        arguments = (
            "--view", "settlement", "--map", synthetic.SETTLEMENT_ID,
            "--width", "320", "--height", "240",
        )

        webp = self.succeeded(*arguments, "--output", self.out("same.webp"))
        png = self.succeeded(*arguments, "--output", self.out("same.png"), "--format", "png")

        decoded = decode_images(self.output / "same.webp", self.output / "same.png")
        first = decoded[str(self.output / "same.webp")]
        second = decoded[str(self.output / "same.png")]
        self.assertEqual(first["size"], second["size"])
        self.assertEqual(first["digest"], second["digest"], "both formats are lossless copies of one render")
        self.assertEqual((first["format"], second["format"]), ("WEBP", "PNG"))
        self.assertEqual((webp["format"], png["format"]), ("webp", "png"))

    def test_every_layer_can_be_hidden_and_the_camera_does_not_move(self):
        cases = (
            ("continent", None, ("terrain", "water", "ridge", "locations", "footprint", "partition", "labels")),
            ("settlement", synthetic.SETTLEMENT_ID, ("nodes", "roads", "labels")),
            ("interior", synthetic.INTERIOR_ID, ("rooms", "connections", "exterior", "labels")),
        )
        self.partitioned()
        for view, map_id, layers in cases:
            identity = ["--view", view, *(["--map", map_id] if map_id else [])]
            camera = ["--width", "320", "--height", "240"]
            baseline = self.succeeded(*identity, *camera, "--output", self.out(f"{view}-all.webp"))
            baseline_pixels = decode_images(self.output / f"{view}-all.webp")[
                str(self.output / f"{view}-all.webp")
            ]["digest"]
            differing = 0
            for layer in layers:
                document = self.succeeded(
                    *identity, *camera, "--hide", layer, "--output", self.out(f"{view}-{layer}.webp")
                )
                self.assertEqual(document["hidden_layers"], [layer], layer)
                self.assertEqual(document["bounds"], baseline["bounds"], f"{layer}: the camera must not move")
                pixels = decode_images(self.output / f"{view}-{layer}.webp")[
                    str(self.output / f"{view}-{layer}.webp")
                ]["digest"]
                differing += pixels != baseline_pixels
            self.assertGreater(differing, 0, f"{view}: hiding layers must change the image")
            hidden = self.succeeded(
                *identity, *camera, "--hide", *layers, "--output", self.out(f"{view}-none.webp")
            )
            self.assertEqual(hidden["hidden_layers"], sorted(layers))
            self.assertEqual(hidden["bounds"], baseline["bounds"])
            self.assert_image(self.output / f"{view}-none.webp", hidden, image_format="webp")

    def test_repeated_hides_are_deduplicated_and_sorted(self):
        self.plain()
        document = self.succeeded(
            "--view", "settlement", "--map", synthetic.SETTLEMENT_ID,
            "--hide", "labels", "nodes", "--hide", "labels", "nodes",
            "--width", "320", "--height", "240", "--output", self.out("hidden.webp"),
        )
        self.assertEqual(document["hidden_layers"], ["labels", "nodes"])

    def test_replacing_an_existing_image_is_atomic_and_reports_the_new_one(self):
        self.plain()
        destination = self.output / "replace.webp"
        destination.write_bytes(b"a previous capture")

        document = self.succeeded(
            "--view", "settlement", "--map", synthetic.SETTLEMENT_ID,
            "--width", "320", "--height", "240", "--output", self.out("replace.webp"),
        )

        self.assertEqual(document["image_path"], str(destination))
        self.assertNotEqual(destination.read_bytes(), b"a previous capture")
        self.assert_image(destination, document, image_format="webp")
        self.assertEqual([path.name for path in self.output.iterdir()], ["replace.webp"])

    def test_relative_outputs_resolve_against_the_working_directory(self):
        self.plain()
        nested = self.workspace / "captures"
        nested.mkdir()

        document = self.succeeded(
            "--view", "settlement", "--map", synthetic.SETTLEMENT_ID,
            "--width", "320", "--height", "240", "--output", "captures/town.webp",
        )

        self.assertEqual(document["image_path"], str((nested / "town.webp").resolve()))
        self.assert_image(nested / "town.webp", document, image_format="webp")

    def test_a_non_ascii_destination_survives_an_ascii_stdout(self):
        self.plain()
        environment = harness.scrubbed_env()
        environment["PYTHONIOENCODING"] = "ascii"
        destination = self.out("地圖.webp")

        # Deliberately without `-I`: isolated mode ignores `PYTHONIOENCODING`,
        # which is exactly the condition under test. The environment is still
        # scrubbed in every other respect.
        result = subprocess.run(
            [
                str(capture_python()), str(SCRIPT),
                "--view", "settlement", "--map", synthetic.SETTLEMENT_ID,
                "--width", "320", "--height", "240", "--output", destination,
            ],
            cwd=self.workspace,
            env=environment,
            capture_output=True,
            text=True,
            timeout=300,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["image_path"], destination)
        self.assert_image(Path(destination), document, image_format="webp")

    def test_the_command_needs_no_node_runtime_and_no_editor_service(self):
        self.plain()
        environment = harness.scrubbed_env()
        # Nothing else can be resolved: no Node, pnpm or editor binary remains
        # on PATH, and no service is started by the capture.
        environment["PATH"] = ""

        document = self.succeeded(
            "--view", "settlement", "--map", synthetic.SETTLEMENT_ID,
            "--width", "320", "--height", "240", "--output", self.out("offline.webp"),
            env=environment,
        )

        self.assert_image(self.output / "offline.webp", document, image_format="webp")


# -- refusals ---------------------------------------------------------------


class CaptureRefusalTests(_CaptureCase):
    def test_bad_flags_and_identity_publish_nothing(self):
        self.plain()
        cases = (
            (("--view", "village", "--output", self.out("a.webp")), "invalid_argument"),
            (("--view", "settlement", "--output", self.out("a.webp")), "invalid_argument"),
            (("--view", "continent", "--map", synthetic.SETTLEMENT_ID, "--output", self.out("a.webp")), "invalid_argument"),
            (("--view", "settlement", "--map", synthetic.SETTLEMENT_ID, "--output", self.out("a.webp"), "--show", "nodes"), "invalid_argument"),
            (("--view", "settlement", "--map", synthetic.SETTLEMENT_ID, "--output", self.out("a.webp"), "--quality", "90"), "invalid_argument"),
            (("--view", "settlement", "--map", synthetic.SETTLEMENT_ID, "--output", self.out("a.webp"), "--service-url", "http://127.0.0.1:8765/"), "invalid_argument"),
            (("--view", "settlement", "--map", synthetic.SETTLEMENT_ID, "--output", self.out("a.webp"), "--format", "jpeg"), "invalid_argument"),
            (("--view", "settlement", "--map", synthetic.SETTLEMENT_ID, "--output", self.out("a.webp"), "--format", "avif"), "invalid_argument"),
        )
        for arguments, code in cases:
            with self.subTest(arguments=arguments):
                self.refused(*arguments, code=code)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_layers_are_view_scoped(self):
        self.plain()
        for view, map_id, layer in (
            ("settlement", synthetic.SETTLEMENT_ID, "rooms"),
            ("interior", synthetic.INTERIOR_ID, "roads"),
            ("continent", None, "roofs"),
        ):
            identity = ["--view", view, *(["--map", map_id] if map_id else [])]
            with self.subTest(view=view, layer=layer):
                self.refused(
                    *identity, "--output", self.out("a.webp"), "--hide", layer,
                    code="unknown_layer",
                )

    def test_bounds_and_dimensions_are_validated_before_rendering(self):
        self.plain()
        identity = ("--view", "settlement", "--map", synthetic.SETTLEMENT_ID, "--output", self.out("a.webp"))
        for bounds in (
            ("--bounds", "0", "0", "0", "10"),
            ("--bounds", "0", "0", "10", "-1"),
            ("--bounds", "nan", "0", "10", "10"),
            ("--bounds", "0", "inf", "10", "10"),
            ("--bounds", "0", "0", "10"),
        ):
            with self.subTest(bounds=bounds):
                self.refused(*identity, *bounds, code="invalid_argument")
        for dimensions in (("--width", "0"), ("--height", "-4"), ("--width", "12.5")):
            with self.subTest(dimensions=dimensions):
                self.refused(*identity, *dimensions, code="invalid_argument")
        self.assertEqual(list(self.output.iterdir()), [])

    def test_output_paths_are_validated_before_rendering(self):
        self.plain()
        identity = ("--view", "settlement", "--map", synthetic.SETTLEMENT_ID)
        (self.output / "folder.webp").mkdir()
        cases = (
            (("--output", self.out("a.png")), "invalid_output"),
            (("--output", self.out("a")), "invalid_output"),
            (("--output", str(self.root / "missing" / "a.webp")), "invalid_output"),
            (("--output", str(self.output / "folder.webp")), "invalid_output"),
        )
        for arguments, code in cases:
            with self.subTest(arguments=arguments):
                self.refused(*identity, *arguments, code=code)

    def test_map_identity_refusals_name_the_problem(self):
        self.plain()
        self.refused(
            "--view", "settlement", "--map", "no_such_map", "--output", self.out("a.webp"),
            code="unknown_map",
        )
        self.refused(
            "--view", "settlement", "--map", synthetic.INTERIOR_ID, "--output", self.out("a.webp"),
            code="wrong_view",
        )
        self.refused(
            "--view", "interior", "--map", synthetic.SETTLEMENT_ID, "--output", self.out("a.webp"),
            code="wrong_view",
        )
        self.assertEqual(list(self.output.iterdir()), [])

    def test_partition_refusals_explain_regenerate_or_hide(self):
        missing = self.plain()
        stderr = self.refused(
            "--view", "continent", "--output", self.out("a.webp"),
            code="partition_unavailable", contains="missing",
        )
        self.assertIn("--hide partition", stderr)
        self.assertIn("regenerate_partition.py", stderr)
        # Hiding the layer is the documented way to capture without it.
        hidden = self.succeeded("--view", "continent", "--hide", "partition", "--output", self.out("hidden.webp"))
        self.assertEqual(hidden["hidden_layers"], ["partition"])

        malformed = self.partitioned()
        (malformed / ARTIFACT).write_text("not a partition document", encoding="utf-8")
        self.refused("--view", "continent", "--output", self.out("b.webp"), code="partition_unavailable", contains="malformed")

        stale = self.partitioned()
        settlement = stale / SETTLEMENT
        data = synthetic.settlement_data()
        data["nodes"]["yard"]["key"] = "Renamed yard"
        settlement.write_text(synthetic.yaml_text(data), encoding="utf-8")
        self.refused("--view", "continent", "--output", self.out("c.webp"), code="partition_unavailable", contains="stale")
        # Settlement and interior captures never open the artifact.
        self.succeeded(
            "--view", "settlement", "--map", synthetic.SETTLEMENT_ID,
            "--width", "320", "--height", "240", "--output", self.out("settlement.webp"),
        )
        self.assertEqual(sorted(path.name for path in self.output.iterdir()), ["hidden.webp", "settlement.webp"])

    def test_structural_source_errors_refuse_the_capture(self):
        root = self.plain()
        (root / DOCUMENTS[1]).write_text("locations: [not: yaml", encoding="utf-8")

        stderr = self.refused(
            "--view", "settlement", "--map", synthetic.SETTLEMENT_ID, "--output", self.out("a.webp"),
            code="structure",
        )
        self.assertTrue(stderr.strip())
        self.assertEqual(list(self.output.iterdir()), [])

    def test_a_failed_render_preserves_an_existing_image(self):
        self.plain()
        destination = self.output / "existing.webp"
        previous = b"an image from an earlier invocation"
        destination.write_bytes(previous)

        # The interior cards cannot fit 80x80 pixels: the entry refuses the
        # automatic fit, so nothing is published.
        stderr = self.refused(
            "--view", "interior", "--map", synthetic.INTERIOR_ID,
            "--width", "80", "--height", "80", "--output", self.out("existing.webp"),
            code="render_failed",
        )
        self.assertIn("does not fit", stderr)
        self.assertEqual(destination.read_bytes(), previous)
        self.assertEqual([path.name for path in self.output.iterdir()], ["existing.webp"])

    def test_a_refusal_after_a_success_still_reports_no_output(self):
        self.plain()
        self.succeeded(
            "--view", "settlement", "--map", synthetic.SETTLEMENT_ID,
            "--width", "320", "--height", "240", "--output", self.out("first.webp"),
        )
        published = _sha(self.output / "first.webp")

        self.refused("--view", "settlement", "--map", "no_such_map", "--output", self.out("first.webp"), code="unknown_map")

        self.assertEqual(_sha(self.output / "first.webp"), published)

    def test_help_exits_zero_without_rendering(self):
        result = self.run_capture("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--view", result.stdout)
        self.assertIn("--hide", result.stdout)
        self.assertEqual(list(self.output.iterdir()), [])


class CaptureReadOnlyTests(_CaptureCase):
    def test_sources_layouts_partition_and_index_are_never_modified(self):
        root = synthetic.write_partitionable_workspace(self.workspace)
        install_partition(root)
        synthetic.write_reference_context(root)
        layout = root / f"content/map-editor-layouts/{synthetic.INTERIOR_ID}.yaml"
        layout.parent.mkdir(parents=True, exist_ok=True)
        layout.write_text(
            synthetic.yaml_text({"version": 1, "kind": "layout", "id": synthetic.INTERIOR_ID, "positions": {"front": {"x": 0, "y": 0}}}),
            encoding="utf-8",
        )
        before = synthetic.tree_digest(root)
        self.assertIn(ARTIFACT, before)
        self.assertIn("content/map-reference-context.json", before)

        self.succeeded("--view", "continent", "--width", "320", "--height", "240", "--output", self.out("continent.webp"))
        self.succeeded(
            "--view", "settlement", "--map", synthetic.SETTLEMENT_ID,
            "--width", "320", "--height", "240", "--output", self.out("settlement.webp"),
        )
        self.succeeded(
            "--view", "interior", "--map", synthetic.INTERIOR_ID,
            "--width", "320", "--height", "240", "--output", self.out("interior.webp"),
        )
        self.refused("--view", "settlement", "--map", "no_such_map", "--output", self.out("refused.webp"))

        self.assertEqual(synthetic.tree_digest(root), before)


if __name__ == "__main__":
    unittest.main()
