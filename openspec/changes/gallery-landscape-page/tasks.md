# Tasks

Run pnpm commands in `web/webclient-app`.

## 1. Page and wall

- [x] 1.1 Apply design decisions 1–3 in `components/GalleryImagePage.vue` and `components/gallery-window-model.js`; add Vitest cases for the three image-page scenarios to `tests/components/gallery_image_page.test.js` and the wall scenario to `tests/components/gallery_wall.test.js`. Verify `pnpm test -- gallery_image_page gallery_wall` passes.

## 2. Stories

- [ ] 2.1 Add Scenes and SceneBundled stories (reference and full HD) to `stories/Data/GalleryImagePage.stories.js` and `stories/Overlays/GalleryWindow.stories.js` with v4 scene fixtures. Verify `pnpm run build-storybook` and `pnpm run showcase-coverage` pass.

## 3. Gates

- [ ] 3.1 Run `pnpm test`, `pnpm run build`, `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate --change gallery-landscape-page`; all pass.
- [ ] 3.2 Run `openspec validate gallery-landscape-page --strict`; it passes.
