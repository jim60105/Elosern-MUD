## 1. Baseline

- [ ] 1.1 Capture the gate report and this area's freeze-list entries with `uv run --locked python -m tools.test_data_lint check --json`
- [ ] 1.2 Confirm the synthetic kit catalogs cover this area's registries; extend only the kit module when an entry shape is genuinely missing

## 2. Migration

Shared idiom (learned from the commands/quests migrations): kit rows come from
`world/tests/synthetic_data.py`; classes that construct against patched catalogs
enter the scope through a helper called at the top of `setUp` (the kit's class
decorator wraps `test*` only); identity-only subject keys become file-local
`t_`-prefixed constants; registry iteration in startup-sync tests runs over the
PATCHED kit registries inside `synthetic_registries("archetypes", "monster_tiers")`.

Baseline (task 1.1): 315 findings across the 22 flagged manifest files
(`test_gallery_seed.py` scans clean → migrates by ledger-entry removal alone).

## 3. Migrate group 1

- [x] 3.1 Migrate `world/art/tests/test_art_observability.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.2 Migrate `world/art/tests/test_connectivity.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.3 Migrate `world/art/tests/test_gallery.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.4 Migrate `world/art/tests/test_gallery_fallback.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.5 Migrate `world/art/tests/test_gallery_match.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 3.6 Migrate `world/art/tests/test_gallery_prompt.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 4. Migrate group 2

- [x] 4.1 Migrate `world/art/tests/test_gallery_seed.py` (tier B): confirmed zero findings — migrates by ledger-entry removal alone (7.1); focused label green
- [x] 4.2 Migrate `world/art/tests/test_presenter.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.3 Migrate `world/art/tests/test_queue.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.4 Migrate `world/art/tests/test_scheduler.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.5 Migrate `world/art/tests/test_sd_worker.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.6 Migrate `world/art/tests/test_service.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 5. Migrate group 3

- [ ] 5.1 Migrate `world/art/tests/test_subjects.py` (tier S, re-derive pinned quantities from the synthetic catalog): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.2 Migrate `world/art/tests/test_worker.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.3 Migrate `world/imports/tests/test_degraded_banner.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.4 Migrate `world/imports/tests/test_loader_trait_values.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.5 Migrate `world/imports/tests/test_profession_assembly_loader.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 5.6 Migrate `world/imports/tests/test_profession_assembly_schema.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 6. Migrate group 4

- [ ] 6.1 Migrate `world/imports/tests/test_schema.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 6.2 Migrate `world/imports/tests/test_validation_semantics.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 6.3 Migrate `world/prompts/tests/test_degrade.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 6.4 Migrate `world/prompts/tests/test_loader.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [ ] 6.5 Migrate `world/prompts/tests/test_verbatim_shipment.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 7. Freeze-list and closure

- [ ] 7.1 Remove exactly the migrated files' entries from `tools/test_data_freeze.json` and re-run the gate (must be clean)
- [ ] 7.2 Add the area closure test file `tests/test_data_independence_art_imports.py` (owned by `unittest discover`, not an Evennia shard): one test asserting the gate reports zero debt exemptions among this change's migrated files, and one asserting every manifest entry was removed from `tools/test_data_freeze.json`. Ship it WITHOUT a `@covers_requirement` annotation — the requirement id does not exist in the traceability index until this delta is archived/synced; adding the annotation earlier fails `spec_traceability check` with `unknown-requirement-id`
- [ ] 7.3 Annotate the closure test with the canonical id from `uv run --locked python -m tools.spec_traceability list` in the archive step that syncs this delta into `openspec/specs/test-data-independence/spec.md`, then run `uv run --locked python -m tools.spec_traceability check` (must be green)
- [ ] 7.4 Run the affected shard(s) per `.github/evennia-shards.json`, the closure test via `unittest`, and `git diff --check`
