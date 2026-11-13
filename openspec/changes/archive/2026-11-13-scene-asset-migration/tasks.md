# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Conversion

- [x] 1.1 Implement `migrate_classic_scene_records()` in `world/art/service.py` per design D1. Verify by 1.3.
- [x] 1.2 Insert the `art_scene_migration` startup step before `art_gallery_prune` (design D2) and update the step-catalog test (`rg -ln "art_gallery_prune" server tests`). Verify that test passes under the prefix.
- [x] 1.3 Add a test class for the six ADDED scenarios (temporary `ART_STORE_ROOT` with real files, synthetic archetypes), beside the prune tests (`rg -ln "prune_gallery_orphans" world/art/tests`). Its requirement annotation lands at archive sync, when the ADDED requirement gains its canonical id. Verify the module passes under the prefix.

## 2. Producers

- [x] 2.1 Apply design D3 in `world/art/service.py`. Verify `rg -n "queue_ensure\(" world/art/service.py` shows no scene call.
- [x] 2.2 Add tests for the ADDED startup requirement (fresh database → one gallery request per synthetic archetype; carded scene → none; deleted scene → none; failed first generation → retried on entry; operator official image → still requested) and the modified room-entry scenarios, retargeting decorators from the removed startup requirement. Verify the startup-sync and room-entry test modules (`rg -ln "ensure_scene_asset|art_sync_all" world typeclasses --glob '*tests*'`) pass under the test prefix.

## 3. Gates

- [x] 3.1 Run `uv run --locked python -m tools.spec_traceability check --change scene-asset-migration`, `uv run --locked python -m tools.observability_lint check` and `uv run --locked python -m tools.contract_gate --change scene-asset-migration`; all pass.
- [x] 3.2 Run `openspec validate scene-asset-migration --strict`; it passes.
