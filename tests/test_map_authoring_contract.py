"""Contract test: authoring documents load and compile in the pure core.

The package-level mechanism tests live in ``packages/map-core/tests``. This
repository-level check establishes the consumer boundary:

* the installed distribution and both locks expose the restricted YAML
  dependency, and the game environment resolves the package;
* schema, parsing, discovery, authoring load, diagnostics and runtime
  compilation all run in an interpreter where Evennia, Django, ``world`` and
  ``typeclasses`` cannot be imported, with no import-time filesystem writes;
* the real read-only inspection entry point exposes the schema and loads a
  workspace without modifying it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "packages" / "map-core"
sys.path.insert(0, str(PACKAGE_ROOT / "tests"))

import authoring_fixtures as fixtures  # noqa: E402

ISOLATED_AUTHORING = textwrap.dedent(
    """
    import json
    import sys
    from pathlib import Path

    FORBIDDEN = {"evennia", "django", "twisted", "world", "typeclasses"}

    class Blocker:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in FORBIDDEN:
                raise AssertionError(f"map core imported forbidden namespace {name}")
            return None

    sys.meta_path.insert(0, Blocker())
    sys.path.insert(0, sys.argv[1])

    loaded = {name.split(".")[0] for name in sys.modules}
    assert not (FORBIDDEN & loaded), sorted(FORBIDDEN & loaded)

    from elosern_map_core import (
        AuthoritativeExternalResult,
        PartitionFreshness,
        compile_runtime,
        diagnose_world,
        load_authoring_world,
        make_source_document,
        parse_document,
        schema,
    )

    payload = json.load(sys.stdin)
    documents = tuple(
        make_source_document(path, text)
        for path, text in sorted(payload.items())
    )
    parsed = parse_document(
        "content/maps/settlements/demo_map.yaml",
        payload["content/maps/settlements/demo_map.yaml"],
    )
    world = load_authoring_world(documents)
    diagnostics = diagnose_world(world)
    snapshot = compile_runtime(
        world,
        AuthoritativeExternalResult(1, "evidence", world.fingerprint, True),
        PartitionFreshness(1, world.partition_signature, True),
    )
    print(
        json.dumps(
            {
                "schema_version": schema()["version"],
                "kinds": sorted(schema()["document_kinds"]),
                "parsed_identity": parsed.identity,
                "diagnostic_codes": [item.code for item in diagnostics],
                "settlements": sorted(snapshot.settlements),
                "provenance_paths": sorted(parsed.provenance),
                "cwd_entries": sorted(item.name for item in Path.cwd().iterdir()),
            }
        )
    )
    """
)


def _run_isolated(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", "-c", ISOLATED_AUTHORING, str(PACKAGE_ROOT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=tempfile.mkdtemp(),
        timeout=120,
    )


def _package_lock_names() -> set[str]:
    lock = tomllib.loads((PACKAGE_ROOT / "uv.lock").read_text())
    return {entry["name"] for entry in lock["package"]}


def _root_lock_entry() -> dict:
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text())
    entries = [
        entry
        for entry in lock["package"]
        if entry["name"] == "elosern-map-core"
    ]
    assert len(entries) == 1
    return entries[0]


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


class InstalledDistributionTests(unittest.TestCase):
    def test_the_game_environment_resolves_the_locked_package(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                "import importlib.metadata as m; import elosern_map_core as c;"
                "print(m.version('elosern-map-core')); print(c.__name__)",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.split(), ["0.1.0", "elosern_map_core"])

    def test_both_locks_declare_the_restricted_yaml_dependency(self):
        self.assertIn("ruamel-yaml", _package_lock_names())
        entry = _root_lock_entry()
        self.assertIn(
            "ruamel-yaml",
            {dependency["name"] for dependency in entry.get("dependencies", [])},
        )
        project = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text())
        self.assertTrue(
            any(
                requirement.startswith("ruamel-yaml")
                for requirement in project["project"]["dependencies"]
            )
        )


class AuthoringBoundaryTests(unittest.TestCase):
    def test_authoring_runs_with_evennia_django_and_world_absent(self):
        payload = {
            source.relative_path: source.text
            for source in fixtures.source_documents()
        }
        completed = _run_isolated(payload)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        observed = json.loads(completed.stdout)

        self.assertEqual(observed["schema_version"], 1)
        self.assertIn("settlement", observed["kinds"])
        self.assertEqual(observed["parsed_identity"], "demo_map")
        self.assertEqual(observed["diagnostic_codes"], [])
        self.assertEqual(observed["settlements"], ["demo_map"])
        self.assertIn("nodes.plaza.x_m", observed["provenance_paths"])
        # Importing and running the authoring core wrote nothing to the cwd.
        self.assertEqual(observed["cwd_entries"], [])


class InspectionEntryPointTests(unittest.TestCase):
    def test_schema_command_exposes_the_machine_readable_domain_schema(self):
        completed = subprocess.run(
            [sys.executable, "-I", "-m", "elosern_map_core", "schema"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["version"], 1)
        self.assertEqual(
            set(document["document_kinds"]),
            {
                "continent",
                "locations",
                "districts",
                "settlement",
                "interior",
                "layout",
            },
        )
        node_fields = document["document_kinds"]["settlement"]["fields"]["nodes"][
            "items"
        ]["fields"]
        self.assertIn("prototype_parent", node_fields)
        self.assertIn("anchor_key", node_fields)

    def test_inspect_loads_a_workspace_without_modifying_it(self):
        workspace = Path(tempfile.mkdtemp())
        for document in fixtures.source_documents():
            path = workspace / document.relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(document.text, encoding="utf-8")
        before = _tree_digest(workspace)

        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-m",
                "elosern_map_core",
                "inspect",
                str(workspace),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        observed = json.loads(completed.stdout)
        self.assertEqual(observed["status"], "loaded")
        self.assertEqual(observed["diagnostics"], [])
        self.assertTrue(observed["semantic_ready"])
        self.assertIsNone(observed["runtime_ready"])
        self.assertEqual(
            [entry["relative_path"] for entry in observed["documents"]],
            sorted(
                entry["relative_path"]
                for entry in observed["documents"]
            ),
        )
        self.assertIn(
            "content/maps/settlements/demo_map.yaml",
            {entry["relative_path"] for entry in observed["documents"]},
        )
        self.assertEqual(_tree_digest(workspace), before)


if __name__ == "__main__":
    unittest.main()
