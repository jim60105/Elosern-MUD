# Tasks

## 1. Content — 幽月谷村 (Eolas) residents

- [ ] 1.1 Author 15 resident homes as permanent interior rooms under `content/maps/interiors/` (plus `content/map-editor-layouts/`), each with a real Exit onto the village street/public node. Verify: `check_map_sources.py` exit 0 and `uv run --locked python -m tools.settlement_synthesis lint <map_id>` clean.
- [ ] 1.2 Author 15 `NpcProfile`s (`world/lore/npc_profiles/eolas_residents*.py`, adult register, ages unstated) and fill 15 `Resident` rows (literal in-band elf stats, `home_room`, `resident` template, `dialogue_key`). Verify: `npc_content_lint.py --profiles` 0 errors and roster validation passes.
- [ ] 1.3 Author 15 conditional dialogue tables (`world/lore/dialogue/content/eolas_resident_*.yaml`), each with at least one hidden/locked optional topic plus a `refusal`. Verify: the dialogue snapshot loads and `npc_content_lint.py` 0 errors; the Chinese/writing-style/zh-TW conversion lints reach 0 must-fix for every file.

## 2. Content — 翠綠森林村 (Fionnen) residents

- [ ] 2.1 Author 15 resident homes as permanent interior rooms under `content/maps/interiors/` (plus `content/map-editor-layouts/`), each with a real Exit onto the village street/public node. Verify: `check_map_sources.py` exit 0 and `uv run --locked python -m tools.settlement_synthesis lint <map_id>` clean.
- [ ] 2.2 Author 15 `NpcProfile`s (`world/lore/npc_profiles/fionnen_residents*.py`, adult register, ages unstated) and fill 15 `Resident` rows (literal in-band elf stats, `home_room`, `resident` template, `dialogue_key`). Verify: `npc_content_lint.py --profiles` 0 errors and roster validation passes.
- [ ] 2.3 Author 15 conditional dialogue tables (`world/lore/dialogue/content/fionnen_resident_*.yaml`), each with at least one hidden/locked optional topic plus a `refusal`. Verify: the dialogue snapshot loads and `npc_content_lint.py` 0 errors; the Chinese/writing-style/zh-TW conversion lints reach 0 must-fix for every file.

## 3. Content — 暗影谷村 (Ciaran) residents

- [ ] 3.1 Author 15 resident homes as permanent interior rooms under `content/maps/interiors/` (plus `content/map-editor-layouts/`), each with a real Exit onto the village street/public node. Verify: `check_map_sources.py` exit 0 and `uv run --locked python -m tools.settlement_synthesis lint <map_id>` clean.
- [ ] 3.2 Author 15 `NpcProfile`s (`world/lore/npc_profiles/ciaran_residents*.py`, adult register, ages unstated) and fill 15 `Resident` rows (literal in-band elf stats, `home_room`, `resident` template, `dialogue_key`). Verify: `npc_content_lint.py --profiles` 0 errors and roster validation passes.
- [ ] 3.3 Author 15 conditional dialogue tables (`world/lore/dialogue/content/ciaran_resident_*.yaml`), each with at least one hidden/locked optional topic plus a `refusal`. Verify: the dialogue snapshot loads and `npc_content_lint.py` 0 errors; the Chinese/writing-style/zh-TW conversion lints reach 0 must-fix for every file.

## 4. Inventory, editorial ledger and generated context

- [ ] 4.1 Add 45 `resident` rows to `world/lore/npc_profiles/inventory.py` (owner = the three village slices) and one `resident` row per resident to `docs/development/npc-editorial-review.md`. Verify: `world.lore.tests.test_npc_profile_inventory` and `world.lore.tests.test_npc_editorial_review` pass with no missing/stale rows.
- [ ] 4.2 Write the per-village resident review documents under `docs/lore/` (line-by-line source/register check, every proper noun resolved to a registry row). Verify: review documents exist and list every owned resident and dialogue table.
- [ ] 4.3 Regenerate `content/map-reference-context.json`. Verify: `uv run --locked python -m tools.contract_gate` reference-context check passes.

## 5. Integration verification

- [ ] 5.1 Run the focused dialogue/roster Evennia labels and the map sources check; then `uv run --locked python -m tools.contract_gate`, `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.spec_traceability check`. Verify: all green.

## Workflow follow-up

- This change applies only after `elven-resident-npcs-mechanism` is archived.
- Archive this change after the project's review requirements are satisfied, and sync the `npc-residents` delta into `openspec/specs/`.