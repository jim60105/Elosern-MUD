# Tasks

## 1. Deletion

- [x] 1.1 Apply the Python deletions and renames of the proposal. Verify `rg -n "gallery_subjects|GALLERY_MAX_SUBJECTS|_v3\b|gallery_subject\b|GallerySelection\b" web/webclient --type py` returns nothing.
- [x] 1.2 Apply the JS deletions. Verify `rg -n "V3|GALLERY_MAX_SUBJECTS" web/static/webclient/js/elosern` returns nothing and `node --test web/static/webclient/js/tests/*.test.js` passes.
- [x] 1.3 Delete the v3-only tests in `web/webclient/presentation/tests/test_gallery_panel.py`. Verify that module and `web.webclient.presentation.tests.test_art_push` pass with the Evennia test runner (`--settings test_settings.py --keepdb`, env file `/tmp/mud-test.env`).

## 2. Gates

- [x] 2.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate` and `pnpm test` (in `web/webclient-app`); all pass.
- [x] 2.2 Run `openspec validate gallery-v3-removal --strict`; it passes.
