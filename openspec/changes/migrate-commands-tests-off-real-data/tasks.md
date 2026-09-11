## 1. Baseline

- [x] 1.1 Capture the gate report and this area's freeze-list entries with `uv run --locked python -m tools.test_data_lint check --json`
- [x] 1.2 Confirm the synthetic kit catalogs cover this area's registries; extend only the kit module when an entry shape is genuinely missing

## 2. Migration

## 3. Migrate group 1

- [x] 3.1 Migrate `commands/tests/test_art.py` (tier B): art subjects driven through scoped kit scene-archetype/monster-tier catalogs plus one locally authored archetype; focused label green
- [x] 3.2 Migrate `commands/tests/test_background.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.3 Migrate `commands/tests/test_character_creation.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.4 Migrate `commands/tests/test_combat_actions.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 3.5 Migrate `commands/tests/test_command_branch_behaviour.py` (tier A): kit guild branch, kit prose gear over a runtime-probed rulebook row, kit race wizard, kit-scope delivery good; focused label green
- [x] 3.6 Migrate `commands/tests/test_guild_economy_commands.py` (tier A): kit synthetic branch/shop/board rows via the shared guild probe helpers; trade and claim amounts derive from live bands

## 4. Migrate group 2

- [x] 4.1 Migrate `commands/tests/test_inventory_breakdown.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.2 Migrate `commands/tests/test_items.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.3 Migrate `commands/tests/test_lineage_command.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.4 Migrate `commands/tests/test_localized.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.5 Migrate `commands/tests/test_lore_command.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 4.6 Migrate `commands/tests/test_party_commands.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 5. Migrate group 3

- [x] 5.1 Migrate `commands/tests/test_persona_commands.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 5.2 Migrate `commands/tests/test_talk_turnin_branch.py` (tier A): mocked reward payload names the kit potion row; focused label green
- [x] 5.3 Migrate `commands/tests/test_talk_turnin_commands.py` (tier A): branch on the kit synthetic branch; quest, offer, and reward are locally registered rows; focused label green
- [x] 5.4 Migrate `commands/tests/test_title_command.py` (tier A): titles registry scoped with locally authored rows; grants replaced by direct bank_fixed/bank_epithet on invented vocabulary; focused label green
- [x] 5.5 Migrate `typeclasses/tests/test_account_capacity.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 5.6 Migrate `typeclasses/tests/test_account_login.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 6. Migrate group 4

- [x] 6.1 Migrate `typeclasses/tests/test_appearance.py` (tier A): zero gate findings — migrated by freeze-list entry removal alone (focused label green on the clean path)
- [x] 6.2 Migrate `typeclasses/tests/test_art_room_entry.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 6.3 Migrate `typeclasses/tests/test_components.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 6.4 Migrate `typeclasses/tests/test_entities.py` (tier B): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 6.5 Migrate `typeclasses/tests/test_exit_movement_cost.py` (tier B): waiver grant set read off the production gate seam; focused label green
- [x] 6.6 Migrate `typeclasses/tests/test_exits.py` (tier B): gate xyz and approaches derived from a live-registry gateway-entry probe; focused label green

## 7. Migrate group 5

- [x] 7.1 Migrate `typeclasses/tests/test_npc_dialogue.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only
- [x] 7.2 Migrate `typeclasses/tests/test_npcs.py` (tier B): zero gate findings — migrated by freeze-list entry removal alone (focused label green on the clean path)
- [x] 7.3 Migrate `typeclasses/tests/test_rooms.py` (tier A): swap literals for kit constants/fixtures, restate assertions as behavior, run the focused label for this file only

## 8. Freeze-list and closure

- [x] 8.1 Remove exactly the migrated files' entries from `tools/test_data_freeze.json` and re-run the gate (must be clean)
- [x] 8.2 Add the area closure test file `tests/test_data_independence_commands.py` (owned by `unittest discover`, not an Evennia shard): one test asserting the gate reports zero debt exemptions among this change's migrated files, and one asserting every manifest entry was removed from `tools/test_data_freeze.json`. Ship it WITHOUT a `@covers_requirement` annotation — the requirement id does not exist in the traceability index until this delta is archived/synced; adding the annotation earlier fails `spec_traceability check` with `unknown-requirement-id`
- [ ] 8.3 Annotate the closure test with the canonical id from `uv run --locked python -m tools.spec_traceability list` in the archive step that syncs this delta into `openspec/specs/test-data-independence/spec.md`, then run `uv run --locked python -m tools.spec_traceability check` (must be green)
- [x] 8.4 Focused per-file labels green for every migrated module; closure test green via `unittest` (`tests.test_data_independence_commands`); no new Evennia test modules so `.github/evennia-shards.json` stays untouched; `git diff --check` clean (full shard sweep is owned by the session-level validation pass)
