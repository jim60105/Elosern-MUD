"""Evidence bridge: run the Vue gallery gates as webclient-gallery-ui evidence.

The 圖庫 management surface is the gallery window (gallery-window-mount) and
is verified in the Vue layer: the gallery suite
(web/webclient-app/tests/components/gallery.test.js) asserts the window's
editor lifecycle, the official-entry actions, the no-image page, the drawer
dispatch contracts and face-rect geometry; the window, wall and image-page
suites assert the committed categories, subjects, tray rows and the two-step
deletion; the application integration suite
(web/webclient-app/tests/app_client_gallery.test.js) asserts the mounted
window, the shared single-dispatch entry, its gates, and the rejection
narrative; the offline
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

from ._showcase_build import ShowcaseEvidenceMixin, showcase_build_lock

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_ROOT / "web/webclient-app/tests"
GALLERY_COMPONENTS = TESTS_DIR / "components" / "gallery.test.js"
GALLERY_STAGE = TESTS_DIR / "components" / "stage_transform.test.js"
GALLERY_APP_CLIENT = TESTS_DIR / "app_client_gallery.test.js"
GALLERY_WINDOW = TESTS_DIR / "components" / "gallery_window.test.js"
GALLERY_WALL = TESTS_DIR / "components" / "gallery_wall.test.js"
GALLERY_PAGE = TESTS_DIR / "components" / "gallery_image_page.test.js"
STORYBOOK_OUT = REPO_ROOT / ".storybook-out"
FRAME_GUIDE = REPO_ROOT / "docs/design/legacy-design/elosern-redesign2/gallery-storyboard.md"

# Every gallery story family registered in the frozen component manifest: the
# gallery window with its interactive Storyboard export, its wall and page, and
# the four editors.
GALLERY_STORY_IDS = frozenset(
    {
        "overlays-gallerywindow--my-characters",
        "overlays-gallerywindow--first-release",
        "overlays-gallerywindow--party",
        "overlays-gallerywindow--official-image",
        "overlays-gallerywindow--no-images",
        "overlays-gallerywindow--monsters",
        "overlays-gallerywindow--storyboard",
        "data-gallerywall--mine",
        "data-gallerywall--tray-states",
        "data-galleryimagepage--character-card",
        "data-galleryimagepage--armed-delete",
        "overlays-gallerygeneratedrawer--character",
        "overlays-gallerygeneratedrawer--monster",
        "overlays-gallerygeneratedrawer--rejected",
        "overlays-gallerybindingdrawer--overlap-warnings",
        "overlays-gallerybindingdrawer--unmatched",
        "overlays-galleryfacerectmodal--edit-portrait",
        "overlays-galleryfacerectmodal--failed-original",
        "overlays-galleryfacerectmodal--recovered-original",
        "overlays-galleryfacerectmodal--rejected",
        "overlays-galleryfacerectmodal--silhouette-only",
        "overlays-gallerystagetransformmodal--identity",
        "overlays-gallerystagetransformmodal--child",
        "overlays-gallerystagetransformmodal--translated",
        "overlays-gallerystagetransformmodal--boundary",
        "overlays-gallerystagetransformmodal--pending",
        "overlays-gallerystagetransformmodal--rejected",
        "overlays-gallerystagetransformmodal--failed-load",
        "overlays-gallerystagetransformmodal--recovered-original",
        "overlays-gallerystagetransformmodal--reduced-motion",
    }
)

# The gallery journey frames the frame guide must state, each with its
# transition and recovery column (spec: "state each transition and recovery
# path"). Matched as the guide's zh-TW frame headings, not prose paraphrases.
FRAME_GUIDE_FRAMES = (
    "1. 瀏覽",
    "2. 檢視",
    "3. 生成",
    "4. 送出與結算",
    "5. 綁定",
    "6. 框選",
    "7. 預設",
    "8. 刪除",
    "9. 魔物",
    "10. 比例",
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


class VueGalleryUiEvidenceTest(ShowcaseEvidenceMixin, unittest.TestCase):
    """Execute the gallery UI Vitest/showcase gates as requirement evidence."""

    #: The gallery storyboard gate needs the static Storybook build.
    SHOWCASE_BUILD = "storybook"

    @covers_requirement(
        "webclient-gallery-ui::the-gallery-surface-renders-committed-categories-subjects-and-rows"
    )
    def test_panel_renders_committed_facts(self):
        # The window suite's 'the rail switches category through the server'
        # cases pin one tab per committed category, the single category
        # dispatch that keeps the committed wall until the next panel, and
        # the focusable disabled category announcing its committed reason;
        # 'marks the subject whose selection is in flight busy' pins the one
        # subject dispatch and publication-driven re-render. The wall suite's
        # 'committed groups as aspect-true subject tiles' and 'the tray under
        # the owner's row' cases pin payload-ordered tiles and tray rows, and
        # its 'tray tiles carry state by shape and text' case pins the
        # committed failure tile with no image.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_WINDOW, GALLERY_WALL), "gallery committed facts"
        )

    @covers_requirement(
        # The retired detail-rail requirement keeps its annotation until the
        # archive sync removes it; the image page requirements carry the
        # same behaviour afterwards.
        "webclient-gallery-ui::the-detail-rail-presents-the-selected-card-and-gates-destructive-intent",
        "webclient-gallery-image-page::deletion-takes-two-steps",
        "webclient-gallery-image-page::the-footer-follows-the-declared-capabilities",
        "webclient-gallery-image-page::the-page-renders-committed-facts-in-cells",
    )
    def test_image_page_gates_destructive_intent(self):
        # The detail rail retired with gallery-window-mount; the image page
        # presents the selected image. The page suite's 'deletion takes two
        # steps' cases pin the armed confirmation, the cancel and Escape
        # paths and the single confirmed press; its footer cases pin the
        # capability-driven buttons (no binding affordance for a monster);
        # its fact cases pin committed binding conditions and no invented
        # ones. The AppClient case 'confirms deletion through the shared
        # entry' pins the same flow against the real store.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_PAGE, GALLERY_APP_CLIENT),
            "gallery image page destructive gating",
        )

    @covers_requirement(
        "webclient-gallery-ui::official-entries-render-as-selectable-read-only-rows-with-personal-geometry-affordances"
    )
    def test_official_rows_are_selectable_read_only(self):
        # 'previews a selected official entry with only its read-only
        # affordances' pins the official page with 清除個人調整/臉框/舞台位置
        # and 清除選取 or 設為預設, and no 刪除/replace/regenerate button;
        # 'dispatches the selection with only the subject key and the
        # committed identity', 'clears the personal geometry through its own
        # action', 'sends only the edited face rectangle for an official
        # identity' and 'sends only the edited stage triple for an official
        # identity' pin every affordance dispatching its committed action
        # with exactly the edited component; 'never dispatches an untouched
        # official geometry save' pins that a save without an edit crosses
        # no wire. The 'official-only artwork and the no-image page' cases
        # pin that committed official rows alone keep the no-image page away,
        # that an empty official list with no cards shows it with 生成新圖,
        # and that a committed replacement toggles it without a dispatch.
        # The wall suite pins the official run after the cards in the tray,
        # never counted as cards.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_COMPONENTS, GALLERY_WALL), "gallery official rows"
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
        "webclient-gallery-ui::stage-transforms-affect-full-figures-and-never-avatar-cover-crops"
    )
    def test_stage_transforms_full_figures_only(self):
        # 'A child stays on the same ground line', 'Translation uses frame
        # dimensions at every scale', and 'Null stage and cover crop remain
        # unchanged' pin the bottom-center custom-property transform, the
        # null normalization, and the untouched faceObjectPosition cover path.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_STAGE), "stage transform rendering"
        )

    @covers_requirement(
        "webclient-gallery-ui::the-stage-editor-previews-a-local-triple-against-a-static-adult-reference"
    )
    def test_stage_editor_local_preview(self):
        # 'Slider and number edits synchronize', 'Drag uses frame fractions
        # and clamps', 'Reset does not save', and 'Adult comparison stays
        # static' pin the local-only draft, the frame-fraction drag mapping
        # with bounds, and the transform-free static reference layer.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_STAGE), "stage editor preview"
        )

    @covers_requirement(
        "webclient-gallery-ui::stage-saves-reuse-correlated-lifecycle-and-accessible-gallery-chrome"
    )
    def test_stage_save_lifecycle(self):
        # 'Save waits for image load', 'Save closes only on its correlated
        # revision', 'Rejection preserves editable intent', and 'Non-card and
        # stale contexts cannot save' pin the load gate, the one-submit
        # payload, the revision-correlated close, the retained rejected
        # draft with the log link, and the pending-row refusal.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_APP_CLIENT), "stage save lifecycle"
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
        # on Escape', 'cancels without an action and restores the opener ...'
        # and 'restores focus to the rail when the edited card and its opener
        # disappear' pin the shared focus trap with Escape-to-close and
        # restoration parity; the window suite's 'focus is rescued and Escape
        # closes in layers' cases and the AppClient case that restores the
        # 圖庫 tool on Escape pin the window's layers. The never-color-only
        # clause: the wall suite's 'marks default, pending and failed tiles
        # with text and a shape' pins the 預設 / 生成中 / 生成失敗 text.
        _assert_vitest_passes(
            _run_vitest_once(GALLERY_COMPONENTS, GALLERY_WINDOW, GALLERY_WALL, GALLERY_APP_CLIENT),
            "gallery keyboard-first + explicit state text",
        )

    @covers_requirement(
        "webclient-gallery-ui::the-gallery-has-an-offline-interactive-storyboard"
    )
    def test_offline_storyboard_and_frame_guide(self):
        # The gallery window family plus its interactive Storyboard are
        # registered in the built offline showcase; the storyboard entry is a
        # story under Overlays/GalleryWindow. The zh-TW frame guide
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
        storyboard = entries["overlays-gallerywindow--storyboard"]
        self.assertEqual(storyboard["type"], "story")
        self.assertEqual(storyboard["title"], "Overlays/GalleryWindow")

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
            "復原 |", guide, "frame guide lacks the recovery column"
        )
        self.assertIn(
            "僅供故事使用的發布驅動器",
            guide,
            "frame guide does not distinguish fixture publications from live behavior",
        )

    @covers_requirement(
        "webclient-gallery-ui::stage-transform-stories-document-visual-and-state-behavior-offline"
    )
    def test_stage_transform_stories_offline(self):
        # 'Showcase covers the complete editor offline' pins the registered
        # modal family (identity, child, translated, boundary, pending,
        # rejected, failed-load, reduced-motion) present in the built
        # showcase index with no game or AI server.
        with showcase_build_lock():
            self.assertTrue(
                (STORYBOOK_OUT / "index.json").is_file(),
                "missing storybook index.json",
            )
            index = json.loads(
                (STORYBOOK_OUT / "index.json").read_text(encoding="utf-8")
            )
        entries = index.get("entries", {})
        missing = {
            story_id
            for story_id in GALLERY_STORY_IDS
            if story_id.startswith("overlays-gallerystagetransformmodal--")
        } - set(entries)
        # The five stage-transform artwork states are asserted here even
        # though they sit outside the frozen required-set manifest.
        missing |= {
            "core-referenceartwork--stage-identity",
            "core-referenceartwork--stage-null-default",
            "core-referenceartwork--stage-child-scale",
            "core-referenceartwork--stage-offsets",
            "core-referenceartwork--stage-enlarged-overflow",
        } - set(entries)
        self.assertEqual(
            missing,
            set(),
            "stage transform stories missing from the showcase: "
            + ", ".join(sorted(missing)),
        )


if __name__ == "__main__":
    unittest.main()
