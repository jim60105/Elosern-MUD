# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Conversion

- [ ] 1.1 Implement `migrate_classic_scene_records()` in `world/art/service.py` per design D1. Verify by 1.3.
- [ ] 1.2 Insert the `art_scene_migration` startup step before `art_gallery_prune` (design D2) and update the step-catalog test (`rg -ln "art_gallery_prune" server tests`). Verify that test passes under the prefix.
- [ ] 1.3 Add a test class for the six ADDED scenarios (temporary `ART_STORE_ROOT` with real files, synthetic archetypes), decorated with the requirement ID, beside the prune tests (`rg -ln "prune_gallery_orphans" world/art/tests`). Verify the module passes under the prefix.

## 2. Gates

- [ ] 2.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.observability_lint check` and `uv run --locked python -m tools.contract_gate --change scene-asset-migration`; all pass.
- [ ] 2.2 Run `openspec validate scene-asset-migration --strict`; it passes.
