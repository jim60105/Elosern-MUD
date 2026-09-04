"""Evidence bridge: run the DOM-independent Node suite and the Vue Vitest
component suite as requirement evidence.

The client state-reduction and keyboard-routing contracts are implemented and
verified in DOM-independent JavaScript. ``covers_requirement`` can only attach
to a Python ``test_*`` function, so this module executes the Node suite (and,
for the choice-point requirements re-pointed to the Vue layer, the Vitest
component files) and asserts every test passes; the annotation then links the
main-spec requirement to a substantively matching, executed evidence record.
"""

from pathlib import Path
import subprocess
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_GLOB = REPO_ROOT / "web/static/webclient/js/tests" / "*.test.js"


class NodeSuiteEvidenceTest(unittest.TestCase):
    @covers_requirement(
        "webclient-desktop-shell::client-state-reduction-is-strict-and-atomic"
    )
    def test_protocol_reducer_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/protocol.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "protocol reducer Node suite failed:\n"
            + result.stdout
            + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe"
    )
    def test_keyboard_router_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/keyboard_router.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "keyboard router Node suite failed:\n"
            + result.stdout
            + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_actions_client_node_suite_passes(self):
        # The legacy `actions.test.js` Node file was retired with the Vue
        # migration (D1); the command-drawer ordinary-text contract is now
        # covered by the re-pointed `ui_contract.test.js`.
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/ui_contract.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "command-drawer text-contract Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel"
    )
    def test_service_menu_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/service_menu.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "service-menu Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-narrative-markup::the-narrative-renders-the-transport-stream-through-a-strict-allowlist-markup-pipeline",
        "webclient-narrative-markup::anything-outside-the-allowlist-degrades-to-visible-literal-text",
        "webclient-narrative-markup::anchors-degrade-to-their-text-content",
    )
    def test_narrative_markup_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/narrative_markup.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "narrative markup Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-pointer-activation::every-action-dock-surface-renders-exactly-the-keyboard-router-s-current-menu-frame",
        "webclient-pointer-activation::the-action-dock-is-a-single-composite-widget-that-cannot-double-activate",
    )
    def test_dock_surface_node_suite_passes(self):
        # The legacy `dock_surface.test.js` Node file was retired with the Vue
        # migration (D1); the pointer-activation / dock-surface menu-frame
        # contract is now covered by `keyboard_router.test.js`.
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/keyboard_router.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "keyboard-router Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-pointer-activation::pointer-activation-traverses-the-identical-path-as-keyboard-confirmation"
    )
    def test_keyboard_router_pointer_confirmation_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/keyboard_router.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "keyboard router Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control",
        "webclient-desktop-shell::theme-and-controls-remain-accessible",
    )
    def test_ui_contract_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/ui_contract.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "UI contract Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus"
    )
    def test_exploration_menu_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/exploration_menu.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "exploration-menu Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone"
    )
    def test_local_map_lattice_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/local_map.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "local-map Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-options-surface::one-shared-card-component-renders-every-suggestion-card"
    )
    def test_option_cards_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/option_cards.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "option-cards Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-options-surface::the-exploration-dock-renders-the-suggestions-section-from-the-validated-v5-panel",
        "webclient-options-surface::a-degraded-payload-with-zero-cards-renders-the-defined-empty-state",
    )
    def test_options_view_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/options_view.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "options-view Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-context-actions-suggestions::the-dock-suggestion-pane-is-the-single-suggestion-surface",
    )
    def test_choicepoint_node_suite_passes(self):
        # The suggestions behavior lives in the action dock: generating,
        # ready, degraded, and transport-reset all render exclusively in
        # the dock suggestion pane (action_dock.test.js).
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/action/action_dock.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "choice-point Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-contextual-hud::narrative-lines-carry-the-reference-s-semantic-classes",
    )
    def test_choicepoint_block_node_suite_passes(self):
        # The narrative feed semantic line styling (sys lines with seal ◈ marker,
        # gold emphasis, plain serif lines) and full-log parity render
        # through narrative_feed.test.js and full_log_overlay.test.js.
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/narrative_feed.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/full_log_overlay.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "choice-point block Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


if __name__ == "__main__":
    unittest.main()
