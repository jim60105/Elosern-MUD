# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Module

- [x] 1.1 Create `web/webclient/presentation/gallery_categories.py` with exactly the contract of design D1 and the rules D2–D5. Verify `uv run --locked python -m tools.observability_lint check` passes; behaviour is verified by 2.1.

## 2. Tests

- [x] 2.1 Create `web/webclient/presentation/tests/test_gallery_categories.py` (`EvenniaTest`, synthetic species via `world/tests/synthetic_data` `synthetic_registries`, synthetic characters/companions created in the test) with one test per scenario of `specs/webclient-gallery-categories/spec.md`, each decorated with its requirement ID; add the module to exactly one shard in `.github/evennia-shards.json`. Verify `<prefix> web.webclient.presentation.tests.test_gallery_categories tests.test_evennia_test_optimization_contract` passes.

## 3. Gates

- [x] 3.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change gallery-category-sources`; all pass.
- [x] 3.2 Run `openspec validate gallery-category-sources --strict`; it passes.
