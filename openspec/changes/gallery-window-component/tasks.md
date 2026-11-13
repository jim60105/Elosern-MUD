# Tasks

Run pnpm commands in `web/webclient-app`.

## 1. Window

- [x] 1.1 Create `components/GalleryWindow.vue` per design D1–D7; add `initialImage` to `gallery-window-model.js` and `GALLERY_CATEGORY_LABELS` plus the glyph map to `gallery-copy.js` if absent. Verify by 1.2.
- [x] 1.2 Create `tests/components/gallery_window.test.js` with one test per ADDED scenario (mount with v4 fixtures, a fake `dispatch` recording calls, simulated committed panels) and a style lint. Verify `pnpm test -- gallery_window` passes.

## 2. Stories

- [x] 2.1 Add `stories/Overlays/GalleryWindow.stories.js` (MyCharacters, FirstRelease with people/scene disabled, Party, OfficialImage, NoImages, Monsters; reference and full-HD variants) and the `Overlays/GalleryWindow` manifest entry. Verify `pnpm run build-storybook` and `pnpm run showcase-coverage` pass.

## Evidence

- [x] E.1 Add `Overlays/GalleryWindow` to the pinned manifest sets in `web/webclient/tests/test_vue_showcase_data_evidence.py`, `test_vue_showcase_action_evidence.py`, `test_vue_showcase_world_evidence.py` and `test_vue_showcase_overlays_evidence.py` (each pins the manifest `required` set). Verify `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence` passes.

## 3. Gates

- [ ] 3.1 Run `pnpm test` and `uv run --locked python -m tools.contract_gate --change gallery-window-component`; both pass.
- [ ] 3.2 Run `openspec validate gallery-window-component --strict`; it passes.
