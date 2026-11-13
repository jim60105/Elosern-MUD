# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`. Run pnpm commands in `web/webclient-app`.

## 1. Server

- [x] 1.1 Implement design decisions 1–2. Verify tests for the three management-actions scenarios plus the updated registry enumeration test pass in the gallery action module and the registry test module under the prefix, decorated with their requirement IDs.

## 2. Client

- [x] 2.1 Implement design decisions 3–4 in `GalleryWall.vue` and `GalleryWindow.vue`; add Vitest cases for the wall and window ADDED scenarios to `tests/components/gallery_wall.test.js` and `tests/components/gallery_window.test.js`; add a People story to `stories/Data/GalleryWall.stories.js` and `stories/Overlays/GalleryWindow.stories.js`. Verify `pnpm test`, `pnpm run build-storybook` and `pnpm run showcase-coverage` pass.

## 3. Gates

- [ ] 3.1 Run `pnpm run build`, `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate --change gallery-group-expansion`; all pass.
- [ ] 3.2 Run `openspec validate gallery-group-expansion --strict`; it passes.
