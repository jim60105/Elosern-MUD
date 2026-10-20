# Tasks

## 1. Managed save configuration and proof

- [x] 1.1 Audit settings read by the real snapshot/intervention path, bind private `GM_SAVES_ROOT` and production-equivalent retention/defaults in the managed settings/environment, and document the private layout in the existing browser-runtime guide; verify a focused configuration test establishes that database/save/art paths are private and every required save setting is present.
- [x] 1.2 Add a real isolated-runtime protected teleport regression using authenticated CSRF, no mocked successful saver, and independently checked pre-save/post-move locations; verify response snapshot ID/completeness, snapshot database before-state, committed room, developer persistence unchanged, disjoint invocation roots and owned teardown, and register the exact browser method in `.github/browser-shards.json`.
- [x] 1.3 Cover configured retention and injected snapshot failure with focused save/console tests; verify failure-before-mutation and unchanged baseline, annotate the modified browser isolation requirement, and register any new Evennia module in its exact shard.

## 2. Integration handoff

- [x] 2.1 Run the focused settings/save/console tests and exact affected browser method, `openspec validate browser-console-save-isolation --strict`, exact shard ownership/frozen contracts and the appropriate equivalent-merged-spec traceability check; record commands and results without weakening the expected pre-sync help-ID rejection.

## Workflow follow-up

- Synchronization/archive ownership runs the ordinary contract gate after requirement synchronization; full browser/evidence verification remains CI-owned.
- Land this fix before the dedicated fixture and resume original acceptance only after the entire batch lands.

## Verification record

- `uv run --locked python -m unittest web.tests.browser.test_browser_console_saves` — 5 tests OK (three settings/retention tests; the real protected teleport and the injected snapshot failure each in a dedicated managed runtime).
- `uv run --locked python -m unittest tests.test_browser_verification_contract` — 10 tests OK.
- `uv run --locked --env-file=<MUD_TEST_SETTINGS=1> evennia test --settings test_settings.py --keepdb web.gm.tests.test_console_api server.console.tests.test_policy` — 23 tests OK.
- `uv run --locked --env-file=<MUD_TEST_SETTINGS=1> evennia test --settings test_settings.py --keepdb server.saves.tests.test_snapshot` — 13 tests OK.
- `uv run --locked python -m unittest tests.test_evennia_test_optimization_contract.TestOwnershipContractTests.test_browser_method_labels_preserve_exact_ownership` — OK; both exact method labels resolve to one process list each.
- `openspec validate browser-console-save-isolation --strict` — valid.
- `uv run --locked python -m tools.contract_gate` — passed (traceability 2349/2349 covered, 0 errors; both lints, manifests, 18 contracts).
- `uv run --locked python -m tools.spec_traceability check` — 2349 requirements, 10141 associations, 0 uncovered, 0 errors. The delta MODIFIES an existing requirement without adding IDs, so the merged-spec ID set is identical to the current one; post-sync `verify --evidence` remains CI-owned.
