# Tasks

## 1. Scene chain

- [x] 1.1 Apply design decision 1 in `world/art/presenter.py` and update the scene presenter tests (no classic fallback; gallery-only generation state and retention), decorated with the modified `scene-artwork-presentation` requirement ID. Verify the scene presenter test module (`rg -ln "describe_scene" world/art/tests web/webclient/presentation/tests`) passes under `uv run --locked --env-file=/tmp/mud-test.env` with the Evennia test runner and `--settings test_settings.py --keepdb`.

- [x] 1.2 Admit the scene gallery card identity (`gallery/scene/<archetype>/<image-id>.<ext>`) to the same-origin media route — it is the scene chain's only generated source now — and prove the record-gated serving in the art media tests (`web/art_media.py`, `web/webclient/tests/test_art_media.py`).

## 2. Browser staging

- [x] 2.1 Apply design decisions 2–3 to `web/browser_support/unified_image_transitions.py` and `web/tests/browser/seed/art_fixture.py` (`exploration_fixture.py` seeds only portrait records, so it holds no scene state to restage). Run `pnpm run build` at the repository root (the workspace script that emits `web/static/webclient/app/dist`), then run the browser unittest driver (`uv run --locked --env-file=/tmp/mud-test.env python -m web.tests.browser.unittest_driver <module>`) once for `web.tests.browser.test_browser_unified_scenes` and, as a separate command, once for `web.tests.browser.test_browser_art`; both pass.

## 3. Gates

- [x] 3.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate --change scene-classic-fallback-removal`; both pass.
- [x] 3.2 Run `openspec validate scene-classic-fallback-removal --strict`; it passes.
