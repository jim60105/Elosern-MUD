## Why

Combat session/initiation/view/modifier/targeting/freeform tests hardcode basic_attack, fire_ball, wind_blade, defense_instinct, and equipment keys in asserted results.


The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 18 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; combat-core behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 18 flagged test files under world/rules/tests/ (combat cluster) to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (8 assertion-literal files, 10 setup-literal files).
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
  closure test in `tests/test_data_independence_rules_combat.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `world/rules/tests/_combat_session_helpers.py` | B |
| `world/rules/tests/test_affinity.py` | B |
| `world/rules/tests/test_combat_initiation.py` | A |
| `world/rules/tests/test_combat_modifiers.py` | A |
| `world/rules/tests/test_combat_modifiers_matched.py` | B |
| `world/rules/tests/test_combat_result.py` | B |
| `world/rules/tests/test_combat_session_flow.py` | A |
| `world/rules/tests/test_combat_session_recovery.py` | B |
| `world/rules/tests/test_combat_session_targeting.py` | B |
| `world/rules/tests/test_combat_view.py` | A |
| `world/rules/tests/test_disengage.py` | B |
| `world/rules/tests/test_disengage_integration.py` | B |
| `world/rules/tests/test_freeform_casting.py` | A |
| `world/rules/tests/test_friendly_fire.py` | B |
| `world/rules/tests/test_golden_combat.py` | B |
| `world/rules/tests/test_initiative_and_turn_loop.py` | A |
| `world/rules/tests/test_phase4_integration.py` | A |
| `world/rules/tests/test_targeting.py` | A |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the Combat-core closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under world/rules/tests/ (combat cluster) owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 18 listed test files plus the new closure test file `tests/test_data_independence_rules_combat.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
