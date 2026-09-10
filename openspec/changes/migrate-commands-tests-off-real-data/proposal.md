## Why

Player-command tests hardcode healing_potion/meal/plain_sword, fire_ball, g_*_rank titles, and assert CJK command output that is rendered from data.


The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 27 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; command and typeclass behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 27 flagged test files under commands/ and typeclasses/ to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (15 assertion-literal files, 12 setup-literal files).
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
  closure test in `tests/test_data_independence_commands.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `commands/tests/test_art.py` | B |
| `commands/tests/test_background.py` | A |
| `commands/tests/test_character_creation.py` | A |
| `commands/tests/test_combat_actions.py` | B |
| `commands/tests/test_command_branch_behaviour.py` | A |
| `commands/tests/test_guild_economy_commands.py` | A |
| `commands/tests/test_inventory_breakdown.py` | B |
| `commands/tests/test_items.py` | A |
| `commands/tests/test_lineage_command.py` | A |
| `commands/tests/test_localized.py` | A |
| `commands/tests/test_lore_command.py` | A |
| `commands/tests/test_party_commands.py` | B |
| `commands/tests/test_persona_commands.py` | B |
| `commands/tests/test_talk_turnin_branch.py` | A |
| `commands/tests/test_talk_turnin_commands.py` | A |
| `commands/tests/test_title_command.py` | A |
| `typeclasses/tests/test_account_capacity.py` | B |
| `typeclasses/tests/test_account_login.py` | B |
| `typeclasses/tests/test_appearance.py` | A |
| `typeclasses/tests/test_art_room_entry.py` | B |
| `typeclasses/tests/test_components.py` | A |
| `typeclasses/tests/test_entities.py` | B |
| `typeclasses/tests/test_exit_movement_cost.py` | B |
| `typeclasses/tests/test_exits.py` | B |
| `typeclasses/tests/test_npc_dialogue.py` | A |
| `typeclasses/tests/test_npcs.py` | B |
| `typeclasses/tests/test_rooms.py` | A |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the Command and typeclass closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under commands/ and typeclasses/ owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 27 listed test files plus the new closure test file `tests/test_data_independence_commands.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
