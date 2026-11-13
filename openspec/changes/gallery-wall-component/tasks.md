# Tasks

Run pnpm commands in `web/webclient-app`.

## 1. Model and component

- [x] 1.1 Add the D2 helpers to `components/gallery-window-model.js` with unit tests in `tests/components/gallery_wall.test.js`. Verify `pnpm test -- gallery_wall` passes.
- [x] 1.2 Create `components/GalleryWall.vue` per design D1, D3, D4; extend the same test file with one test per ADDED scenario of `specs/webclient-gallery-wall/spec.md` and the style lint. Verify `pnpm test -- gallery_wall` passes.

## 2. Stories

- [x] 2.1 Add v4 fixtures to `stories/gallery-fixtures-v4.js`, `stories/Data/GalleryWall.stories.js` and the `Data/GalleryWall` manifest entry (design D5), plus the Node fixture-validity test. Verify `pnpm run build-storybook` and `pnpm run showcase-coverage` pass.

## Evidence

- [x] E.1 Add `Data/GalleryWall` to the pinned manifest sets in `web/webclient/tests/test_vue_showcase_data_evidence.py`, `test_vue_showcase_action_evidence.py`, `test_vue_showcase_world_evidence.py` and `test_vue_showcase_overlays_evidence.py` (each pins the manifest `required` set). Verify `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence` passes.

## 3. Gates

- [ ] 3.1 Run `pnpm test` and `uv run --locked python -m tools.contract_gate --change gallery-wall-component`; both pass.
- [ ] 3.2 Run `openspec validate gallery-wall-component --strict`; it passes.
