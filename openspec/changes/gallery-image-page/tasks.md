# Tasks

Run pnpm commands in `web/webclient-app`.

## 1. Model

- [x] 1.1 Add `galleryFooter` and `galleryRibbon` to `components/gallery-window-model.js` (create the file if `gallery-wall-component` has not landed; both changes only append functions) per design D2/D4, with unit tests covering every scenario of the two footer requirements in `tests/components/gallery_image_page.test.js`. Verify `pnpm test -- gallery_image_page` passes.

## 2. Component

- [ ] 2.1 Create `components/GalleryImagePage.vue` per design D1, D3, D4, D5; add component tests for the deletion and fact-cell requirements and a style lint to the same test file. Verify `pnpm test -- gallery_image_page` passes.

## 3. Stories

- [ ] 3.1 Add `stories/Data/GalleryImagePage.stories.js` (character card, default card, monster card, official entry, pending, failed, empty, armed delete; both viewports) using v4 fixtures from `stories/gallery-fixtures-v4.js`, and the `Data/GalleryImagePage` manifest entry. Verify `pnpm run build-storybook` and `pnpm run showcase-coverage` pass.

## Evidence

- [ ] E.1 Add `Data/GalleryImagePage` to the pinned manifest sets in `web/webclient/tests/test_vue_showcase_data_evidence.py`, `test_vue_showcase_action_evidence.py`, `test_vue_showcase_world_evidence.py` and `test_vue_showcase_overlays_evidence.py` (each pins the manifest `required` set). Verify `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence` passes.

## 4. Gates

- [ ] 4.1 Run `pnpm test` and `uv run --locked python -m tools.contract_gate --change gallery-image-page`; both pass.
- [ ] 4.2 Run `openspec validate gallery-image-page --strict`; it passes.
