## Why

Sexual state/resist/status-query tests hardcode SEXUAL_ACT keys and shipped CJK level labels (中等/極限/平靜/私處 ...) that are rulebook and vocabulary data.


The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 14 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; sexual-state and status behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 14 flagged test files under world/rules/tests/ (sexual/status cluster) to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (8 assertion-literal files, 6 setup-literal files).
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
  closure test in `tests/test_data_independence_rules_sexual.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `world/rules/tests/test_cast_settlement_sexual_coercion.py` | B |
| `world/rules/tests/test_combat_session_sexual_coercion.py` | B |
| `world/rules/tests/test_equipment_sexual_effects.py` | A |
| `world/rules/tests/test_ordered_level_trait.py` | A |
| `world/rules/tests/test_sexual_act_effects.py` | A |
| `world/rules/tests/test_sexual_decay_and_reset.py` | A |
| `world/rules/tests/test_sexual_event_self_arming.py` | B |
| `world/rules/tests/test_sexual_resist.py` | B |
| `world/rules/tests/test_sexual_resist_cast_wiring.py` | B |
| `world/rules/tests/test_sexual_state.py` | A |
| `world/rules/tests/test_sexual_transitions.py` | A |
| `world/rules/tests/test_sexual_unlock.py` | A |
| `world/rules/tests/test_status_query.py` | A |
| `world/rules/tests/test_status_text.py` | B |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the Sexual-state and status closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under world/rules/tests/ (sexual/status cluster) owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 14 listed test files plus the new closure test file `tests/test_data_independence_rules_sexual.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
