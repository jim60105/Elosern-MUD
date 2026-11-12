# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Shared helper

- [x] 1.1 Extract `_selected_subject_fields(subject, entity)` from `gallery_presenter` per design D1 and make v3 use it. Verify `<prefix> web.webclient.presentation.tests.test_gallery_panel web.webclient.presentation.tests.test_art_push` passes with no test edits.

## 2. Store

- [x] 2.1 Add `GalleryViewSelection`, `gallery_view_snapshot`, `select_gallery_category`, `select_gallery_subject_v4` to `web/webclient/presentation/gallery_selection.py` and retire `ndb.gallery_view` through a post-puppet owner check rather than `retire_gallery_selection` (design D2); add `gallery_view` to `PresentationContext` and fill it in `ingress.py`. Verify by 3.2.

## 3. Builder and tests

- [x] 3.1 Add `build_gallery_v4(context)` and `_resolve_view` per design D3–D4; do not register it. Verify by 3.2.
- [x] 3.2 Create `web/webclient/presentation/tests/test_gallery_v4_presenter.py` (`EvenniaTest`, synthetic species, synthetic account characters and companions) with one test per ADDED scenario, left unannotated (ADDED requirement IDs exist only after archive sync; os-archive annotates them); every built payload must pass `validate_gallery_v4`. Register the module in `.github/evennia-shards.json`. Verify `<prefix> web.webclient.presentation.tests.test_gallery_v4_presenter tests.test_evennia_test_optimization_contract` passes.

## 4. Gates

- [x] 4.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change gallery-v4-presenter`; all pass.
- [x] 4.2 Run `openspec validate gallery-v4-presenter --strict`; it passes.
