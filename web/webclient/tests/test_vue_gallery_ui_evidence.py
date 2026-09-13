"""Evidence bridge: run the Vue gallery gates as webclient-gallery-ui evidence.

The 角色肖像圖庫 management surface is implemented and verified in the Vue
layer: the gallery component suite
(web/webclient-app/tests/components/gallery.test.js) asserts the committed
panel rendering, destructive-intent gating, drawer dispatch contracts, and
face-rect geometry; the application integration suite
(web/webclient-app/tests/app_client_gallery.test.js) asserts the shared
single-dispatch entry, its gates, and the rejection narrative; the offline
interactive storyboard is registered in the static Storybook showcase and
documented by the English frame guide. ``covers_requirement`` can only attach
to a Python ``test_*`` function, so this module executes those gates and
asserts they pass; each annotation links one webclient-gallery-ui main-spec
requirement to its substantively matching, executed evidence record
(webclient-hud-drawer evidence-bridge precedent).
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

from ._showcase_build import showcase_build_lock

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_ROOT / "web/webclient-app/tests"
GALLERY_COMPONENTS = TESTS_DIR / "components" / "gallery.test.js"
GALLERY_APP_CLIENT = TESTS_DIR / "app_client_gallery.test.js"
STORYBOOK_OUT = REPO_ROOT / ".storybook-out"
FRAME_GUIDE = REPO_ROOT / "docs/design/elosern-redesign2/gallery-storyboard.md"

# Every gallery story family registered in the frozen component manifest: the
# five component families plus the interactive Storyboard export.
GALLERY_STORY_IDS = frozenset(
    {
        "data-gallerypanel--populated",
        "data-gallerypanel--empty",
        "data-gallerypanel--monster",
        "data-gallerypanel--unavailable",
        "data-gallerypanel--locked",
        "data-gallerypanel--storyboard",
        "data-gallerydetailrail--default-portrait",
        "data-gallerydetailrail--unmatched-binding",
        "data-gallerydetailrail--failed",
        "overlays-gallerygeneratedrawer--character",
        "overlays-gallerygeneratedrawer--monster",
        "overlays-gallerygeneratedrawer--rejected",
        "overlays-gallerybindingdrawer--overlap-warnings",
        "overlays-gallerybindingdrawer--unmatched",
        "overlays-galleryfacerectmodal--edit-portrait",
        "overlays-galleryfacerectmodal--rejected",
    }
)

# The gallery journey frames the frame guide must state, each with its
# transition and recovery column (spec: "state each transition and recovery
# path"). Matched as the guide's frame headings, not prose paraphrases.
FRAME_GUIDE_FRAMES = (
    "1. Browse",
    "2. Inspect",
    "3. Generate",
    "4. Submit and settle",
    "5. Bind",
    "6. Crop",
    "7. Default",
    "8. Delete",
    "9. Monster",
)

# The four reference design images the guide must link (spec: "reference the
# four design images").
FRAME_GUIDE_IMAGES = (
    "角色肖像圖庫管理頁-圖庫主畫面.webp",
    "角色肖像圖庫管理頁-生成新圖.webp",
    "角色肖像圖庫管理頁-裝備綁定.webp",
    "角色肖像圖庫管理頁-臉部框選.webp",
)

# The vitest file-set results executed once per class; each annotated test
# asserts its own substantive mapping against the shared execution evidence.
_VITEST_RESULTS: dict[tuple[str, ...], subprocess.CompletedProcess[str]] = {}


def _run_vitest_once(*test_files: Path) -> subprocess.CompletedProcess[str]:
    """Run each vitest file-set once per process (cold starts are shared)."""
    key = tuple(str(p) for p in test_files)
    if key not in _VITEST_RESULTS:
        _VITEST_RESULTS[key] = subprocess.run(
            ["npx", "--no-install", "vitest", "run", *key],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
    return _VITEST_RESULTS[key]


def _assert_vitest_passes(result, label):
    assert result.returncode == 0, (
        f"{label} Vitest suite failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "passed" in result.stdout, f"{label}: expected a passing suite summary"


class VueGalleryUiEvidenceTest(unittest.TestCase):
    """Execute the gallery UI Vitest/showcase gates as requirement evidence."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # The storyboard gate needs the static Storybook build; build it once
        # per process when the checkout has none (CI workspaces only build the
        # app dist). The lock serializes against the B1/B2 evidence classes,
        # which rebuild the same .storybook-out in other parallel workers.
        with showcase_build_lock():
            if not (STORYBOOK_OUT / "iframe.html").is_file():
                result = subprocess.run(
                    ["npm", "run", "build-storybook"],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=900,
                )
                assert result.returncode == 0, (
                    "Storybook build failed under gallery evidence:\n"
                    + result.stdout
                    + result.stderr
                )

    @covers_requirement(
        "webclient-gallery-ui::the-gallery-surface-renders-only-committed-panel-facts"
    )
    def test_panel_renders_committed_facts(self):
        # 'filters committed rows without replacing counts or order, and keeps
        # failure text intact' pins verbatim tab counts, payload row order,
        # and the committed failure line with no image element; 'waits for
        # subject publication rather than optimistically switching cards'
        # pins the one select dispatch and publication-driven re-render.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_COMPONENTS), "gallery panel facts"
        )

    @covers_requirement(
        "webclient-gallery-ui::the-detail-rail-presents-the-selected-card-and-gates-destructive-intent"
    )
    def test_detail_rail_gates_destructive_intent(self):
        # 'cancels deletion, confirms once, and never invents missing binding
        # conditions' pins the in-rail confirmation, the single confirmed
        # dispatch, explicit condition absence, and the monster binding-
        # affordance gate; the AppClient case 'confirms deletion through the
        # shared entry' pins the same flow against the real store.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_COMPONENTS, GALLERY_APP_CLIENT),
            "gallery detail rail destructive gating",
        )

    @covers_requirement(
        "webclient-gallery-ui::the-generate-drawer-maps-checkboxes-to-the-closed-catalog-and-dispatches-one-request"
    )
    def test_generate_drawer_catalog_dispatch(self):
        # 'submits raw code-point-counted oversized input with only selected
        # field ids' pins the closed-catalog checkbox ids, the raw text, and
        # the ids-only payload; 'respects monster capabilities ...' pins the
        # capability-gated absence of checkboxes and free text.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_COMPONENTS), "gallery generate drawer"
        )

    @covers_requirement(
        "webclient-gallery-ui::the-binding-drawer-enables-slots-only-and-renders-overlap-warnings-verbatim"
    )
    def test_binding_drawer_slots_and_warnings(self):
        # 'requires a slot, preserves empty-slot intent, and renders warning
        # lines verbatim' pins the checkbox-only slot mask, the
        # equipped-value-only display (no picker), the verbatim warning card,
        # and the ids-only save payload.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_COMPONENTS), "gallery binding drawer"
        )

    @covers_requirement(
        "webclient-gallery-ui::the-face-rect-modal-stores-geometry-over-the-original-image"
    )
    def test_face_rect_modal_geometry(self):
        # 'moves without resizing and clamps positive area at image
        # boundaries', 'uses the displayed non-square image bounds, and
        # submits the keyboard-adjusted rectangle without pixels', and
        # 'cancels without an action ...' pin the normalized [0,1] geometry,
        # the no-pixel payload, and the cancel path.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_COMPONENTS), "gallery face-rect modal"
        )

    @covers_requirement(
        "webclient-gallery-ui::gallery-mutations-ride-the-single-dispatch-entry-and-its-gates"
    )
    def test_mutations_single_dispatch_gates(self):
        # The AppClient integration suite (real pinia store + fake sender)
        # pins every mutation leaving only through the shared dispatch entry,
        # the concurrent-mutation block, the rejected generation surfacing its
        # committed message exactly once through the narrative path, and the
        # transport teardown blocking a stale dispatch.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_APP_CLIENT), "gallery dispatch gates"
        )

    @covers_requirement(
        "webclient-gallery-ui::the-gallery-surface-is-keyboard-first-and-never-color-only"
    )
    def test_keyboard_first_and_never_color_only(self):
        # The keyboard clause: 'traps keyboard focus and restores the opener
        # on Escape', 'cancels without an action and restores the opener ...',
        # and 'restores a remaining gallery control when the edited card and
        # opener disappear' pin the shared focus trap with Escape-to-close and
        # restoration parity. The never-color-only clause: 'marks crown,
        # pending, and failed rows with explicit state text, not color alone'
        # pins the 目前預設 / 生成中 / committed-failure text on those rows.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_COMPONENTS, GALLERY_APP_CLIENT),
            "gallery keyboard-first + explicit state text",
        )

    @covers_requirement(
        "webclient-gallery-ui::the-gallery-has-an-offline-interactive-storyboard"
    )
    def test_offline_storyboard_and_frame_guide(self):
        # The five component families plus the interactive Storyboard are
        # registered in the built offline showcase; the storyboard entry is a
        # document story under Data/GalleryPanel. The English frame guide
        # links the four reference images, states every journey frame with
        # its transition and recovery column, and separates the fixture
        # publication driver from live behavior.
        with showcase_build_lock():
            self.assertTrue(
                (STORYBOOK_OUT / "index.json").is_file(),
                "missing storybook index.json",
            )
            index = json.loads(
                (STORYBOOK_OUT / "index.json").read_text(encoding="utf-8")
            )
        entries = index.get("entries", {})
        missing = GALLERY_STORY_IDS - set(entries)
        self.assertEqual(
            missing,
            set(),
            "gallery stories missing from the showcase: "
            + ", ".join(sorted(missing)),
        )
        storyboard = entries["data-gallerypanel--storyboard"]
        self.assertEqual(storyboard["type"], "story")
        self.assertEqual(storyboard["title"], "Data/GalleryPanel")

        guide = FRAME_GUIDE.read_text(encoding="utf-8")
        for image in FRAME_GUIDE_IMAGES:
            self.assertIn(
                image, guide, f"frame guide does not reference {image}"
            )
        for frame in FRAME_GUIDE_FRAMES:
            self.assertIn(
                frame, guide, f"frame guide does not state frame {frame}"
            )
        self.assertIn(
            " Recovery", guide, "frame guide lacks the recovery column"
        )
        self.assertIn(
            "story-only publication driver",
            guide,
            "frame guide does not distinguish fixture publications from live behavior",
        )


if __name__ == "__main__":
    unittest.main()
