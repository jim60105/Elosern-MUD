# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Qualification

- [ ] 1.1 Replace `_gallery_subject_keys` in `web/webclient/presentation/art_push.py` with the design's function and docstring. Verify by 1.2.
- [ ] 1.2 Add to `web/webclient/presentation/tests/test_art_push.py` one test for the new scenario (listed, unselected companion completes → gallery update with refreshed tile, `selected` unchanged) and one for an unlisted subject (no gallery update), decorated with the modified requirement ID. Verify `<prefix> web.webclient.presentation.tests.test_art_push` passes.

## 2. Gates

- [ ] 2.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate --change gallery-tile-completion-refresh`; both pass.
- [ ] 2.2 Run `openspec validate gallery-tile-completion-refresh --strict`; it passes.
