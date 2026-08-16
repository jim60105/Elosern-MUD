"""Scene-builder repository boundary tests (offline invariants).

Covers ``SceneBuilderBoundaryTests``: the deterministic-path ban, the
no-generative-import scan, the registry write-domain, the no-startup-resync
guard, and the no-live-client construction guard. All checks read the
repository from disk and never boot Evennia.
"""
import unittest

from tools.spec_traceability import covers_requirement

class SceneBuilderBoundaryTests(unittest.TestCase):
    @covers_requirement("scene-builder::scenebuilder-is-the-deterministic-requirements-to-spawn-materialization-layer")
    def test_scene_builder_module_stays_inside_the_deterministic_path_ban(self):
        import pathlib

        from world.quests import scene_builder

        source = pathlib.Path(scene_builder.__file__).read_text(encoding="utf-8").lower()
        for fragment in ("world.ai", "ollama", "llm_client"):
            self.assertNotIn(fragment, source)

    @covers_requirement("scene-builder::scenebuilder-is-the-deterministic-requirements-to-spawn-materialization-layer")
    def test_no_generative_module_imports_the_scene_builder(self):
        import ast
        from pathlib import Path

        ai_root = Path(__file__).resolve().parents[3] / "world" / "ai"
        for module_path in sorted(ai_root.rglob("*.py")):
            if "tests" in module_path.parts or "__init__.py" in module_path.parts:
                continue
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and "scene_builder" in node.module:
                    self.fail(f"{module_path} imports {node.module}")

    @covers_requirement("scene-builder::every-scene-builder-test-runs-offline-and-the-boundary-invariants-stay-green")
    def test_requirements_registry_is_written_only_by_the_compile_boundary(self):
        import pathlib

        repo = pathlib.Path(__file__).resolve().parents[3]
        writers = []
        for path in sorted((repo / "world").rglob("*.py")):
            if "tests" in path.parts:
                continue
            if "SCENE_REQUIREMENT_REGISTRY" in path.read_text(encoding="utf-8"):
                writers.append(path.relative_to(repo).as_posix())
        self.assertEqual(writers, ["world/quests/compile.py"])

    @covers_requirement("scene-builder::every-scene-builder-test-runs-offline-and-the-boundary-invariants-stay-green")
    def test_no_startup_resync_populates_generated_requirements(self):
        import pathlib

        repo = pathlib.Path(__file__).resolve().parents[3]
        source = (repo / "server" / "conf" / "at_server_startstop.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("SCENE_REQUIREMENT_REGISTRY", source)
        self.assertNotIn("scene_builder", source)

    @covers_requirement("scene-builder::every-scene-builder-test-runs-offline-and-the-boundary-invariants-stay-green")
    def test_scene_builder_and_service_tests_never_construct_the_live_client(self):
        import pathlib

        repo = pathlib.Path(__file__).resolve().parents[3]
        for relative in (
            "world/quests/tests/test_scene_builder.py",
            "server/conf/tests/test_ai_director_service.py",
        ):
            source = (repo / relative).read_text(encoding="utf-8")
            client_constructor = "OpenAICompatClient" + "("
            socket_import = "import so" + "cket"
            socket_from = "from so" + "cket"
            self.assertNotIn(client_constructor, source, relative)
            self.assertNotIn(socket_import, source, relative)
            self.assertNotIn(socket_from, source, relative)
if __name__ == "__main__":
    unittest.main()
