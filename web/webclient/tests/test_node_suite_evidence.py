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
import os
import subprocess
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_GLOB = REPO_ROOT / "web/static/webclient/js/tests" / "*.test.js"

# The two evidence helpers below read Vitest's own summary lines ("Test Files
# 1 passed (1)", "Tests N passed (N)"). Vitest enables colour as soon as `CI`
# exists in the environment (tinyrainbow's rule), which every GitHub runner
# sets, and the counts then carry ANSI escapes no plain-text regex matches.
# NO_COLOR is the runner-independent way to ask for the plain form.
_VITEST_ENV = {**os.environ, "NO_COLOR": "1"}


class NodeSuiteEvidenceTest(unittest.TestCase):
    @covers_requirement(
        "webclient-desktop-shell::client-state-reduction-is-strict-and-atomic"
    )
    def test_protocol_reducer_node_suite_passes(self):
        # Every protocol_*.test.js sibling is evidence; node --test silently
        # ignores a missing path whenever another path resolves.
        suite = sorted(
            str(path)
            for path in (REPO_ROOT / "web/static/webclient/js/tests").glob(
                "protocol_*.test.js"
            )
        )
        self.assertTrue(suite, "no protocol reducer Node siblings discovered")
        result = subprocess.run(
            ["node", "--test", *suite],
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
        "webclient-immutable-presentation::ordinary-committed-notifications-reuse-immutable-unchanged-payloads",
        "webclient-immutable-presentation::explicit-detached-snapshots-retain-isolation",
    )
    def test_immutable_committed_record_node_suite_passes(self):
        # The ownership contract (webclient-immutable-adoption): a delta keeps
        # the unchanged eager panel by === identity while replacing the changed
        # one, a metadata-only notification and an equal alignment reuse the
        # already owned panel values, a hostile subscriber in either strictness
        # and a mutation of the transport caller's own envelope or result graph
        # cannot reach the committed record, a listener's retained old record
        # stays the earlier committed state, and one notification is published
        # per complete publication (none for a pending part). getState()
        # snapshots are edited and retained without touching either the reducer
        # or a later commit, and same-epoch map references survive an eager
        # snapshot.
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/protocol_immutable.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "immutable committed record Node suite failed:\n"
            + result.stdout
            + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-immutable-presentation::complete-alignment-preserves-valid-local-interaction-state",
        "webclient-immutable-presentation::ordinary-committed-notifications-reuse-immutable-unchanged-payloads",
    )
    def test_immutable_presentation_vitest_evidence_passes(self):
        # What only the composed client shows (webclient-immutable-adoption):
        # the view projects the committed panels by reference and keeps the
        # unchanged ones by identity across a delta, subscribers and the getter
        # see one frozen record, a hostile consumer cannot write through the
        # published view or a resolved menu, a complete same-mode alignment
        # keeps the open drawer, the focused field and its unsaved text without
        # remounting, the existing mode-change and unavailable-backing-panel
        # teardown still runs, and an equal checkpoint replays neither a settled
        # dialogue delivery nor a completed combat round.
        self._run_single_vitest_file(
            "web/webclient-app/tests/immutable_presentation.test.js",
            "immutable presentation",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-vitals-island-is-shown-only-in-combat-or-while-a-vital-or-a-condition-needs-attention",
    )
    def test_vitals_visibility_node_suite_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/data/vitals_visibility.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/data/status_panel.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "vitals-visibility Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe",
        "webclient-room-actions::the-exploration-screen-roots-at-the-compass-the-rail-and-room-actions"
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
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow"
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
    @covers_requirement(
        "webclient-service-menus::board-offers-carry-structured-facts-from-the-canonical-seams"
    )
    def test_services_panel_node_suite_passes(self):
        suite = [
            str(REPO_ROOT / "web/static/webclient/js/tests/protocol_services_a.test.js"),
            str(REPO_ROOT / "web/static/webclient/js/tests/protocol_services_b.test.js"),
        ]
        result = subprocess.run(
            [
                "node",
                "--test",
                *suite,
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "services-panel Node suite failed:\n" + result.stdout + result.stderr,
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
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow",
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
        "webclient-desktop-shell::the-top-navigation-bar-carries-the-tool-group",
    )
    def test_desktop_navigation_node_suite_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/desktop_navigation.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "desktop-navigation Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-room-actions::the-exploration-screen-roots-at-the-compass-the-rail-and-room-actions"
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
        "webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure"
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
        "webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel"
    )
    def test_local_map_gateway_contract_node_suites_pass(self):
        # The browser half of the exact node contract: the client validator's
        # required gateway field (protocol_local_map.test.js) and the model's
        # unchanged gateway pass-through (local_map.test.js). Each file is
        # listed explicitly and checked to exist, since node --test silently
        # ignores a missing path whenever another path resolves.
        suite = [
            REPO_ROOT / "web/static/webclient/js/tests/protocol_local_map.test.js",
            REPO_ROOT / "web/static/webclient/js/tests/local_map.test.js",
        ]
        for path in suite:
            self.assertTrue(path.is_file(), f"missing Node suite {path}")
        result = subprocess.run(
            ["node", "--test", *(str(path) for path in suite)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "local-map gateway contract Node suites failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("requires exact gateway metadata", result.stdout)
        self.assertIn("passes node gateway metadata through unchanged", result.stdout)

    @covers_requirement(
        "webclient-local-map::island-projection-selects-a-metric-scale-for-one-hop-exits",
        "webclient-local-map::island-projection-compresses-extreme-exit-distances-monotonically",
        "webclient-local-map::island-projection-handles-sparse-and-coincident-nodes-deterministically",
        "webclient-local-map::island-projection-separates-gateway-stubs-from-node-scale",
        "webclient-local-map::island-background-describes-the-selected-distance-mapping",
        "webclient-local-map::the-wilderness-payload-legend-states-the-cell-scale-from-the-provider-constant",
    )
    def test_minimap_projection_vitest_evidence_passes(self):
        # The pure island projection (minimap_projection.js): ladder and
        # worked examples, hysteresis with the map-key reset helper, strict
        # compression boundaries and the logarithmic mapping, zero/no-exit
        # inputs, bounded overlap spreading, cross-layer gate stubs, and the
        # dot/ring background. The wilderness-legend requirement is matched
        # only by its island clause: the 3x3 case converts one-kilometre cell
        # deltas to metres (radii 50 and 70.7 at level 2000) without reading
        # the legend or rewriting payload coordinates; the presenter's scale
        # note and patchability stay pinned by the Python presenter tests.
        suite = REPO_ROOT / "web/webclient-app/tests/minimap_projection.test.js"
        self.assertTrue(suite.is_file(), f"missing Vitest file {suite}")
        result = subprocess.run(
            ["npx", "--no-install", "vitest", "run", str(suite)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env=_VITEST_ENV,
        )
        self.assertEqual(
            result.returncode,
            0,
            "minimap projection Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        # Exactly the one file ran, and every case in it passed.
        self.assertRegex(result.stdout, r"Test Files\s+1 passed \(1\)")
        # The return code already covers failures; pin that nothing was
        # skipped or left as a todo.
        self.assertRegex(result.stdout, r"Tests\s+\d+ passed \(\d+\)")
        self.assertNotRegex(result.stdout, r"\d+ (skipped|todo)")

    @covers_requirement(
        "webclient-local-map::the-minimap-island-draws-the-area-map-s-node-glyphs",
        "webclient-local-map::an-island-fallback-label-never-covers-its-own-node-glyph",
    )
    def test_island_shared_glyph_vitest_evidence_passes(self):
        # The island draws MapNodeGlyph inside one group at the island glyph
        # scale (lattice independent of markerScale, graph times it), its
        # footprints, spreading, label clearance, stub start and aim ring
        # follow that one constant, the current gate room wears the here
        # seal, and a raster-fallback label never lands on its own marker.
        suite = [
            REPO_ROOT / "web/webclient-app/tests/world/map_lattice_renderer.test.js",
            REPO_ROOT / "web/webclient-app/tests/world/local_map.test.js",
            REPO_ROOT / "web/webclient-app/tests/minimap_projection.test.js",
            REPO_ROOT / "web/webclient-app/tests/world/island_labels.test.js",
        ]
        for path in suite:
            self.assertTrue(path.is_file(), f"missing Vitest file {path}")
        result = subprocess.run(
            ["npx", "--no-install", "vitest", "run", "--reporter=verbose", *(str(path) for path in suite)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env=_VITEST_ENV,
        )
        self.assertEqual(
            result.returncode,
            0,
            "island shared-glyph Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertRegex(result.stdout, r"Test Files\s+4 passed \(4\)")
        self.assertNotRegex(result.stdout, r"\d+ (skipped|todo)")
        for name in (
            "the minimap island draws the area map's node glyphs > draws the lattice glyph group at the island scale, whatever markerScale",
            "the minimap island draws the area map's node glyphs > draws the graph glyph group at the island scale times markerScale",
            "the minimap island draws the area map's node glyphs > starts a gateway stub at the scaled travel halo's edge",
            "the minimap island draws the area map's node glyphs > keeps the aim ring's inner stroke edge outside the scaled travel halo",
            "the minimap island draws the area map's node glyphs > rescales glyph, footprint, label clearance, stub start and aim ring from the one constant",
            "the minimap island draws the area map's node glyphs > holds no island marker-ladder paint of its own",
            "draws the current gate room's here seal, room name and 通往 line on the city side",
            "scales the base footprints uniformly by the glyph size",
            "an island fallback label never covers its own node glyph > skips a raster box inside its own footprint plus the label gap",
        ):
            self.assertIn(name, result.stdout)

    def _run_single_vitest_file(self, relative: str, label: str) -> None:
        suite = REPO_ROOT / relative
        self.assertTrue(suite.is_file(), f"missing Vitest file {suite}")
        result = subprocess.run(
            ["npx", "--no-install", "vitest", "run", str(suite)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env=_VITEST_ENV,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"{label} Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        # Exactly the one file ran, every case passed, none skipped or todo.
        self.assertRegex(result.stdout, r"Test Files\s+1 passed \(1\)")
        self.assertRegex(result.stdout, r"Tests\s+\d+ passed \(\d+\)")
        self.assertNotRegex(result.stdout, r"\d+ (skipped|todo)")

    @covers_requirement(
        "webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure",
        "webclient-local-map::map-chrome-and-ordinary-node-labels-are-legible-without-dropping-topology",
        "webclient-local-map::metric-coordinates-survive-authoritative-transport-and-uniform-projection",
        "webclient-local-map::island-gateways-expose-labelled-accessible-exit-ring-controls",
        "webclient-local-map::the-map-surfaces-state-a-place-name-only-where-it-adds-information",
    )
    def test_local_map_island_vitest_evidence_passes(self):
        # The island cutover (render-auto-scaled-minimap-island) in LocalMap:
        # current centred in the fixed 240-unit square, the stress room's
        # exits on the compressed ring with its unlinked neighbour as a
        # label-free context dot, only labelled routes, the exit-driven
        # uniform level on the metric frame with far context omitted, exact
        # bearings when context alone sets a compressed scale, the hysteresis
        # level kept on one map and reset on another map or layer, and the
        # 格距 / 距離壓縮 caption beside the unchanged coordinate readout.
        # label-minimap-exits-and-gateways: the gate arch with its 通往 line,
        # cross-layer targets as exit-ring stubs whose native button is named
        # 往 <leads_to> 移動 and moves exactly once without opening the map,
        # locked stubs visible and inert, the wilderness return without city
        # streets, the duplicate-region suppression kept, and the crowded
        # crossroads with every exit labelled and remembered names whole.
        self._run_single_vitest_file("web/webclient-app/tests/world/local_map.test.js", "local map island")

    @covers_requirement(
        "webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure",
        "webclient-local-map::map-chrome-and-ordinary-node-labels-are-legible-without-dropping-topology",
    )
    def test_island_label_placement_vitest_evidence_passes(self):
        # The pure island label placement (lib/island_labels.js,
        # label-minimap-exits-and-gateways): eight candidates in exit, current,
        # context priority (gateway stubs first), outward and route-avoiding
        # orders, never-dropped exits with truncation and leader lines, the
        # current label's classic fallback, omitted context labels, and every
        # label of a dense exit ring inside the square.
        self._run_single_vitest_file("web/webclient-app/tests/world/island_labels.test.js", "island label placement")

    @covers_requirement(
        "webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure",
        "webclient-local-map::map-chrome-and-ordinary-node-labels-are-legible-without-dropping-topology",
    )
    def test_map_lattice_island_renderer_vitest_evidence_passes(self):
        # The shared renderer's island branch: every same-layer exit of the
        # metric plaza inside the exit ring with one route each, context as
        # in-square dots without activation, no cross-layer gate node,
        # compressed rings with 16-unit labels on the clear diagonal, the
        # uniform dot field inside a pan group, labels kept inside the
        # square, and the overlay held off the projection.
        self._run_single_vitest_file(
            "web/webclient-app/tests/world/map_lattice_renderer.test.js", "map lattice renderer"
        )

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
        "webclient-context-actions-suggestions::the-suggestions-card-is-the-single-suggestion-surface",
        "webclient-room-actions::the-建議-pill-opens-the-suggestions-card",
    )
    def test_choicepoint_node_suite_passes(self):
        # The single suggestion surface is the centred suggestions card the
        # 建議 pill opens (app_client_room_actions.test.js: generating, ready,
        # degraded, and unavailable present only on the card, whose rows own
        # the intents; action_dock.test.js keeps the retired dock pane down).
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/action/action_dock.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_room_actions.test.js"),
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
        # The narrative semantic line styling (sys lines with seal ◈ marker,
        # gold emphasis, plain serif lines) and full-log parity render
        # through full_log_overlay.test.js and narrative_line_nodes.test.js; the
        # message window renders its page fragments through the same classes
        # (message_window.test.js).
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/full_log_overlay.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/narrative_line_nodes.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/message_window.test.js"),
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

    @covers_requirement(
        "webclient-contextual-hud::companion-standing-portraits-line-up-behind-the-controlled-character-in-the-actor-left-anchor",
        "webclient-contextual-hud::possession-moves-the-possessed-companion-to-the-group-s-front",
    )
    def test_companion_lineup_node_suite_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/core/companion_lineup.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "companion-lineup Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-contextual-hud::the-place-card-names-the-current-location-and-the-world-time",
        "webclient-room-actions::the-place-card-carries-查看房間-and-休息-in-exploration-only",
    )
    def test_place_card_node_suite_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/place_card.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "place-card Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-party-window::the-party-window-presents-the-whole-party-through-one-rail",
        "webclient-party-window::the-window-remembers-its-tab-and-member-for-the-session",
        "webclient-party-window::the-member-tab-presents-bond-membership-persona-and-actions",
        "webclient-party-window::windows-show-state-never-rule-explanations",
        "webclient-party-panel::the-party-window-member-tab-offers-possession-controls-per-companion",
    )
    def test_party_window_vitest_evidence_passes(self):
        """The party window shell, its 成員 tab and their AppClient wiring
        (webclient-party-window-member-tab): rail dispatch and pending,
        server-truth adoption and fallback reset, session tab memory,
        possession-identical rendering, the descriptor-driven member actions
        with the two-step leave, the empty-slot invite and the no-rule-prose
        text check."""
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/data/party_window.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/data/party_member_tab.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_party_window.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/components/member_rail.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/core/companion_lineup.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "party-window Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-party-window::the-bag-tab-presents-the-viewed-member-s-doll-bag-and-holdings",
        "webclient-party-window::giving-from-the-bag-uses-the-committed-receive-facts",
        "webclient-party-window::the-bag-action-bar-uses-or-equips-for-the-viewed-member",
    )
    def test_party_bag_tab_vitest_evidence_passes(self):
        """The party window's 背包 tab (webclient-party-bag-tab): the doll's
        slot filter, the item selection's one party.view_member and its
        in-flight row, holdings rendered only from the committed answer,
        the stepper bounded by the committed give count, the party.transfer,
        inventory.use (after confirmation) and inventory.toggle_equip
        payloads naming the viewed member, the replaced-item label, and the
        committed disabled reasons."""
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/data/party_bag_tab.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/data/party_window.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_party_window.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/components/holdings_strip.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "party-bag-tab Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "inventory-item-actions::inventory-tiles-confirm-use-and-directly-toggle-equipment",
        "webclient-party-window::the-bag-action-bar-uses-or-equips-for-the-viewed-member",
        "webclient-party-window::in-combat-the-bag-shows-counts-and-saves-draft-item-use",
    )
    def test_party_bag_retire_vitest_evidence_passes(self):
        """The in-combat 背包 tab and the old openers (webclient-party-bag-
        retire): counts only, no give control or stepper, the committed
        戰鬥中無法交換物品 reason, 設為 X 本回合的行動… handing the viewed
        member's item to useCombatItem (switching the commanded member
        first), free toggles, no inventory.use or party.transfer leaving in
        combat, and every 背包 opener landing on the party window's 背包 tab
        without a dispatch."""
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/data/party_bag_tab.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/data/party_window.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/store/party_items_tactics.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/store/frameless_bag.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_frameless_bag.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "party-bag-retire Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    # Canonical webclient-shop-window IDs for the archive to re-point once the
    # capability exists in the main specs: `the-shop-window-uses-the-frame-with-buy-and-sell-tabs-and-the-member-rail`, `the-buy-view-shows-one-price-and-the-recipient-s-facts`, `the-sell-view-lists-the-seller-s-unequipped-items-with-one-price`, `the-shop-window-explains-no-rules`.
    @covers_requirement(
        "webclient-contextual-hud::the-party-purse-renders-exactly-once-per-window",
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully",
    )
    def test_shop_window_vitest_evidence_passes(self):
        """The shop window (webclient-shop-window): the frame with 購買/出售
        and the shared rail carrying the party window's selection, one price
        per view, the recipient's delta or held count per row, the comparison
        and the other members' chips from item_holdings, the stepper bounded
        by the committed maximum, the labelled remaining purse beside the one
        header purse, the shop.buy/shop.sell payloads naming the member, the
        closed reasons, an ordinary trade refusal and no rule prose."""
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/world/shop_window.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_shop_window.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/components/holdings_strip.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_drawers.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "shop-window Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-contextual-hud::combat-figures-stand-in-a-shared-scale-formation",
    )
    def test_foe_lineup_vitest_evidence_passes(self):
        """The foe line-up component, its geometry, and its wiring in the
        client (active foes only, live-only entrance, inert leaving copies)."""
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/core/foe_lineup.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_stage_actor.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/mode_transitions.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "foe line-up Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-contextual-hud::combat-formation-geometry-is-one-pure-shared-scale-function",
    )
    def test_combat_formation_geometry_vitest_evidence_passes(self):
        """The pure combat formation function: shared-scale ladder, dead-centre
        gap, fit rules, out-of-range fallback, full matrix and anchor values."""
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/core/combat_formation.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "combat formation Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-contextual-hud::the-objective-tracker-island-presents-the-committed-objectives-only",
    )
    def test_objective_tracker_node_suite_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/overlays/objective_tracker.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "objective-tracker Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-quest-drawer::the-detail-action-bar-mirrors-server-descriptors",
        "webclient-quest-drawer::the-quest-drawer-is-a-two-level-icon-tabbed-surface",
    )
    def test_quest_book_tracking_toggle_node_suite_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_drawer_model.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_detail.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_drawer.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "quest drawer tracking toggle Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-quest-drawer::the-detail-action-bar-mirrors-server-descriptors",
        "webclient-quest-drawer::the-quest-book-shows-one-quest-state-at-a-time",
        "webclient-quest-drawer::the-quest-drawer-degrades-honestly",
    )
    def test_quest_book_merge_rule_vitest_evidence_passes(self):
        """The quest drawer model, detail, and drawer suites are the executed
        evidence for the counter-only action join: tracking on in-progress
        rows, abandon/turn-in only on a quest_id match mirroring the counter's
        descriptor, never synthesized or re-enabled."""
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_drawer_model.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_detail.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_drawer.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "quest drawer merge rule Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-quest-drawer::selecting-a-quest-shows-its-full-detail-beside-the-list",
    )
    def test_quest_book_disclosure_vitest_evidence_passes(self):
        """The model and detail suites pin the disclosure contract: issuer
        label and letter, the settlement note, and reward cells only when the
        panel carries a reward, nothing in their place when null."""
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_drawer_model.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_detail.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "quest drawer disclosure Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-quest-drawer::the-guild-board-is-organized-by-difficulty-grade-tabs",
        "webclient-quest-drawer::the-counter-tab-shows-the-rank-card-above-the-board",
        "webclient-quest-drawer::selecting-a-board-offer-shows-its-detail-and-the-accept-action",
        "webclient-quest-drawer::an-unregistered-holder-sees-registration-instead-of-the-board",
    )
    def test_guild_board_tab_vitest_evidence_passes(self):
        """The quest drawer model and drawer suites are the executed evidence
        for the guild counter tab's grade-tabbed board: ladder-ordered grade
        tabs with the lock, dim, and own-grade marks, the default grade, the
        rank card above the offers, each offer's detail and accept action,
        and the unregistered holder's registration card."""
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_drawer_model.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_drawer.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/world/quest_detail.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "guild board tab Vitest evidence failed:\n"
            + result.stdout
            + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class DialogueSurfaceEvidenceTest(unittest.TestCase):
    """webclient-align-08/11, webclient-dialogue-stage-actors, and
    webclient-dialogue-choices-overlay: the paged dialogue window, the choice
    list over the stage, the collapsed command region, and the stage actors
    are Vue-layer contracts; the Vitest files are their executed
    evidence."""

    @covers_requirement(
        "webclient-contextual-hud::dialogue-choices-appear-centred-over-the-stage-after-the-line-is-fully-read",
    )
    def test_dialogue_feed_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/message_window_dialogue.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/dialogue_choices.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_dialogue_choices.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/dialogue_view_model.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "dialogue choices Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-contextual-hud::the-command-region-collapses-in-dialogue-mode-and-the-message-window-spans-the-band",
    )
    def test_dialogue_dock_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/dialogue_dock.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/dialogue_store.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/hud_frame.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "dialogue-dock Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-contextual-hud::stage-actors-present-the-player-and-the-dialogue-host-with-a-speaking-state",
        "webclient-contextual-hud::standing-portraits-retain-contours-and-truthful-grounded-fallbacks",
    )
    def test_stage_actor_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/core/stage_actor.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_stage_actor.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/dialogue_store.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "stage-actor Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class WaitingPracticeSurfaceEvidenceTest(unittest.TestCase):
    """align-webclient-waiting-practice-specs: the three-operation waiting
    surface and the skill book's declared-practice sub-screen are Vue-layer
    contracts; the Vitest files are their executed evidence."""

    @covers_requirement(
        "webclient-exploration-menu::the-waiting-surface-offers-three-operations-through-two-layers",
    )
    def test_waiting_surface_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/waiting_surface.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "waiting-surface Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-party-window::the-skill-tab-browses-the-viewed-member-s-skills-with-growth",
        "webclient-party-window::the-skill-detail-shows-lineage-position-and-the-freeform-ladder",
        "webclient-party-window::the-skill-tab-casts-and-books-for-the-viewed-member",
        "webclient-skillbook-casting::skill-tab-use-shares-one-keyboard-owner-and-preserves-practice",
        "webclient-skillbook-casting::the-skill-tab-follows-the-approved-prototype-and-availability-is-truthful",
    )
    def test_party_skill_tab_vitest_evidence_passes(self):
        # webclient-party-skill-tab: the party window's 技能 tab (segment,
        # search and tree in payload order; meters, levels, 新 and booked
        # tags; the ladder and lineage position only from the committed
        # selected_skill; the opening selection with tab skills and its
        # retry; 施放 / 排入修煉 for the viewed member with the committed combat
        # reasons), the store's hand-over that closes the window before the
        # dock, the companion cast through AppClient, and the retired
        # drawer name's alias.
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/data/party_skill_tab.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/store/skill_use_flow.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_drawers.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "party skill tab Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-party-window::the-lineage-list-groups-graphs-with-node-diamonds",
        "webclient-party-window::the-lineage-detail-draws-the-real-graph",
        "skill-lineage-panel::the-party-window-lineage-tab-renders-the-graphs-from-the-view-alone",
        "webclient-contextual-hud::lineage-identity-and-inventory-rarity-use-backed-fields",
        "webclient-desktop-shell::the-top-navigation-bar-carries-the-tool-group",
    )
    def test_party_lineage_tab_vitest_evidence_passes(self):
        # webclient-party-lineage-tab: the party window's 系譜 tab (graphs
        # grouped by label, rows named by their roots with node diamonds,
        # owned/total, 可解鎖 and 已全數見頂; the detail drawn by depth with each
        # merge node once and labelled edges; per-node level, meter, 見頂,
        # prerequisite and 可解鎖 text from the payload alone; an owned node
        # opening its skill on 技能 and the 技能 link opening its graph), the
        # 系譜 rows' root identity, and the 技能系譜 tool opening the party
        # window on 系譜 with focus returned to it.
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/data/party_lineage_tab.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/drawer_content_polish.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/desktop_navigation.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/reference_surface_frame.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "party lineage tab Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class GalleryArtConsumptionEvidenceTest(unittest.TestCase):
    """align-gallery-art-consumption-specs: the shared face-rect crop mapping
    and the reference-artwork frame's truthful degradation are Vue-layer
    contracts; the Vitest files are their executed evidence."""

    @covers_requirement(
        "webclient-art-panel::the-browser-maps-each-framed-portrait-s-carried-face-rectangle-to-a-centered-cover-crop-through-one-shared-pure-function",
    )
    def test_face_rect_mapping_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/data/face_rect.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "face-rect-mapping Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-art-panel::the-reference-artwork-frame-presents-a-portrait-entry-truthfully-through-cover-fit-and-rect-crop",
    )
    def test_reference_artwork_frame_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/core/reference_artwork.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "reference-artwork-frame Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class SmallAvatarZoomCropEvidenceTest(unittest.TestCase):
    """face-crop-small-avatar-thumbnails: the shared faceCropStyle zoom
    mapping and its switcher and party-window nameplate bindings are Vue-layer
    contracts; the Vitest files are their executed evidence."""

    @covers_requirement(
        "webclient-art-panel::small-avatar-thumbnails-zoom-crop-their-portrait-image-to-the-carried-face-rectangle-through-one-shared-pure-function",
    )
    def test_small_avatar_zoom_crop_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/core/character_switcher.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/data/party_member_tab.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "small-avatar-zoom-crop Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class MessagePagesEvidenceTest(unittest.TestCase):
    """webclient-message-pages: the pure response-segmentation and
    token-stream pagination contracts are verified in Vitest."""

    @covers_requirement(
        "webclient-input-narrative::the-narrative-log-is-segmented-into-responses-at-each-player-action",
        "webclient-input-narrative::a-response-is-cut-into-pages-that-fit-a-measured-box-and-never-mid-sentence",
    )
    def test_message_pages_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/message_pages.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/store/narrative_responses.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "message-pages Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-input-narrative::the-message-window-s-reading-controls-advance-pages-and-a-new-action-flushes-unread-pages",
    )
    def test_message_window_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/message_window.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "message-window Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-input-narrative::a-page-types-in-at-the-reader-s-text-speed-and-auto-advance-is-opt-in",
    )
    def test_message_window_typing_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/message_window_typing.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/message_reveal.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "message-window typing Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class MotionLevelEvidenceTest(unittest.TestCase):
    """webclient-motion-level: the motion level is resolved in one pure
    module, applied by the store, and enforced by a duration guard — all
    three are DOM-independent JS contracts, so the Vitest files are their
    executed evidence."""

    @covers_requirement(
        "webclient-contextual-hud::the-motion-level-is-a-client-local-preference-that-governs-every-client-animation",
        "webclient-contextual-hud::presentation-timing-never-gates-committed-state-or-input",
    )
    def test_motion_level_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/motion_level.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/motion_tokens.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/store/motion_preferences.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "motion-level Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class SceneTransitionsEvidenceTest(unittest.TestCase):
    """webclient-scene-transitions: the inert rule, the minimap pan offset,
    and the stage transitions driven through the real Vue <Transition> are
    DOM-state contracts jsdom can execute, so the Vitest files are their
    evidence (the browser file covers computed durations).
    animate-minimap-scale-transitions adds the island's scale-aware motion:
    map_pan.test.js decides pan / crossfade / switch from the projection's
    mode and level, and map_lattice_scale_motion.test.js mounts the island
    to show the dot field panning with the drawing on an equal-scale step,
    the inert identity-free dissolving copy at full, the immediate switch
    with no copy or pan through two frames at reduced/off, interrupted and
    unmounted sequences settling on the latest projection, and the graph
    and no-shared-frame paths unchanged."""

    @covers_requirement(
        "webclient-contextual-hud::location-appearance-and-vitals-changes-transition-at-the-motion-level",
        "webclient-contextual-hud::a-leaving-element-is-out-of-reach-while-it-animates-out",
        "webclient-local-map::island-movement-uses-scale-aware-effective-motion",
    )
    def test_scene_transitions_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/transition_hooks.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/map_pan.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/scene_transitions.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/world/map_lattice_scale_motion.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "scene-transitions Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class CombatBeatsEvidenceTest(unittest.TestCase):
    """webclient-combat-beats: the client protocol mirrors the combat beats
    schema. The DOM-independent Node sibling is its executed evidence."""

    @covers_requirement(
        "webclient-combat-beats::the-client-protocol-mirrors-the-combat-beats-schema"
    )
    def test_combat_beats_node_suite_passes(self):
        suite = (
            REPO_ROOT
            / "web/static/webclient/js/tests/protocol_combat_beats.test.js"
        )
        self.assertTrue(suite.is_file(), "the combat beats Node sibling is missing")
        result = subprocess.run(
            ["node", "--test", str(suite)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "combat beats Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class SkillUsePanelEvidenceTest(unittest.TestCase):
    """skillbook-authoritative-casting: the client protocol mirrors the
    version-1 ``skill_use`` panel (exact form, identity bounds, opening
    line-up cross references). The DOM-independent Node sibling is its
    executed evidence."""

    @covers_requirement(
        "webclient-oob-protocol::presenter-registration-and-execution-are-isolated-and-read-only"
    )
    def test_skill_use_node_suite_passes(self):
        suite = (
            REPO_ROOT
            / "web/static/webclient/js/tests/protocol_skill_use.test.js"
        )
        self.assertTrue(suite.is_file(), "the skill_use Node sibling is missing")
        result = subprocess.run(
            ["node", "--test", str(suite)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "skill_use Node suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class CombatBeatQueueEvidenceTest(unittest.TestCase):
    """webclient-combat-beat-queue: the script-side motion-token reader, the
    pure round plan / state machine / displayed hit points / page model, the
    store's bind and lock, and the message window's beat pages are DOM-state
    contracts jsdom executes, so the change's four Vitest files are their
    evidence (the browser journeys cover a real server round at `off` and
    `reduced`)."""

    @covers_requirement(
        "webclient-combat-menu::a-combat-round-plays-beat-by-beat",
        "webclient-contextual-hud::presentation-timing-never-gates-committed-state-or-input",
        "webclient-input-narrative::the-message-window-s-reading-controls-advance-pages-and-a-new-action-flushes-unread-pages",
        "webclient-contextual-hud::held-combat-decoration-never-holds-canonical-scene-identity",
    )
    def test_beat_queue_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/motion_tokens_reader.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/beat_queue.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/store/beat_playback.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/message_window_beats.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "beat-queue Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class BeatChoreographyEvidenceTest(unittest.TestCase):
    """webclient-combat-beat-choreography: which figure plays which gesture
    on each step, the pre-round line-up, the act's wait, the terminal-round
    hold, and the gesture wrapper and floating number are DOM-state contracts
    jsdom executes, so the change's Vitest files are their evidence (the
    browser journeys cover the computed animations per level and the hold)."""

    @covers_requirement(
        "webclient-contextual-hud::combat-beats-are-choreographed-on-the-stage-at-the-motion-level",
    )
    def test_beat_choreography_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/beat_choreography.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/core/stage_actor.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/core/foe_lineup.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "beat-choreography Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class ModeTransitionsEvidenceTest(unittest.TestCase):
    """webclient-mode-transitions: the live mode-change signal, the inert
    collapsed command region, the decorative flash and veil, the host's inert
    exit, the reconnect that plays nothing, and the choice rows' stagger index
    and the held terminal-round backdrop (combat decoration without a frozen
    scene identity) are DOM-state contracts jsdom can execute, so the Vitest
    file is their evidence (the browser file covers computed durations and
    animations; the beat-queue bridge covers the hold's release lifecycle)."""

    @covers_requirement("webclient-contextual-hud::mode-changes-transition-at-the-motion-level")
    @covers_requirement(
        "webclient-contextual-hud::held-combat-decoration-never-holds-canonical-scene-identity"
    )
    def test_mode_transitions_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/mode_transitions.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "mode-transitions Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class ExitCompassEvidenceTest(unittest.TestCase):
    """exploration-exit-compass: the compass's pure model, its pad component,
    the shared readout, the store's exit gate, and the dock's controls
    reference are DOM-state and reducer contracts jsdom executes, so the
    change's Vitest files are their evidence (the browser journeys cover the
    live client's hold-to-walk, the readout, and the pad's geometry)."""

    @covers_requirement(
        "webclient-exit-compass::each-exploration-exit-resolves-to-exactly-one-angled-or-portal-target",
        "webclient-exit-compass::portals-occupy-deterministic-slots-on-an-outer-track",
        "webclient-exit-compass::an-aim-snaps-to-the-nearest-angled-exit-within-thirty-degrees",
        "webclient-exit-compass::the-compass-degrades-honestly",
    )
    def test_exit_compass_model_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/action/compass_model.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "exit-compass model Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-exit-compass::the-compass-pad-answers-hover-and-click",
        "webclient-exit-compass::holding-a-pointer-press-on-an-angled-target-starts-a-walk",
        "webclient-exit-compass::the-compass-is-one-keyboard-composite",
        "webclient-exit-compass::bracket-keys-cycle-every-target-and-holding-a-key-walks",
        "webclient-exit-compass::continuous-movement-is-commit-driven",
        "webclient-exit-compass::continuous-movement-stops-safely-with-a-reason",
        "webclient-exit-compass::a-press-produces-one-discrete-move-or-one-walk-never-both",
    )
    def test_exit_compass_pad_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/action/exit_compass.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "exit-compass pad Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-exit-compass::the-compass-feeds-one-shared-readout-line",
        "webclient-exit-compass::the-aimed-destination-lights-on-the-minimap-and-motion-respects-the-motion-level",
        "webclient-room-actions::the-shared-readout-resolves-its-content-by-a-fixed-priority",
    )
    def test_exit_compass_readout_and_pane_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/action/exploration_readout.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_scene_overview.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "exit-compass readout/pane Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-exit-compass::the-compass-never-loosens-the-server-s-gate",
        "webclient-exit-compass::the-dialogue-screen-s-exits-list-stays-independent-of-the-exploration-root",
        "webclient-exit-compass::the-controls-reference-documents-the-compass-and-the-exploration-panel-shows-no-key-hints",
        "webclient-room-actions::the-controls-reference-documents-the-room-actions",
    )
    def test_exit_compass_gate_and_surfaces_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/store/exit_activation.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/app_client_dialogue_choices.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/overlays/help_overlay.test.js"),
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
            "exit-compass gate/surfaces Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class PresenceRailEvidenceTest(unittest.TestCase):
    """Vitest evidence for exploration-presence-rail (rail, verb card, ChoiceCard)."""

    def _run_vitest(self, *relative_paths):
        result = subprocess.run(
            ["npx", "--no-install", "vitest", "run"]
            + [str(REPO_ROOT / rel) for rel in relative_paths],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "presence-rail Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-presence-rail::the-presence-rail-shows-people-and-objects-on-the-stage-floor",
        "webclient-presence-rail::the-rail-shows-at-most-six-entries-and-folds-the-rest-into-a-count",
        "webclient-presence-rail::rail-entries-activate-by-the-payload-each-entry-already-carries",
        "webclient-presence-rail::the-rail-is-one-keyboard-composite-and-digits-pick-entries",
    )
    def test_presence_rail_component_vitest_evidence_passes(self):
        self._run_vitest("web/webclient-app/tests/world/presence_rail.test.js")

    @covers_requirement(
        "webclient-presence-rail::the-person-focus-verb-card-is-client-local-and-replaces-the-verb-popover",
        "webclient-presence-rail::verb-card-rows-submit-the-payloads-the-popover-rows-submitted",
        "webclient-presence-rail::a-departed-person-closes-the-card",
        "webclient-presence-rail::menu-refresh-requires-a-fresh-selection-against-the-current-mapping",
        "webclient-presence-rail::service-return-and-departure-use-valid-focus-origins",
        "webclient-presence-rail::rail-entries-activate-by-the-payload-each-entry-already-carries",
    )
    def test_presence_card_store_vitest_evidence_passes(self):
        self._run_vitest("web/webclient-app/tests/store/presence_card.test.js")

    @covers_requirement(
        "webclient-room-actions::the-exploration-screen-roots-at-the-compass-the-rail-and-room-actions",
        "webclient-presence-rail::the-person-focus-verb-card-is-client-local-and-replaces-the-verb-popover",
        "webclient-presence-rail::a-departed-person-closes-the-card",
        "webclient-presence-rail::the-presence-rail-shows-people-and-objects-on-the-stage-floor",
        "webclient-presence-rail::non-party-person-focus-uses-the-admitted-portrait-and-truthful-fallback",
    )
    def test_presence_rail_app_client_vitest_evidence_passes(self):
        self._run_vitest("web/webclient-app/tests/app_client_presence_rail.test.js")

    @covers_requirement(
        "webclient-presence-rail::choicecard-is-the-one-centred-card-shell",
        "webclient-presence-rail::the-dialogue-screen-does-not-change-when-it-renders-through-choicecard",
        "webclient-presence-rail::service-return-and-departure-use-valid-focus-origins",
    )
    def test_choice_card_vitest_evidence_passes(self):
        self._run_vitest(
            "web/webclient-app/tests/components/choice_card.test.js",
            "web/webclient-app/tests/app_client_dialogue_choices.test.js",
        )

    @covers_requirement(
        "webclient-presence-rail::npc-cards-preserve-common-slots-and-grouped-service-order",
    )
    def test_grouped_interaction_card_vitest_evidence_passes(self):
        # The card's own row model (npc-interaction-service-card, slice U): the
        # fixed common slots keep 交談 at 1 and 查看 at 2 with their reasons, the
        # conditional operations keep their deterministic order, the services
        # group follows, the return stays unnumbered, only positions 1 through 9
        # carry a digit badge, and the rendered groups are real labelled
        # sections whose headings are not rows.
        self._run_vitest(
            "web/webclient-app/tests/npc_service_card.test.js",
            "web/webclient-app/tests/components/choice_card.test.js",
        )

    @covers_requirement(
        "webclient-presence-rail::rail-digits-are-claimed-by-the-rail-and-never-fall-through",
        "webclient-presence-rail::the-rail-shows-at-most-six-entries-and-folds-the-rest-into-a-count",
    )
    def test_rail_digit_claims_vitest_evidence_passes(self):
        self._run_vitest("web/webclient-app/tests/store/digit_row_picks.test.js")


class RoomActionsEvidenceTest(unittest.TestCase):
    """exploration-room-actions; redesign-rest-entry: the rest entry and the
    suggestions card are the AppClient's room-actions composition contract;
    the Vitest files are their executed evidence (the browser journeys cover
    the live client's geometry and the retired surfaces)."""

    @covers_requirement(
        "webclient-room-actions::休息-opens-a-two-layer-rest-entry",
        "webclient-room-actions::the-rest-entry-steps-back-and-closes-with-defined-focus",
        "webclient-room-actions::the-rest-entry-s-first-layer-presents-two-choice-tiles",
        "webclient-room-actions::the-choice-tiles-show-only-client-known-context",
        "webclient-room-actions::the-rest-entry-s-second-layer-shares-one-shell-around-the-wait-and-sleep-forms",
        "webclient-room-actions::the-wait-form-mirrors-the-sleep-form",
        "webclient-room-actions::the-rest-entry-exposes-stable-test-hooks",
    )
    def test_room_actions_wait_card_vitest_evidence_passes(self):
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/app_client_room_actions.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/waiting_surface.test.js"),
                # The rest entry's components (redesign-rest-entry): the
                # first-layer tiles and the two second-layer forms.
                str(REPO_ROOT / "web/webclient-app/tests/components/time_choice_card.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/components/wait_form.test.js"),
                str(REPO_ROOT / "web/webclient-app/tests/components/sleep_form.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "room-actions wait-card Vitest evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class PartyExitEvidenceTest(unittest.TestCase):
    """webclient-party-exit-confirmation: the party-scope exit confirmation
    belongs to the combat card. The DOM-independent menu model's shared
    contract and the store's prompt/cancel/confirm lifecycle are the executed
    evidence; the managed browser journeys cover the live client's two-step
    confirmation (CI-owned)."""

    @covers_requirement(
        "webclient-combat-menu::party-command-and-exit-adapters-accept-only-guarded-exact-payloads",
    )
    @covers_requirement(
        "webclient-combat-menu::browser-party-exits-require-a-safe-default-party-consequence-dialog",
    )
    def test_party_exit_confirmation_node_and_vitest_evidence_passes(self):
        node = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/combat_menu.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            node.returncode,
            0,
            "party-exit menu Node evidence failed:\n" + node.stdout + node.stderr,
        )
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(REPO_ROOT / "web/webclient-app/tests/store/party_exit_confirmation.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "party-exit confirmation Vitest evidence failed:\n"
            + result.stdout
            + result.stderr,
        )
        self.assertIn("pass", result.stdout)


class PublicationAssemblyEvidenceTest(unittest.TestCase):
    """webclient-publication-assembly: the browser owns the bounded general
    assembly's lifetime — one live transfer per transport, a fixed first-part
    deadline no traffic extends, supersession by a newer snapshot, and release
    of buffers/timers on disconnect, detach, epoch retirement and expiry
    independently of the specialized map assembler. Those lifecycle rules only
    exist in the DOM-independent reducer, so its Node file is the executed
    evidence; the Python cross-language fixture covers adoption separately."""

    @covers_requirement(
        "webclient-publication-assembly::assembly-lifetime-and-teardown-are-explicit",
    )
    def test_publication_assembly_node_suite_passes(self):
        result = subprocess.run(
            [
                "node",
                "--test",
                str(REPO_ROOT / "web/static/webclient/js/tests/protocol_publication_parts.test.js"),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "publication assembly Node evidence failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)


if __name__ == "__main__":
    unittest.main()
