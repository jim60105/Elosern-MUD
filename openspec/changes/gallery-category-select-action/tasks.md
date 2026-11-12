# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Adapter

- [x] 1.1 Add `validate_gallery_category_select_payload` and `_gallery_category_select_adapter` to `web/webclient/actions/gallery_actions.py` and register `gallery.category.select` in `web/webclient/actions/registry.py` (design). Verify by 1.2.
- [x] 1.2 Add tests for the three ADDED scenarios in the gallery action test module (`rg -ln "gallery.subject.select" web/webclient/actions/tests`), decorated with the requirement ID, and update the production-registry enumeration test to include `gallery.category.select` under the modified `webclient-action-dispatch` requirement. Verify the two modules pass under the prefix.

## 2. Gates

- [x] 2.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate --change gallery-category-select-action`; both pass.
- [x] 2.2 Run `openspec validate gallery-category-select-action --strict`; it passes.
