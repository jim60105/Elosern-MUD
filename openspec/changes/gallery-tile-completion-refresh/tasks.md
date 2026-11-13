# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Qualification

- [x] 1.1 Replace `_gallery_subject_keys` in `web/webclient/presentation/art_push.py` with the design's function and docstring. Verify by 1.2.
- [x] 1.2 Add to `web/webclient/presentation/tests/test_art_push.py` one test for the new scenario (listed, unselected companion completes → gallery update with refreshed tile, `selected` unchanged) and one for an unlisted subject (no gallery update), decorated with the modified requirement ID. Verify `<prefix> web.webclient.presentation.tests.test_art_push` passes.
- [x] 1.3 Resolve the delta's scenario drift: the inherited selection-restoration, off-room roster sibling, late-completion and scene-reach scenarios, plus the off-room sibling test, assumed gallery matched the selection only. Restate their preconditions or references on the rendered wall's listed subjects so every scenario states the rule this change implements. Verify `openspec validate gallery-tile-completion-refresh --strict`.

## 2. Gates

- [x] 2.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate --change gallery-tile-completion-refresh`; both pass.
- [x] 2.2 Run `openspec validate gallery-tile-completion-refresh --strict`; it passes.
