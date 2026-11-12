# Tasks

## 1. Scene chain

- [ ] 1.1 Apply design decision 1 in `world/art/presenter.py` and update the scene presenter tests (no classic fallback; gallery-only generation state and retention), decorated with the modified `scene-artwork-presentation` requirement ID. Verify the scene presenter test module (`rg -ln "describe_scene" world/art/tests web/webclient/presentation/tests`) passes under `uv run --locked --env-file=/tmp/mud-test.env` with the Evennia test runner and `--settings test_settings.py --keepdb`.

## 2. Browser staging

- [ ] 2.1 Apply design decisions 2–3 to `web/browser_support/unified_image_transitions.py`, `web/tests/browser/seed/art_fixture.py` and `exploration_fixture.py`. Run `pnpm run build` in `web/webclient-app`, then run the browser unittest driver (`uv run --locked --env-file=/tmp/mud-test.env python -m web.tests.browser.unittest_driver <module>`) once for `web.tests.browser.test_browser_unified_scenes` and, as a separate command, once for `web.tests.browser.test_browser_art`; both pass.

## 3. Gates

- [ ] 3.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate --change scene-classic-fallback-removal`; both pass.
- [ ] 3.2 Run `openspec validate scene-classic-fallback-removal --strict`; it passes.
