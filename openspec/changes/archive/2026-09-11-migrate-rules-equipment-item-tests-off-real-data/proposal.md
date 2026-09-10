## Why

equipment_*/item_*/buff/effect-handler tests hardcode ITEM_REGISTRY keys (healing_potion, plain_sword, knight_platemail, ...), synthetic-independent buff keys, and equipment modifier data in asserted outcomes.


The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 17 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; equipment and item behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 17 flagged test files under world/rules/tests/ (equipment/item cluster) to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (10 assertion-literal files, 7 setup-literal files).
- Replace every shipped-identifier literal and shipped display-prose literal in the
  migrated files with kit constants or locally built synthetic definitions; replace
  pinned data quantities with values derived from the patched synthetic catalogs.
- Where a shared helper is part of this area's debt, rewrite its builders on kit data so
  every borrower stops inheriting shipped ids.

- Restate converted assertions as the mechanics the owning OpenSpec requirement
  describes. A test that only echoes synthetic-fixture content is deepened or deleted;
  a deleted test's `@covers_requirement` annotation moves onto the replacement test.
  A deleted test MUST name the test that exercises the same production branch; a test
  that is the only evidence for a branch is retained, never deleted for gate
  cleanliness (the aggregate coverage gate stays the CI-owned floor).
- Remove this area's debt entries from `tools/test_data_freeze.json` and add the area
  closure test in `tests/test_data_independence_rules_equipment.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `world/rules/tests/test_buffs.py` | A |
| `world/rules/tests/test_cast_settlement.py` | A |
| `world/rules/tests/test_climax_settlement.py` | B |
| `world/rules/tests/test_damage_effect_handler.py` | B |
| `world/rules/tests/test_effect_handlers.py` | B |
| `world/rules/tests/test_equipment_attached_buffs.py` | B |
| `world/rules/tests/test_equipment_combat_wiring.py` | A |
| `world/rules/tests/test_equipment_gauge_sync.py` | B |
| `world/rules/tests/test_equipment_immunity.py` | B |
| `world/rules/tests/test_equipment_prose.py` | A |
| `world/rules/tests/test_equipment_toggle.py` | A |
| `world/rules/tests/test_equipment_worn_grace_rules.py` | B |
| `world/rules/tests/test_heal_effect_handler.py` | A |
| `world/rules/tests/test_holy_water_cleanse.py` | A |
| `world/rules/tests/test_inventory_helpers.py` | A |
| `world/rules/tests/test_item_combat_turn.py` | A |
| `world/rules/tests/test_item_use.py` | A |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the Equipment and item closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under world/rules/tests/ (equipment/item cluster) owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 17 listed test files plus the new closure test file `tests/test_data_independence_rules_equipment.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
