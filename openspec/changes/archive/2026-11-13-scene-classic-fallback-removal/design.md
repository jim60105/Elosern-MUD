# Design: remove the classic fallback from the scene chain

## Context

- `world/art/presenter.py::describe_scene` after `scene-kind-gallery`: the
  generated position tries `_scene_gallery_card(subject)` then the classic
  record (`_scene_generated_resource`), generation state merges gallery and
  classic facts, retention uses the card identity then classic outputs.
- `web/browser_support/unified_image_transitions.py` stages scene states with
  the classic queue (`requeue`, claim, `settle`) and `scene_subject_for_room`;
  `web/tests/browser/seed/art_fixture.py` writes classic scene
  `ArtAssetRecord`s (`exploration_fixture.py` writes only portrait records, so
  it holds no scene state to restage); `test_browser_unified_scenes.py` and
  `test_browser_art.py` assert the resulting backgrounds.

## Goals / Non-Goals

**Goals:** gallery-only scene generated source; browser staging follows.

**Non-Goals:** deleting the generic classic queue/worker code.

## Decisions

1. Delete the classic branch from `describe_scene`; remove
   `_scene_generated_resource` and the scene use of
   `_scene_retained_output_identity` if no other caller remains (check with
   `rg`). Generation state: pending when a scene gallery job is in flight,
   failed when the gallery record has `last_error_code`, done when a stored
   card exists, else missing. A recorded error also stays a reached
   generation-failed fact at the generated position (beside the card it did
   not replace), so the existing "failed regeneration remains visible"
   presentation and the browser's local failure caption keep working without
   the classic failed record.
2. Browser staging: `pending_scene` enqueues a scene gallery job through
   `request_gallery_image(scene_subject)`; `done_scene` settles it through
   the gallery settle path with a fixture image; `failed_scene` settles it
   failed; `move_scene` keeps its room logic. Seeds append scene cards with
   `gallery_api.append_card` instead of classic records.
3. Keep test names; if a browser test method is renamed, update
   `.github/browser-shards.json` in the same commit.

## Risks / Trade-offs

- [Browser staging helpers are shared by other journeys] → run each affected
  browser file once locally after `pnpm run build`.
