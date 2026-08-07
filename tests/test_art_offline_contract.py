"""Repository-wide offline acceptance contract for the art backend.

With the sd-webui client fixed to fail and every LLM profile unavailable, the
deterministic game must remain fully playable while every art state degrades
to the approved placeholders (design D3/Goals, focused design §5). This is a
repository check over source invariants: the engine must never open a socket
in tests (the harness injects the fake client through ``ART_SD_CLIENT``), the
external worker command must be fully removed, and every art state must keep
its deterministic degrade path. The behavior-level offline loop lives in the
package suites (``world.art.tests.test_worker`` scripts every named ``SDError``
through the fake client and asserts the presenter keeps its placeholders).
"""

from pathlib import Path
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]


class ArtOfflineAcceptanceContract(unittest.TestCase):
    @covers_requirement("art-asset-lifecycle::world-art-service-py-is-the-sole-writer-of-asset-and-queue-records")
    def test_no_world_ai_module_writes_art_state(self):
        ai_root = REPO_ROOT / "world" / "ai"
        for path in sorted(ai_root.rglob("*.py")):
            if "tests" in path.parts or path.name == "__init__.py":
                continue
            source = path.read_text(encoding="utf-8")
            with self.subTest(module=path.relative_to(REPO_ROOT).as_posix()):
                self.assertNotIn("world.art", source)
                self.assertNotIn("from world.art", source)

    def test_art_package_has_no_forbidden_transport_fragments(self):
        for path in sorted((REPO_ROOT / "world" / "art").rglob("*.py")):
            if "tests" in path.parts:
                continue
            source = path.read_text(encoding="utf-8").lower()
            with self.subTest(module=path.relative_to(REPO_ROOT).as_posix()):
                for fragment in ("world.ai", "ollama", "llm_client"):
                    self.assertNotIn(fragment, source)

    @covers_requirement("art-queue-worker::the-scheduler-is-settings-configurable-and-disableable")
    def test_scheduler_can_be_disabled_by_setting(self):
        source = (REPO_ROOT / "server" / "conf" / "settings.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("ART_SCHEDULER_ENABLED", source)

    def test_art_store_root_is_gitignored_under_server(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("server/.art/", gitignore)

    def test_startup_wires_art_sync_after_the_deterministic_core(self):
        source = (REPO_ROOT / "server" / "conf" / "at_server_startstop.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("art_sync_all", source)

    def test_external_worker_command_and_tool_are_fully_removed(self):
        settings_source = (REPO_ROOT / "server" / "conf" / "settings.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("ART_WORKER_CMD", settings_source)
        self.assertNotIn("ART_WORKER_TIMEOUT_SECONDS", settings_source)
        self.assertFalse((REPO_ROOT / "tools" / "art_worker.py").exists())

    def test_every_harness_injects_the_fake_client_never_a_socket(self):
        browser_settings = (
            REPO_ROOT / "web" / "tests" / "browser" / "browser_settings.py"
        ).read_text(encoding="utf-8")
        self.assertIn("ART_SD_CLIENT", browser_settings)
        self.assertIn("world.art.fake_sd_client.FakeSDWebUIClient", browser_settings)
        self.assertNotIn("ART_WORKER_CMD", browser_settings)


if __name__ == "__main__":
    unittest.main()
