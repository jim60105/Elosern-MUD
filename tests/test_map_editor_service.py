"""The standalone map editor service, driven as a real separate process.

Each test launches ``python -m elosern_map_editor`` from the editor's own
locked environment (``tools/map-editor``) with a scrubbed environment and no
``PATH``, against a temporary synthetic workspace (or, for the read-only load
check, the repository checkout), and asserts effects over real HTTP: no game
framework in that interpreter, rejected foreign/unauthenticated/oversized
requests that leave the files and revision unchanged, refused escaping links,
and an old session's token rejected after a restart.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parent.parent
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"


def _load(name: str):
    import importlib.util
    import sys

    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, EDITOR_TESTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


harness = _load("process_harness")
synthetic = _load("synthetic_workspace")


class _EditorCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            harness.editor_python()
        except harness.EditorUnavailable as error:
            if not harness.skip_allowed():
                raise
            raise unittest.SkipTest(f"standalone editor environment unavailable: {error}") from error

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="map-editor-wrapper-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.workspace = synthetic.write_workspace(self.root / "workspace")


class EditorEnvironmentTests(_EditorCase):
    @covers_requirement("map-editor-service::editor-runs-without-game-services-or-dependencies")
    def test_the_editor_interpreter_has_no_game_framework_or_game_modules(self):
        code = (
            "import importlib.util, json, sys\n"
            "from elosern_map_editor.app import create_app, service_of\n"
            "from elosern_map_editor.config import EditorConfig\n"
            "import elosern_map_core\n"
            f"service = service_of(create_app(EditorConfig(workspace_root={str(self.workspace)!r})))\n"
            "print(json.dumps({\n"
            "  'specs': {name: importlib.util.find_spec(name) is not None for name in ('evennia', 'django', 'world', 'typeclasses')},\n"
            "  'loaded': sorted(m for m in sys.modules if m.split('.')[0] in ('evennia', 'django', 'world', 'typeclasses', 'commands', 'server', 'web')),\n"
            "  'core': elosern_map_core.__file__,\n"
            "  'preview': service.preview_state,\n"
            "}))\n"
        )
        result = harness.run_editor_python(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["specs"], {"evennia": False, "django": False, "world": False, "typeclasses": False})
        self.assertEqual(report["loaded"], [])
        self.assertEqual(
            Path(report["core"]).resolve().parent,
            (REPO_ROOT / "packages/map-core/elosern_map_core").resolve(),
        )
        self.assertEqual(report["preview"], "current")


class EditorHttpBoundaryTests(_EditorCase):
    @covers_requirement("map-editor-service::local-api-confines-and-authorizes-workspace-access")
    def test_foreign_unauthenticated_and_oversized_requests_change_nothing(self):
        before = synthetic.tree_digest(self.workspace)
        with harness.EditorProcess(self.workspace) as editor:
            session = editor.session()
            revision = editor.workspace_state()["snapshot_revision"]
            status, body = editor.request("GET", "/api/workspace", headers={"Host": "rebind.example.invalid"})
            self.assertEqual((status, body["error"]["code"]), (403, "forbidden_host"))
            status, body = editor.request("GET", "/api/session", headers={"Origin": "http://localhost:1"})
            self.assertEqual((status, body["error"]["code"]), (403, "forbidden_origin"))
            status, body = editor.reload(session["token"], session["session_generation"], Origin="http://evil.example.invalid")
            self.assertEqual((status, body["error"]["code"]), (403, "forbidden_origin"))
            status, body = editor.reload(None, session["session_generation"])
            self.assertEqual((status, body["error"]["code"]), (401, "unauthorized"))
            status, body = editor.request(
                "POST",
                "/api/reload",
                headers={
                    "Origin": editor.origin,
                    "X-Map-Editor-Token": session["token"],
                    "Content-Type": "application/json",
                },
                body=json.dumps({"session_generation": session["session_generation"], "pad": "x" * 200_000}),
            )
            self.assertEqual((status, body["error"]["code"]), (413, "body_too_large"))
            status, _ = editor.request("GET", "/assets/../../../pyproject.toml")
            self.assertEqual(status, 404)
            self.assertEqual(editor.workspace_state()["snapshot_revision"], revision)
        self.assertEqual(synthetic.tree_digest(self.workspace), before)

    @covers_requirement("map-editor-service::local-api-confines-and-authorizes-workspace-access")

    def test_an_escaping_linked_source_is_refused_and_its_target_never_served(self):
        outside = self.root / "outside.yaml"
        outside.write_text("OUTSIDE-MARKER: true\n", encoding="utf-8")
        target = self.workspace / f"content/maps/settlements/{synthetic.SETTLEMENT_ID}.yaml"
        target.unlink()
        target.symlink_to(outside)
        with harness.EditorProcess(self.workspace) as editor:
            state = editor.workspace_state()
        self.assertEqual(state["preview_state"], "unavailable")
        self.assertTrue(state["write_pause"]["paused"])
        self.assertIn(
            ("content/maps/settlements/synthetic_town.yaml", "unsafe_source_path"),
            {(item["relative_path"], item["code"]) for item in state["candidate_diagnostics"]},
        )
        self.assertNotIn("OUTSIDE-MARKER", json.dumps(state))

    def test_an_old_session_token_is_rejected_after_a_restart(self):
        port = harness.free_port()
        with harness.EditorProcess(self.workspace, port=port) as editor:
            old = editor.session()
        with harness.EditorProcess(self.workspace, port=port) as editor:
            new = editor.session()
            self.assertNotEqual(new["session_generation"], old["session_generation"])
            status, body = editor.reload(old["token"], old["session_generation"])
            self.assertEqual((status, body["error"]["code"]), (401, "unauthorized"))
            self.assertEqual(editor.workspace_state()["snapshot_revision"], 1)
            status, body = editor.reload(new["token"], new["session_generation"])
            self.assertEqual((status, body["changed"]), (200, False))


class RepositoryWorkspaceTests(_EditorCase):
    def test_the_repository_world_loads_read_only_with_disk_fingerprints(self):
        with harness.EditorProcess(REPO_ROOT) as editor:
            state = editor.workspace_state()
        self.assertEqual(state["preview_state"], "current")
        self.assertEqual(state["write_pause"], {"paused": False, "reason": None})
        self.assertTrue(state["documents"])
        for document in state["documents"]:
            digest = hashlib.sha256((REPO_ROOT / document["relative_path"]).read_bytes()).hexdigest()
            self.assertEqual(document["fingerprint"], digest, document["relative_path"])


if __name__ == "__main__":
    unittest.main()
