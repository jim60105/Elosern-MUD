# Tasks

Run pnpm commands in `web/webclient-app`.

## 1. Mount and navigation

- [x] 1.1 Apply design decisions 1–4 (`hud.js`, `view.js` comment, `nav-tools.js`, `AppClient.vue`, `OverlayHost.vue`, `styles/app-shell.css`). Verify `rg -n "GalleryPanel|角色肖像圖庫" web/webclient-app --glob '!node_modules'` returns only the files task 2.1 deletes or edits.
- [x] 1.2 Add tests for the two ADDED `webclient-gallery-window` scenarios (AppClient-level: open from the tool, Escape restores focus; unavailable panel locks) and update `tests/desktop_navigation.test.js` and `tests/reference_surface_frame.test.js` for 圖庫, decorated with the modified desktop-shell requirement where they assert it. Verify `pnpm test -- desktop_navigation reference_surface_frame gallery_window` passes.

## 2. Removal

- [x] 2.1 Apply design decisions 5–6 (delete components, stories, manifest titles; re-point or delete tests; update comments). Verify `rg -n "GalleryPanel|GalleryDetailRail" web --glob '!node_modules'` returns nothing and `pnpm test`, `pnpm run build-storybook`, `pnpm run showcase-coverage` pass.

- [x] 2.2 Remove `Data/GalleryPanel` and `Data/GalleryDetailRail` from the pinned sets in `web/webclient/tests/test_vue_showcase_data_evidence.py`, `test_vue_showcase_action_evidence.py`, `test_vue_showcase_world_evidence.py` and `test_vue_showcase_overlays_evidence.py` (each pins the manifest `required` set); in `web/webclient/tests/test_vue_gallery_ui_evidence.py` replace `GALLERY_STORY_IDS` and the storyboard story with the `Overlays/GalleryWindow` stories and retarget the annotations of the removed detail-rail requirement to `webclient-gallery-image-page` requirements. Verify those five modules pass under `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb <labels>`.

## 3. Browser journey and docs

- [x] 3.1 Apply decision 7; run `pnpm run build`, then `uv run --locked --env-file=/tmp/mud-test.env python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_gallery_image_contract`; it passes.
- [x] 3.2 Apply decision 8 to `web/webclient-app/AGENTS.md`. Verify by reading the diff.

## 4. Gates

- [x] 4.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate --change gallery-window-mount`, and the frozen-contract test `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb tests.test_webclient_frozen_contract`; all pass.
- [x] 4.2 Run `openspec validate gallery-window-mount --strict`; it passes.
