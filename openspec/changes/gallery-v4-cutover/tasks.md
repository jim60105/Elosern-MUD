# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Server

- [ ] 1.1 Apply design D1 (Python) and D2 in `web/webclient/presentation/gallery.py`, `gallery_selection.py`, `context.py`, `ingress.py`; switch `gallery.subject.select` to the renamed v4 store function. Verify the registry imports the v4 `gallery_presenter` and `rg -n "gallery_subjects" web/webclient --type py -g '!**/tests/**'` shows it only inside `gallery_presenter_v3`.
- [ ] 1.2 Migrate `web/webclient/presentation/tests/test_gallery_panel.py`, `test_art_push.py` and the gallery action tests per design D4, retargeting decorators from removed requirements to their replacements. Verify `<prefix> web.webclient.presentation.tests.test_gallery_panel web.webclient.presentation.tests.test_art_push web.webclient.presentation.tests.test_gallery_v4_presenter` and the gallery action module pass.

## 2. Client wire and transitional panel

- [ ] 2.1 Apply design D1 (JS) in `web/static/webclient/js/elosern/protocol/panels/gallery.js`, `protocol/constants.js`, `protocol.js`. Verify `node --test web/static/webclient/js/tests/*.test.js` passes.
- [ ] 2.2 Switch every client test, story and `stories/fixtures/*_panels.js` gallery entry to `gallery-fixtures-v4.js` and delete `gallery-fixtures.js`. Verify `pnpm test` passes.
- [ ] 2.3 Apply design D3 to `web/webclient-app/components/GalleryPanel.vue` and `gallery-copy.js`; update `web/webclient-app/tests/components/gallery.test.js`. Verify `pnpm test -- gallery` (run in `web/webclient-app`) passes.

## 3. Browser journey

- [ ] 3.1 Rewrite `web/tests/browser/test_browser_gallery_image_contract.py` per design D4; keep `.github/browser-shards.json` ownership exact (update labels if test names change). Run `pnpm run build` in `web/webclient-app`, then `uv run --locked --env-file=/tmp/mud-test.env python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_gallery_image_contract`; it passes.

## 4. Gates

- [ ] 4.0 Retarget `web/webclient/tests/test_vue_gallery_ui_evidence.py` annotations of the removed requirement. Verify that module passes under `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_gallery_ui_evidence`.
- [ ] 4.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate --change gallery-v4-cutover`, `pnpm run build-storybook` and `pnpm run showcase-coverage`; all pass.
- [ ] 4.2 Run `openspec validate gallery-v4-cutover --strict`; it passes.

## Workflow follow-up

- At archive sync, edit the Purpose of `openspec/specs/webclient-gallery-panel/spec.md` and `openspec/specs/webclient-gallery-ui/spec.md` to describe the category-scoped panel and drop "subject rail" and "filter" wording.
